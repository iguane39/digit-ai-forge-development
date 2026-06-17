"""CLI du conductor — point d'entrée unique `conductor run "<idée>"`.

Enchaîne les cinq étapes dans l'ordre structurel A → B → C → D → E. L'ordre
scaffold-first (B avant C) est un invariant, pas une option (décision 02).
La logique de chaque étape arrive aux Epics 1 et 3 ; ici on câble la séquence.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from conductor import __version__
from conductor.bmad_bridge import BmadPlanner, lancer_planification
from conductor.cadrage import cadrer
from conductor.contracts import MissionConfig
from conductor.onramp import select_onramp
from conductor.planners import ComplementPlanner, CompositePlanner, RemediationPlanner
from conductor.sprint_config import preparer_sprint
from conductor.supervisor import superviser


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
    workdir: Path = Path("generated"),
) -> None:
    """Orchestration A → B (onramp) → C (HITL 1) → D → E (HITL 2), greenfield ou brownfield."""
    mission = cadrer(
        idea,
        mode=mode,  # type: ignore[arg-type]
        existing_repo=existing_repo,
        intent=intent,  # type: ignore[arg-type]
    )
    if mission.mode == "brownfield":
        # garde explicite (≠ assert, non silencé par -O) ; cadrer() garantit déjà l'invariant
        if mission.existing_repo is None:
            raise ValueError("Le mode brownfield exige un existing_repo.")
        target = mission.existing_repo
    else:
        target = workdir / _slug(idea)
    substrate = select_onramp(mission).prepare(mission, target)  # B
    plan = lancer_planification(substrate, planner=_select_planner(mission))  # C — HITL 1
    layout = preparer_sprint(plan, target, baseline=substrate.baseline)  # D
    superviser(layout)  # E — HITL 2


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
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.idea, mode=args.mode, existing_repo=args.repo, intent=args.intent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
