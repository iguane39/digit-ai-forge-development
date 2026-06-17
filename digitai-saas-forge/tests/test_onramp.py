"""Substrate = sortie d'onramp ; le protocole Onramp est structurel."""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.onramp.base import Onramp, Substrate
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
