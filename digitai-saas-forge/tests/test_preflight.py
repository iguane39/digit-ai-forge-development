"""Préflight outils (P-13) : shutil.which par outil + message actionnable."""

from __future__ import annotations

import pytest

from conductor.preflight import check_tools, preflight_message


def test_all_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("conductor.preflight.shutil.which", lambda name: "/bin/" + name)
    report = check_tools(["git", "uv", "gh"])
    assert report.ok is True
    assert report.missing == []
    assert "OK" in preflight_message(report)


def test_reports_missing_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
    present = {"git", "uv"}
    monkeypatch.setattr(
        "conductor.preflight.shutil.which", lambda name: "/bin/x" if name in present else None
    )
    report = check_tools(["git", "npx", "uv", "copier"])
    assert report.ok is False
    assert report.missing == ["copier", "npx"]  # trié
    msg = preflight_message(report)
    assert "copier" in msg and "npx" in msg and "KO" in msg
