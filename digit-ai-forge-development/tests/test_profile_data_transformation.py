"""Profil d'un produit DATA (TF-0861, lot L4 de l'étude d'opportunité du pilot du 07/09/2026).

Un projet de transformation Silver/Gold se reconnaît à son marqueur racine `dbt_project.yml`,
se résout en profil curé `data-transformation` (aucune UI : le gate design ne s'applique pas ;
le gate code joue `dbt test`), et le marqueur data prime sur un `pyproject.toml` d'outillage.
"""

from __future__ import annotations

from pathlib import Path

from conductor.onramp.detect import detect_stack
from conductor.profiles import DATA_TRANSFORMATION, profile_for_stack, resolve_profile


def test_detect_stack_data_transformation(tmp_path: Path) -> None:
    (tmp_path / "dbt_project.yml").write_text("name: ventes_silver_gold\nversion: '1.0.0'\n", encoding="utf-8")
    assert detect_stack(tmp_path) == "data-transformation"


def test_data_marker_primes_over_pyproject(tmp_path: Path) -> None:
    (tmp_path / "dbt_project.yml").write_text("name: ventes\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'outillage'\n", encoding="utf-8")
    assert detect_stack(tmp_path) == "data-transformation"


def test_profile_data_transformation_contract() -> None:
    profile = profile_for_stack("data-transformation")
    assert profile is DATA_TRANSFORMATION
    assert profile.has_ui is False
    assert profile.enforceable == {"code": True, "design": False}
    assert profile.code_check == "dbt test"
    assert profile.commands["transformations"].build == "dbt docs generate"


def test_resolve_profile_curated_data(tmp_path: Path) -> None:
    (tmp_path / "dbt_project.yml").write_text("name: ventes\n", encoding="utf-8")
    resolution = resolve_profile(tmp_path)
    assert resolution.confidence == "curated"
    assert resolution.profile.name == "data-transformation"
