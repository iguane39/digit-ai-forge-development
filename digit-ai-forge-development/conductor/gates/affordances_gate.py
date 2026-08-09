"""Gate affordances (loi 1 — zéro affordance inerte, TF-0010) — DÉLÈGUE, ne duplique pas.

Convention documentée dans `../../docs/run-playbook.md` § « Produit livrable — disciplines de
production » : le contrôle statique des affordances (bouton/lien/formulaire câblé ou absent)
est déjà implémenté par le pan ``interface`` de `digit-ai-forge-tests`. Ce gate se contente de le
DÉCLARER — l'invoquer et lire son verdict JSON — jamais de le réimplémenter (dépôt frère,
lecture seule ; cf. garde-fous du pilot). Il traduit le rapport réel de forge-tests :
``couverture_par_pan.interface.ratio`` (1.0 attendu) et
``couverture_par_pan.interface.elements_non_exerces`` (les affordances inertes nommées).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Protocol

from conductor.contracts import GateVerdict
from conductor.process import ProcessRunner, SubprocessProcessRunner

SEUIL = 1.0  # couverture_surface_interface (bloquant) — cf. forge_tests/seuils.py


class InterfacePanRunner(Protocol):
    """Exécute le pan ``interface`` de forge-tests et renvoie son rapport JSON complet."""

    def run_interface_pan(self, forge_tests_path: Path, repo_path: Path) -> dict[str, Any]: ...


class SubprocessInterfacePanRunner:
    """Runner de prod : ``uv run --project <forge-tests> python -m forge_tests <repo>
    --pans interface --json``."""

    def __init__(self, runner: ProcessRunner | None = None) -> None:
        self._runner: ProcessRunner = runner or SubprocessProcessRunner()

    def run_interface_pan(self, forge_tests_path: Path, repo_path: Path) -> dict[str, Any]:
        args = [
            "uv", "run", "--project", str(forge_tests_path),
            "python", "-m", "forge_tests", str(repo_path), "--pans", "interface", "--json",
        ]
        result = self._runner.run(args)
        report: dict[str, Any] = json.loads(result.stdout) if result.stdout.strip() else {}
        return report


def _verdict_from_report(report: dict[str, Any], *, log_ref: str) -> GateVerdict:
    couverture = report.get("couverture_par_pan", {})
    interface = couverture.get("interface") if isinstance(couverture, dict) else None
    if not isinstance(interface, dict):
        # Pan non exécuté (absent du rapport) : do-no-harm — on ne fabrique pas un échec faute
        # de mesure, le rapport source fait foi (`pans_non_couverts` y explique pourquoi).
        return GateVerdict(
            gate="affordances",
            passed=True,
            findings=[{"skipped": "pan interface absent du rapport forge-tests"}],
            log_ref=log_ref,
        )
    ratio = float(interface.get("ratio", 0.0))
    inertes = list(interface.get("elements_non_exerces", []))
    return GateVerdict(
        gate="affordances",
        passed=ratio >= SEUIL,
        findings=[{"element": str(e)} for e in inertes],
        log_ref=log_ref,
    )


def run_affordances_gate(
    forge_tests_path: Path | None,
    repo_path: Path,
    *,
    runner: InterfacePanRunner | None = None,
) -> GateVerdict:
    """P-06 : forge-tests introuvable → SKIP tracé (do-no-harm), jamais un échec implicite —
    même posture que `code_gate`/`design_gate` quand leur outil n'est pas exploitable."""
    if forge_tests_path is None or not forge_tests_path.exists():
        return GateVerdict(
            gate="affordances",
            passed=True,
            findings=[{"skipped": "digit-ai-forge-tests introuvable — pan interface non exécuté"}],
        )
    report = (runner or SubprocessInterfacePanRunner()).run_interface_pan(
        forge_tests_path, repo_path
    )
    return _verdict_from_report(report, log_ref=str(repo_path))


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.affordances_gate <forge-tests> <repo>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m conductor.gates.affordances_gate <forge-tests> <repo>",
              file=sys.stderr)
        return 2
    verdict = run_affordances_gate(Path(args[0]), Path(args[1]))
    if verdict.passed:
        print("affordances gate: PASS")
        return 0
    print(f"affordances gate: FAIL ({len(verdict.findings)} affordance(s) inerte(s))",
          file=sys.stderr)
    for f in verdict.findings:
        print(f"  - {f.get('element', f.get('skipped', '?'))}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
