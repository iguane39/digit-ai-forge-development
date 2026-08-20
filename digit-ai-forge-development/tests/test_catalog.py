"""Vérifie le catalogue des 11 briques (spike S-3) et la résolution des briques de t0."""

from __future__ import annotations

from conductor.catalog import CATALOG, T0_BRICKS, BrickAction, resolve_bricks
from conductor.contracts import BrickChoice


def test_catalog_has_eleven_bricks() -> None:
    assert len(CATALOG) == 11


def test_actions_are_role_based() -> None:
    """P-11 : les actions référencent un rôle + args (list[str]), plus de chaîne shell `cd … &&`."""
    billing = CATALOG["billing"].actions
    assert billing and isinstance(billing[0], BrickAction)
    assert billing[0].role == "backend"
    assert billing[0].args == ["{pm}", "add", "stripe"]
    assert CATALOG["analytics"].actions[0].role == "frontend"


def test_t0_bricks_are_build_and_flagged() -> None:
    for name in T0_BRICKS:
        spec = CATALOG[name]
        assert spec.t0 is True
        assert spec.default_decision == "build"


def test_resolve_always_includes_t0_even_with_empty_scope() -> None:
    resolved = [b.name for b in resolve_bricks([])]
    for name in T0_BRICKS:
        assert name in resolved


def test_resolve_honore_le_skip_t0_et_force_l_absence() -> None:
    """TF-0406 (RF-8) : ce test affirmait « t0 indéboulonnable » — c'était le DÉFAUT mesuré.
    Le contrat expose `decision: build|buy|skip` ; l'écraser en silence était le contournement
    que la doctrine interdit (pour une vitrine sans espace connecté, multi-tenancy/rbac/auth-sso
    étaient greffées sans objet). Le défaut reste protecteur : une t0 ABSENTE est greffée ;
    seul un `skip` EXPLICITE dit quelque chose, et ce qu'il dit est respecté."""
    scope = [
        BrickChoice(name="multi-tenancy", decision="skip"),  # t0 skip EXPLICITE → honoré
        BrickChoice(name="billing", decision="skip"),  # non-t0 skip → exclu
        BrickChoice(name="jobs-async", decision="build"),  # inclus
    ]
    resolved = [b.name for b in resolve_bricks(scope)]
    assert "multi-tenancy" not in resolved  # le skip explicite est HONORÉ
    assert "rbac" in resolved and "auth-sso" in resolved  # les t0 ABSENTES restent forcées
    assert "billing" not in resolved
    assert "jobs-async" in resolved


def test_resolve_orders_t0_first() -> None:
    scope = [BrickChoice(name="billing", decision="buy")]
    resolved = [b.name for b in resolve_bricks(scope)]
    assert resolved[: len(T0_BRICKS)] == list(T0_BRICKS)
    assert resolved[-1] == "billing"
