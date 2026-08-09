"""Gate de traçabilité des exigences (RV-1, TF-0010) — la doctrine devient oracle exécutable.

Convention documentée dans `../../docs/run-playbook.md` § « Traçabilité des exigences (RV-1) » :
chaque exigence MVP du référentiel `EXIGENCES.json` (forge-conception) doit être citée par au
moins un test, dans son nom ou sa docstring (``E-042``). Grep 100 % : un identifiant MVP jamais
cité fait échouer le gate. Fonction pure sur des chemins, testable hors-ligne — même posture
P-06 que `code_gate`/`design_gate` : sans référentiel exploitable, SKIP tracé, jamais un échec
implicite.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from conductor.contracts import GateVerdict

ID_PATTERN = re.compile(r"E-\d{3}")


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


def _cited_ids(tests_dir: Path) -> set[str]:
    """Identifiants cités par au moins un test (grep sur le nom ET le contenu du fichier)."""
    cited: set[str] = set()
    if not tests_dir.exists():
        return cited
    for path in tests_dir.rglob("*.py"):
        cited.update(ID_PATTERN.findall(path.name))
        cited.update(ID_PATTERN.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return cited


def run_traceability_gate(exigences_json: Path, tests_dir: Path) -> GateVerdict:
    """P-06 : sans référentiel MVP exploitable, SKIP tracé — jamais un échec implicite."""
    mvp_ids = _mvp_ids(exigences_json)
    if not mvp_ids:
        return GateVerdict(
            gate="traceability",
            passed=True,
            findings=[{"skipped": f"aucune exigence MVP exploitable dans {exigences_json}"}],
        )
    missing = sorted(mvp_ids - _cited_ids(tests_dir))
    return GateVerdict(
        gate="traceability",
        passed=not missing,
        findings=[{"id": mid, "issue": "jamais citée par un test"} for mid in missing],
        log_ref=str(tests_dir),
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.traceability_gate <EXIGENCES.json> <tests_dir>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(
            "usage: python -m conductor.gates.traceability_gate <EXIGENCES.json> <tests_dir>",
            file=sys.stderr,
        )
        return 2
    verdict = run_traceability_gate(Path(args[0]), Path(args[1]))
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
