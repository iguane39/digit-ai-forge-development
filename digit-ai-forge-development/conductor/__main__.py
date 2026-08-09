"""CLI du conductor — point d'entrée unique `conductor run "<idée>"`.

Enchaîne les cinq étapes dans l'ordre structurel A → B → C → D → E. L'ordre
scaffold-first (B avant C) est un invariant, pas une option (décision 02).
La logique de chaque étape arrive aux Epics 1 et 3 ; ici on câble la séquence.

Le run laisse une **sortie machine** (`_forge-output/run-report.json` dans le repo cible) et
rend un **code de retour signifiant** : 0 run complet, 2 pause HITL (légitime, ≠ échec),
1 erreur.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from pathlib import Path

from conductor import __version__
from conductor.bmad_bridge import BmadPlanner, lancer_planification
from conductor.cadrage import DEFAULT_CHARTER, DEFAULT_STYLE, DEFAULT_TARGET, cadrer, charger_scope
from conductor.contracts import BrickChoice, MissionConfig, SprintReport
from conductor.governance import DelegatedGate, HitlPending, HumanGate, require_hitl0
from conductor.onramp import select_onramp
from conductor.planners import ComplementPlanner, CompositePlanner, RemediationPlanner
from conductor.report import Clock, RunStatus, write_run_report
from conductor.sprint_config import preparer_sprint
from conductor.supervisor import superviser

# Codes de retour du CLI — une pause HITL n'est PAS un échec (décision 07).
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_HITL_PENDING = 2


def _slug(idea: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")
    return (s or "saas")[:40]


def _select_planner(mission: MissionConfig) -> BmadPlanner | None:
    """Planner selon l'intention. None = DefaultBmadPlanner (greenfield / complément délégué)."""
    if mission.mode == "greenfield":
        return None
    intent = mission.brownfield_intent
    if intent == "remediation":
        return RemediationPlanner()
    if intent == "complement":
        return ComplementPlanner()
    return CompositePlanner(RemediationPlanner(), ComplementPlanner())


def run(
    idea: str,
    *,
    mode: str = "greenfield",
    existing_repo: Path | None = None,
    intent: str = "remediation",
    target: str = DEFAULT_TARGET,
    brand_charter: Path = DEFAULT_CHARTER,
    style_slug: str = DEFAULT_STYLE,
    bricks: list[BrickChoice] | None = None,
    workdir: Path = Path("generated"),
    clock: Clock | None = None,
    hitl_gate: HumanGate | None = None,
) -> SprintReport:
    """Orchestration A → B (onramp) → C (HITL 1) → D → E (HITL 2), greenfield ou brownfield.

    Renvoie le `SprintReport` de l'étape E et écrit systématiquement la sortie machine
    `_forge-output/run-report.json` dans le repo cible — y compris en pause HITL ou en échec,
    où l'exception d'origine est relayée telle quelle à l'appelant.

    `hitl_gate` (TF-0009) : `None` préserve le défaut prudent (`ManualGate`, refus systématique,
    inchangé). Passer un `DelegatedGate` délègue explicitement HITL-0/1/2 selon sa politique —
    jamais activé par défaut.
    """
    mission = cadrer(
        idea,
        mode=mode,  # type: ignore[arg-type]
        existing_repo=existing_repo,
        intent=intent,  # type: ignore[arg-type]
        target=target,
        brand_charter=brand_charter,
        style_slug=style_slug,
        bricks=bricks,
    )
    if mission.mode == "brownfield":
        # garde explicite (≠ assert, non silencé par -O) ; cadrer() garantit déjà l'invariant
        if mission.existing_repo is None:
            raise ValueError("Le mode brownfield exige un existing_repo.")
        dest = mission.existing_repo
    else:
        dest = workdir / _slug(idea)

    def _emit(status: RunStatus, *, sprint: SprintReport | None = None, detail: str = "") -> None:
        write_run_report(
            dest, status=status, idea=idea, mode=mode, sprint=sprint, detail=detail, clock=clock
        )

    try:
        substrate = select_onramp(mission).prepare(mission, dest)  # B
        # HITL-0 seulement s'il y a quelque chose à valider (normalisation/dégradation déclarée) :
        # actif en C/B, sauté en A (repo déjà conforme) — conforme à la spec.
        if mission.mode == "brownfield" and substrate.declared_degradation:
            require_hitl0("normalisation & carte d'archi", substrate, gate=hitl_gate)
        plan = lancer_planification(
            substrate, planner=_select_planner(mission), gate=hitl_gate
        )  # C — HITL 1
        layout = preparer_sprint(plan, dest, baseline=substrate.baseline)  # D
        report = superviser(layout, hitl=hitl_gate)  # E — HITL 2
    except HitlPending as pause:
        _emit("hitl-pending", detail=str(pause))
        raise
    except Exception as err:
        # un échec d'écriture du rapport ne doit jamais masquer l'erreur d'origine
        with contextlib.suppress(OSError):
            _emit("error", detail=f"{type(err).__name__} : {err}")
        raise
    _emit("complete", sprint=report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conductor", description="Accélérateur SaaS Digit-AI")
    parser.add_argument("--version", action="version", version=f"conductor {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="idée → SaaS PR-ready")
    run_p.add_argument("idea", help="l'intention produit, ex. \"un CRM pour artisans\"")
    run_p.add_argument("--mode", choices=["greenfield", "brownfield"], default="greenfield")
    run_p.add_argument("--repo", type=Path, default=None, help="repo cible existant (brownfield)")
    run_p.add_argument(
        "--intent", choices=["remediation", "complement", "both"], default="remediation"
    )
    run_p.add_argument(
        "--charter", type=Path, default=DEFAULT_CHARTER, help="chemin du DESIGN.md client"
    )
    run_p.add_argument("--target", default=DEFAULT_TARGET, help="slug de la cible de production")
    run_p.add_argument("--style", default=DEFAULT_STYLE, help="slug du style design retenu")
    run_p.add_argument(
        "--scope", type=Path, default=None, help="fichier JSON du scope SaaS (liste de briques)"
    )
    run_p.add_argument(
        "--auto-approve-hitl",
        nargs="*",
        default=None,
        metavar="PREFIXE",
        help=(
            "délègue l'approbation des checkpoints HITL dont l'intitulé commence par l'un de ces "
            'préfixes, ex. --auto-approve-hitl "HITL-0" "PRD & architecture (HITL 1)" '
            "(TF-0009 ; absent = comportement inchangé, refus systématique par ManualGate)"
        ),
    )
    args = parser.parse_args(argv)
    if args.command != "run":
        return EXIT_OK
    try:
        run(
            args.idea,
            mode=args.mode,
            existing_repo=args.repo,
            intent=args.intent,
            target=args.target,
            brand_charter=args.charter,
            style_slug=args.style,
            bricks=charger_scope(args.scope) if args.scope is not None else None,
            hitl_gate=DelegatedGate(args.auto_approve_hitl) if args.auto_approve_hitl else None,
        )
    except HitlPending as pause:
        # Pause légitime, pas un échec : on imprime la question posée à l'humain.
        print(f"HITL — validation humaine requise :\n  {pause}")
        print("Le run est en pause. Approuve hors chaîne, puis relance.")
        return EXIT_HITL_PENDING
    except Exception as err:
        print(f"Échec du run — {type(err).__name__} : {err}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
