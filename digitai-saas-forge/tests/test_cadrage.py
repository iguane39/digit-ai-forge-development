"""Vérifie l'étape A : MissionConfig produite, briques de t0 forcées (décision 05)."""

from __future__ import annotations

import pytest

from conductor.cadrage import cadrer
from conductor.catalog import T0_BRICKS
from conductor.contracts import BrickChoice


def test_cadrer_forces_t0_bricks_as_build() -> None:
    cfg = cadrer("un CRM pour artisans")
    by_name = {b.name: b for b in cfg.saas_scope}
    for name in T0_BRICKS:
        assert by_name[name].decision == "build"


def test_cadrer_t0_cannot_be_skipped() -> None:
    cfg = cadrer("idée", bricks=[BrickChoice(name="rbac", decision="skip")])
    rbac = next(b for b in cfg.saas_scope if b.name == "rbac")
    assert rbac.decision == "build"  # override de t0


def test_cadrer_keeps_extra_brick() -> None:
    cfg = cadrer("idée", bricks=[BrickChoice(name="billing", decision="buy")])
    assert any(b.name == "billing" and b.decision == "buy" for b in cfg.saas_scope)


def test_cadrer_rejects_unknown_brick() -> None:
    with pytest.raises(ValueError, match="inconnue"):
        cadrer("idée", bricks=[BrickChoice(name="quantum-blockchain", decision="build")])


def test_cadrer_rejects_empty_idea() -> None:
    with pytest.raises(ValueError, match="vide"):
        cadrer("   ")


def test_cadrer_default_target_and_charter() -> None:
    cfg = cadrer("idée")
    assert cfg.target == "fastapi-saas"
    assert cfg.style_slug == "digitai"
