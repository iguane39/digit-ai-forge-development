"""Gate de non-régression : un check vert dans la baseline ne doit pas passer au rouge."""

from __future__ import annotations

from conductor.gates.regression_gate import evaluate_regression


def test_no_regression_passes() -> None:
    v = evaluate_regression({"code": True, "design": True}, {"code": True, "design": True})
    assert v.passed is True
    assert v.gate == "regression"


def test_green_to_red_blocks() -> None:
    v = evaluate_regression({"code": True}, {"code": False})
    assert v.passed is False
    assert v.findings and v.findings[0]["check"] == "code"


def test_red_baseline_not_aggravated_passes() -> None:
    v = evaluate_regression({"code": False}, {"code": False})
    assert v.passed is True


def test_empty_baseline_passes() -> None:
    assert evaluate_regression({}, {"code": True}).passed is True
