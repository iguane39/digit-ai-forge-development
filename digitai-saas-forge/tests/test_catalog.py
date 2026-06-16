"""Vérifie le catalogue des 11 briques (spike S-3) et la résolution des briques de t0."""

from __future__ import annotations

from conductor.catalog import CATALOG, T0_BRICKS, resolve_bricks
from conductor.contracts import BrickChoice


def test_catalog_has_eleven_bricks() -> None:
    assert len(CATALOG) == 11


def test_t0_bricks_are_build_and_flagged() -> None:
    for name in T0_BRICKS:
        spec = CATALOG[name]
        assert spec.t0 is True
        assert spec.default_decision == "build"


def test_resolve_always_includes_t0_even_with_empty_scope() -> None:
    resolved = [b.name for b in resolve_bricks([])]
    for name in T0_BRICKS:
        assert name in resolved


def test_resolve_ignores_skip_but_keeps_t0() -> None:
    scope = [
        BrickChoice(name="multi-tenancy", decision="skip"),  # t0 → ignoré, forcé quand même
        BrickChoice(name="billing", decision="skip"),  # non-t0 skip → exclu
        BrickChoice(name="jobs-async", decision="build"),  # inclus
    ]
    resolved = [b.name for b in resolve_bricks(scope)]
    assert "multi-tenancy" in resolved  # t0 indéboulonnable
    assert "billing" not in resolved
    assert "jobs-async" in resolved


def test_resolve_orders_t0_first() -> None:
    scope = [BrickChoice(name="billing", decision="buy")]
    resolved = [b.name for b in resolve_bricks(scope)]
    assert resolved[: len(T0_BRICKS)] == list(T0_BRICKS)
    assert resolved[-1] == "billing"
