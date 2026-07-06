"""Verrouille la correction du piège S-2.3 : le gate design bloque sur le CONTENU
du JSON, jamais sur l'exit code natif du linter (qui laisse passer les warnings)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.gates.design_gate import evaluate_findings, run_design_gate


def test_clean_report_passes() -> None:
    report = {
        "findings": [
            {"severity": "info", "path": "tokens", "message": "12 tokens defined."},
            {
                "severity": "warning",
                "path": "components.button-primary",
                "message": "contrast ratio 15.42:1 — passes WCAG AA.",
            },
        ],
        "summary": {"errors": 0, "warnings": 1, "info": 1},
    }
    assert evaluate_findings(report).passed is True


def test_contrast_failure_as_warning_still_blocks() -> None:
    """Cas piège : violation WCAG émise en `warning` → exit 0 natif, mais on DOIT bloquer."""
    report = {
        "findings": [
            {
                "severity": "warning",
                "path": "components.cta",
                "message": "contrast ratio 2.1:1 — fails WCAG AA.",
            }
        ],
        "summary": {"errors": 0, "warnings": 1, "info": 0},
    }
    verdict = evaluate_findings(report)
    assert verdict.passed is False
    assert verdict.findings  # le finding bloquant est remonté


def test_native_error_blocks() -> None:
    report = {"findings": [{"severity": "error", "path": "x", "message": "boom"}]}
    assert evaluate_findings(report).passed is False


def test_blocking_rule_field_blocks_regardless_of_severity() -> None:
    report = {
        "findings": [{"severity": "info", "rule": "broken-ref", "path": "p", "message": "ref"}]
    }
    assert evaluate_findings(report).passed is False


def test_empty_report_passes() -> None:
    assert evaluate_findings({}).passed is True
    assert evaluate_findings({"findings": []}).passed is True


class FakeLinter:
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        self.seen: list[Path] = []

    def lint_json(self, design_md: Path) -> dict[str, Any]:
        self.seen.append(design_md)
        return self.report


def test_run_design_gate_passes_with_info_only(tmp_path: Path) -> None:
    """Reproduit le rapport réel de notre DESIGN.md (3 findings info → PASS)."""
    report = {
        "findings": [
            {"severity": "info", "message": "Design system defines 8 colors, 3 typography scales."},
            {"severity": "info", "path": "spacing", "message": "No 'spacing' section defined."},
        ],
        "summary": {"errors": 0, "warnings": 0, "infos": 2},
    }
    linter = FakeLinter(report)
    design_md = tmp_path / "DESIGN.md"
    design_md.write_text("# design", encoding="utf-8")
    verdict = run_design_gate(design_md, linter=linter)
    assert verdict.passed is True
    assert linter.seen == [design_md]


def test_run_design_gate_blocks_on_wcag_warning(tmp_path: Path) -> None:
    report = {"findings": [{"severity": "warning", "message": "contrast 2.1:1 - fails WCAG AA."}]}
    design_md = tmp_path / "DESIGN.md"
    design_md.write_text("# design", encoding="utf-8")
    verdict = run_design_gate(design_md, linter=FakeLinter(report))
    assert verdict.passed is False


def test_run_design_gate_skips_when_absent(tmp_path: Path) -> None:
    """P-10 : DESIGN.md absent → skip tracé (do-no-harm), le linter n'est pas appelé."""
    linter = FakeLinter({"findings": [{"severity": "error", "message": "boom"}]})
    verdict = run_design_gate(tmp_path / "nope.md", linter=linter)
    assert verdict.passed is True
    assert linter.seen == []
    assert verdict.findings and "skipped" in verdict.findings[0]


def test_npx_design_linter_uses_process_runner_list_args() -> None:
    """P-01 : npx passe par le ProcessRunner (args en liste, shutil.which), pas en nom nu."""
    from conductor.gates.design_gate import NpxDesignLinter
    from conductor.process import ProcessResult

    seen: dict[str, list[str]] = {}

    class _FakeProc:
        def run(self, args: Any, *, cwd: Any = None, timeout_s: int = 300) -> ProcessResult:
            seen["args"] = list(args)
            return ProcessResult(0, '{"findings": []}', "")

    report = NpxDesignLinter(runner=_FakeProc()).lint_json(Path("d/DESIGN.md"))
    assert report == {"findings": []}
    assert seen["args"][0] == "npx" and "--yes" in seen["args"]
    assert str(Path("d/DESIGN.md")) in seen["args"]
