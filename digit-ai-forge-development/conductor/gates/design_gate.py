"""Gate design — design.md lint + POLITIQUE DE SÉVÉRITÉ de la forge.

⚠ Piège S-2.3 : `design.md lint` ne sort en exit code 1 que pour des `error`. Or le
contraste WCAG peut être émis en `warning` → exit 0. Et il n'existe aucun flag
`--strict`. Se fier à l'exit code laisserait donc passer une violation WCAG.

Solution : on lance `lint --format json` et on applique NOTRE politique sur le JSON,
quelle que soit la sévérité native. `evaluate_findings` ci-dessous est pure et
testable hors-ligne ; l'invocation du CLI (`run_design_gate`) arrive en Epic 2 (2.2).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Protocol

from conductor.contracts import GateVerdict
from conductor.process import ProcessRunner, SubprocessProcessRunner

# Outil de gate design, épinglé (décision 06 / risque 7 — alpha). Adopté, jamais forké.
DESIGN_MD_PKG = "@google/design.md@0.3.0"

# Règles design.md (parmi les 9) qui DOIVENT bloquer le merge, quelle que soit la
# sévérité native renvoyée par le linter. Aligné sur le dossier : refs, contraste,
# structure on-system.
BLOCKING_RULES: frozenset[str] = frozenset(
    {
        "broken-ref",
        "missing-primary",
        "missing-sections",
        "missing-typography",
        "section-order",
        "contrast-ratio",
    }
)

# Motifs de message qui trahissent un échec même sans champ `rule` explicite
# (le finding JSON peut ne porter que severity/path/message — cf. exemple S-2.4).
BLOCKING_MESSAGE_PATTERNS: tuple[str, ...] = ("fails wcag", "broken reference", "missing")


def _finding_blocks(finding: dict[str, Any]) -> bool:
    """Un finding bloque-t-il, selon la politique de la forge ?"""
    if str(finding.get("severity", "")).lower() == "error":
        return True
    rule = str(finding.get("rule", "")).lower()
    if rule in BLOCKING_RULES:
        return True
    message = str(finding.get("message", "")).lower()
    return any(pat in message for pat in BLOCKING_MESSAGE_PATTERNS)


def evaluate_findings(report: dict[str, Any]) -> GateVerdict:
    """Applique la politique de sévérité de la forge au rapport JSON de design.md lint.

    Le verdict ne dépend PAS de l'exit code du CLI mais du contenu des findings.
    """
    findings = report.get("findings", []) or []
    blocking = [f for f in findings if _finding_blocks(f)]
    return GateVerdict(
        gate="design",
        passed=not blocking,
        findings=[
            {
                "severity": str(f.get("severity", "")),
                "path": str(f.get("path", "")),
                "message": str(f.get("message", "")),
            }
            for f in blocking
        ],
    )


class DesignLinter(Protocol):
    """Produit le rapport JSON de design.md lint pour un fichier DESIGN.md."""

    def lint_json(self, design_md: Path) -> dict[str, Any]: ...


class NpxDesignLinter:
    """Linter de production : invoque le CLI épinglé via l'alias de bin `designmd`.

    On utilise l'alias sans point (`designmd`) plutôt que `@google/design.md` : la
    résolution npx du nom contenant un point est fragile selon les plateformes.
    """

    def __init__(self, runner: ProcessRunner | None = None) -> None:
        self._runner: ProcessRunner = runner or SubprocessProcessRunner()

    def lint_json(self, design_md: Path) -> dict[str, Any]:
        args = [
            "npx", "--yes", "-p", DESIGN_MD_PKG,
            "designmd", "lint", "--format", "json", str(design_md),
        ]
        result = self._runner.run(args)
        report: dict[str, Any] = json.loads(result.stdout) if result.stdout.strip() else {}
        return report


def run_design_gate(design_md: Path, *, linter: DesignLinter | None = None) -> GateVerdict:
    """Lint le DESIGN.md puis applique la politique de sévérité de la forge (S-2.3).

    Le verdict dépend du CONTENU du rapport, jamais de l'exit code du CLI.
    """
    if not design_md.exists():
        # P-10 : do-no-harm — pas de DESIGN.md → gate design SKIP tracé, jamais un échec.
        return GateVerdict(
            gate="design", passed=True, findings=[{"skipped": f"DESIGN.md absent : {design_md}"}]
        )
    report = (linter or NpxDesignLinter()).lint_json(design_md)
    return evaluate_findings(report)


def main(argv: list[str] | None = None) -> int:
    """Entrée CI : lit un rapport JSON et renvoie 1 si la politique bloque (FR-G3).

    Usage : `python -m conductor.gates.design_gate findings.json`
    """
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: python -m conductor.gates.design_gate <findings.json>", file=sys.stderr)
        return 2
    report = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    verdict = evaluate_findings(report)
    if verdict.passed:
        print("design gate: PASS")
        return 0
    print(f"design gate: FAIL ({len(verdict.findings)} finding(s) bloquant(s))", file=sys.stderr)
    for f in verdict.findings:
        print(f"  - [{f['severity']}] {f['path']}: {f['message']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
