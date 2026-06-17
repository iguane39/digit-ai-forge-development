"""Substrate = sortie d'onramp ; le protocole Onramp est structurel."""

from __future__ import annotations

from pathlib import Path

from conductor.cadrage import cadrer
from conductor.contracts import MissionConfig
from conductor.onramp import select_onramp
from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.scaffold_onramp import ScaffoldOnramp
from conductor.profiles import FASTAPI_SAAS


def test_substrate_defaults_baseline_and_archmap_to_none() -> None:
    s = Substrate(
        repo_path=Path("repo"),
        profile=FASTAPI_SAAS,
        design_md_path=Path("repo/design/DESIGN.md"),
    )
    assert s.baseline is None  # rempli en BA
    assert s.arch_map is None  # rempli en BC/BB


def test_fake_onramp_satisfies_protocol() -> None:
    class FakeOnramp:
        def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    cfg = MissionConfig(idea="test", brand_charter=Path("d.md"), style_slug="minimal")
    onramp: Onramp = FakeOnramp()
    s = onramp.prepare(cfg, Path("x"))
    assert s.profile is FASTAPI_SAAS


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def run(self, command: str, cwd: Path) -> int:
        self.calls.append((command, cwd))
        return 0


def test_scaffold_onramp_generates_and_returns_substrate(tmp_path: Path) -> None:
    runner = _FakeRunner()
    substrate = ScaffoldOnramp(runner=runner).prepare(cadrer("un CRM"), tmp_path / "app")
    assert substrate.profile is FASTAPI_SAAS
    assert substrate.repo_path == tmp_path / "app"
    assert substrate.baseline is None  # greenfield : rien à préserver
    assert any("copier copy" in c for c, _ in runner.calls)  # scaffold-first exécuté


def test_select_onramp_greenfield_is_scaffold() -> None:
    mission = MissionConfig(idea="test", brand_charter=Path("d.md"), style_slug="minimal")
    assert isinstance(select_onramp(mission), ScaffoldOnramp)
