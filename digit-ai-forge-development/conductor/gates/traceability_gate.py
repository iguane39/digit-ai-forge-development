"""Gate de traçabilité des exigences (RV-1, TF-0010) — la doctrine devient oracle exécutable.

Convention documentée dans `../../docs/run-playbook.md` § « Traçabilité des exigences (RV-1) » :
chaque exigence MVP du référentiel `EXIGENCES.json` (forge-conception) doit être citée par au
moins un test, dans sa docstring (``E-042``) ou son nom (``test_x_E_042``). Grep 100 % : un
identifiant MVP jamais cité fait échouer le gate. Fonction pure sur des chemins, testable
hors-ligne — même posture P-06 que `code_gate`/`design_gate` : sans référentiel exploitable,
SKIP tracé, jamais un échec implicite.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from conductor.contracts import GateVerdict

# TF-1780 (lot Produit-83, 15/10/2026) : un nom de test Python ne peut pas porter le tiret
# (`def test_x_E-042():` lève SyntaxError). Le nom cite donc l'exigence par un souligné
# (`test_x_E_042`), que le gate ramène à l'identifiant `E-042` ; la docstring garde le tiret.
ID_PATTERN = re.compile(r"E[-_](\d{3})")
# TF-1779 : les tests d'interface (Vitest, Jest, Playwright) comptent, à condition d'être des
# fichiers de TEST ; un composant qui cite une exigence en commentaire ne la teste pas.
SUFFIXES_TESTS_JS = (".ts", ".tsx", ".js", ".jsx", ".mjs")
MARQUES_TESTS_JS = (".test.", ".spec.")


def _mvp_ids(exigences_json: Path) -> set[str]:
    """Identifiants MVP du référentiel : champ ``palier`` == ``MVP`` s'il est porté, sinon
    l'identifiant est retenu par défaut (repli permissif — un item non palié n'est pas ignoré)."""
    if not exigences_json.exists():
        return set()
    raw = json.loads(exigences_json.read_text(encoding="utf-8"))
    items: list[Any] = raw if isinstance(raw, list) else list(raw.get("exigences", []))
    ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        palier = item.get("palier")
        if palier is None or str(palier).upper() == "MVP":
            ids.add(item_id)
    return ids


def _ids(texte: str) -> set[str]:
    return {f"E-{num}" for num in ID_PATTERN.findall(texte)}


def _est_un_test(path: Path) -> bool:
    if path.suffix == ".py":
        return True
    return path.suffix in SUFFIXES_TESTS_JS and any(m in path.name for m in MARQUES_TESTS_JS)


def _cited_ids(tests_dir: Path) -> set[str]:
    """Identifiants cités par au moins un test (grep sur le nom ET le contenu du fichier)."""
    cited: set[str] = set()
    if not tests_dir.exists():
        return cited
    for path in tests_dir.rglob("*"):
        if not path.is_file() or not _est_un_test(path) or "node_modules" in path.parts:
            continue
        cited.update(_ids(path.name))
        cited.update(_ids(path.read_text(encoding="utf-8", errors="ignore")))
    return cited


def run_traceability_gate(exigences_json: Path, *tests_dirs: Path) -> GateVerdict:
    """P-06 : sans référentiel MVP exploitable, SKIP tracé — jamais un échec implicite.

    Plusieurs dossiers de tests s'additionnent (TF-1779) : `backend/tests`, `e2e`,
    `frontend/src`."""
    mvp_ids = _mvp_ids(exigences_json)
    if not mvp_ids:
        return GateVerdict(
            gate="traceability",
            passed=True,
            findings=[{"skipped": f"aucune exigence MVP exploitable dans {exigences_json}"}],
        )
    cited: set[str] = set()
    for tests_dir in tests_dirs:
        cited |= _cited_ids(tests_dir)
    missing = sorted(mvp_ids - cited)
    return GateVerdict(
        gate="traceability",
        passed=not missing,
        findings=[{"id": mid, "issue": "jamais citée par un test"} for mid in missing],
        log_ref=", ".join(str(d) for d in tests_dirs),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI : ``python -m conductor.gates.traceability_gate <EXIGENCES.json> <tests_dir>…``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print(
            "usage: python -m conductor.gates.traceability_gate <EXIGENCES.json> <tests_dir>"
            " [<tests_dir>…]",
            file=sys.stderr,
        )
        return 2
    verdict = run_traceability_gate(Path(args[0]), *(Path(a) for a in args[1:]))
    if verdict.passed:
        print("traceability gate: PASS")
        return 0
    print(f"traceability gate: FAIL ({len(verdict.findings)} exigence(s) MVP non citée(s))",
          file=sys.stderr)
    for f in verdict.findings:
        print(f"  - {f.get('id', f.get('skipped', '?'))}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
