"""Verrouille la correction du piège S-2.3 : le gate design bloque sur le CONTENU
du JSON, jamais sur l'exit code natif du linter (qui laisse passer les warnings)."""

from __future__ import annotations

from conductor.gates.design_gate import evaluate_findings


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
