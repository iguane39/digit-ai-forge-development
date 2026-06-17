"""Vérifie l'export de tokens (charte → code) via un runner factice."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.tokens import ExportFormat, export_tokens


class FakeExportRunner:
    def __init__(self, rc: int, content: str) -> None:
        self.rc = rc
        self.content = content
        self.calls: list[tuple[Path, str]] = []

    def export(self, design_md: Path, fmt: ExportFormat) -> tuple[int, str]:
        self.calls.append((design_md, fmt))
        return self.rc, self.content


def test_export_css_tailwind_writes_theme(tmp_path: Path) -> None:
    runner = FakeExportRunner(0, ":root { --primary: #2563eb; }")
    dest = export_tokens(Path("design/DESIGN.md"), "css-tailwind", tmp_path, runner=runner)
    assert dest.name == "theme.css"
    assert "--primary" in dest.read_text(encoding="utf-8")


def test_export_dtcg_writes_tokens(tmp_path: Path) -> None:
    runner = FakeExportRunner(0, '{"color": {}}')
    dest = export_tokens(Path("design/DESIGN.md"), "dtcg", tmp_path, runner=runner)
    assert dest.name == "tokens.json"


def test_export_raises_on_failure(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Export"):
        export_tokens(Path("design/DESIGN.md"), "dtcg", tmp_path, runner=FakeExportRunner(1, ""))


def test_export_raises_on_empty_output(tmp_path: Path) -> None:
    runner = FakeExportRunner(0, "  ")
    with pytest.raises(RuntimeError):
        export_tokens(Path("design/DESIGN.md"), "css-tailwind", tmp_path, runner=runner)
