"""Le TargetProfile réifie le contrat d'une stack ; FASTAPI_SAAS = la forge actuelle."""

from __future__ import annotations

from pathlib import Path

from conductor.catalog import CATALOG
from conductor.profiles import (
    FASTAPI_SAAS,
    NODE_TS,
    TargetProfile,
    derive_profile,
    profile_for_stack,
)


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


def test_fastapi_profile_has_roles_and_managers() -> None:
    """P-11 : rôle → répertoire et rôle → gestionnaire (backend=uv, frontend=npm)."""
    assert FASTAPI_SAAS.roles == {"backend": "backend", "frontend": "frontend"}
    assert FASTAPI_SAAS.pkg_managers == {"backend": "uv", "frontend": "npm"}


def test_derive_profile_reads_package_json_scripts(tmp_path: Path) -> None:
    """P-09 : test/build dérivés des scripts package.json + gestionnaire du lockfile."""
    (tmp_path / "package.json").write_text(
        '{"scripts": {"test": "vitest", "build": "tsc"}}', encoding="utf-8"
    )
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    p = derive_profile(tmp_path, NODE_TS)
    assert p.test_cmd == ["pnpm", "run", "test"]
    assert p.build_cmd == ["pnpm", "run", "build"]
    assert p.lint_cmd is None  # pas de script lint → non dérivé


def test_derive_profile_falls_back_to_makefile(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("test:\n\tpytest\nbuild:\n\ttrue\n", encoding="utf-8")
    p = derive_profile(tmp_path, FASTAPI_SAAS)
    assert p.test_cmd == ["make", "test"]


def test_derive_profile_no_markers_returns_base(tmp_path: Path) -> None:
    assert derive_profile(tmp_path, FASTAPI_SAAS) is FASTAPI_SAAS
