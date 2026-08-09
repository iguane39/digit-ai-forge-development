"""Gate frontière démo/production (RV-3, TF-0010) — la doctrine devient oracle exécutable.

Convention documentée dans `../../docs/run-playbook.md` § « Produit livrable — disciplines de
production » : tout artefact de démonstration (fixtures, comptes, données simulées, endpoints
de peuplement) vit derrière un drapeau d'environnement explicite (``*_MODE_DEMO`` ou équivalent),
absent par défaut. Contrôle STATIQUE, même posture heuristique que le pan ``interface`` de
forge-tests (coïncidence de chaîne, pas d'exécution d'un build réel) : un marqueur de démo
présent dans un fichier source sans référence au drapeau dans ce même fichier est un finding —
le fichier promet une frontière qu'il ne pose nulle part.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from conductor.contracts import GateVerdict

DEMO_MARKER = re.compile(
    r"fixture|d[ée]mo|jeu[_-]de[_-]|donn[ée]es?[_-]simul|fournisseur[_-]simul", re.IGNORECASE
)
GUARD_MARKER = re.compile(r"[A-Za-z][A-Za-z0-9]*_MODE_DEMO|MODE_DEMO", re.IGNORECASE)

# Hors périmètre : suites de tests (fixtures de test légitimes) et migrations de peuplement
# datées (loi 4 — une donnée volatile documentée n'est pas un défaut démo).
_EXCLUDED_PARTS = ("test", "tests", "migrations")


def _is_excluded(path: Path) -> bool:
    return any(part.lower() in _EXCLUDED_PARTS for part in path.parts)


def run_demo_markers_gate(source_dir: Path) -> GateVerdict:
    """P-06 : sans arborescence source, SKIP tracé — jamais un échec implicite."""
    if not source_dir.exists():
        return GateVerdict(
            gate="demo-markers",
            passed=True,
            findings=[{"skipped": f"arborescence source absente : {source_dir}"}],
        )
    findings: list[dict[str, str]] = []
    for path in sorted(source_dir.rglob("*.py")):
        if not path.is_file() or _is_excluded(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if DEMO_MARKER.search(text) and not GUARD_MARKER.search(text):
            findings.append(
                {"file": str(path), "issue": "marqueur de démo sans drapeau *_MODE_DEMO associé"}
            )
    return GateVerdict(
        gate="demo-markers", passed=not findings, findings=findings, log_ref=str(source_dir)
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.demo_markers_gate <source_dir>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m conductor.gates.demo_markers_gate <source_dir>", file=sys.stderr)
        return 2
    verdict = run_demo_markers_gate(Path(args[0]))
    if verdict.passed:
        print("demo-markers gate: PASS")
        return 0
    print(f"demo-markers gate: FAIL ({len(verdict.findings)} fichier(s) sans drapeau)",
          file=sys.stderr)
    for f in verdict.findings:
        print(f"  - {f['file']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
