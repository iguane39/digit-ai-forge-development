"""Le TargetProfile réifie le contrat d'une stack ; FASTAPI_SAAS = la forge actuelle."""

from __future__ import annotations

from conductor.catalog import CATALOG
from conductor.profiles import FASTAPI_SAAS, NODE_TS, TargetProfile, profile_for_stack


def test_fastapi_profile_reifies_current_behavior() -> None:
    assert FASTAPI_SAAS.name == "fastapi-saas"
    assert FASTAPI_SAAS.code_check == "uv run pytest"
    assert FASTAPI_SAAS.has_ui is True
    assert FASTAPI_SAAS.design_md_path == "design/DESIGN.md"
    assert FASTAPI_SAAS.brick_catalog == CATALOG  # le catalogue actuel devient le brick_catalog


def test_enforceable_reflects_gates() -> None:
    assert FASTAPI_SAAS.enforceable == {"code": True, "design": True}


def test_profile_without_code_check_disables_code_gate() -> None:
    p = TargetProfile(name="doc-only", code_check=None, has_ui=False)
    assert p.enforceable == {"code": False, "design": False}


def test_node_ts_profile() -> None:
    assert NODE_TS.name == "node-ts"
    assert NODE_TS.code_check == "npm test"
    assert NODE_TS.has_ui is True
    assert NODE_TS.brick_catalog == {}


def test_profile_for_stack_maps_known_stacks() -> None:
    assert profile_for_stack("fastapi") is FASTAPI_SAAS
    assert profile_for_stack("node-ts") is NODE_TS
    assert profile_for_stack("rails") is None
