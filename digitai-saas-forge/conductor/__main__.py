"""CLI du conductor — point d'entrée unique `conductor run "<idée>"`.

Enchaîne les cinq étapes dans l'ordre structurel A → B → C → D → E. L'ordre
scaffold-first (B avant C) est un invariant, pas une option (décision 02).
La logique de chaque étape arrive aux Epics 1 et 3 ; ici on câble la séquence.
"""

from __future__ import annotations

import argparse

from conductor import __version__
from conductor.bmad_bridge import lancer_planification
from conductor.cadrage import cadrer
from conductor.scaffold import scaffold
from conductor.sprint_config import preparer_sprint
from conductor.supervisor import superviser


def run(idea: str) -> None:
    """Orchestration de bout en bout : A → B → C (HITL 1) → D → E (HITL 2)."""
    mission = cadrer(idea)  # A
    built = scaffold(mission)  # B — scaffold-first (avant tout agent)
    plan = lancer_planification(built)  # C — pose HITL 1
    layout = preparer_sprint(plan)  # D — placement & config (pas de graphe, S-1)
    superviser(layout)  # E — /bad + double gate, pose HITL 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conductor", description="Accélérateur SaaS Digit-AI")
    parser.add_argument("--version", action="version", version=f"conductor {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="idée → SaaS PR-ready")
    run_p.add_argument("idea", help="l'intention produit, ex. \"un CRM pour artisans\"")
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.idea)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
