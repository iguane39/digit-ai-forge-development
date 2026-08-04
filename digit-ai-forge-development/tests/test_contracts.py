"""Vérifie que les contrats du pipeline instancient et portent les invariants clés."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from conductor.contracts import (
    BadConfig,
    BadSprintLayout,
    BmadPlan,
    MissionConfig,
    Story,
)


def test_mission_config_minimal() -> None:
    cfg = MissionConfig(
        idea="un CRM pour artisans",
        brand_charter=Path("design/DESIGN.md"),
        style_slug="digitai",
    )
    assert cfg.target == "fastapi-saas"  # cible par défaut, paramétrable (décision 08)
    assert cfg.saas_scope == []


def test_bad_config_defaults_match_spike_s1b() -> None:
    cfg = BadConfig()
    assert cfg.max_parallel_stories == 3
    assert cfg.model_standard == "sonnet"
    assert cfg.model_quality == "opus"
    assert cfg.run_ci_locally is False


def test_auto_pr_merge_is_locked_false() -> None:
    """HITL 2 (décision 07) : auto_pr_merge ne peut JAMAIS être true."""
    assert BadConfig().auto_pr_merge is False
    with pytest.raises(ValidationError):
        BadConfig(auto_pr_merge=True)  # type: ignore[arg-type]


def test_story_status_enum() -> None:
    s = Story(id="0.1", epic="0", title="Squelette")
    assert s.status == "backlog"
    with pytest.raises(ValidationError):
        Story(id="0.2", epic="0", title="x", status="merged")  # type: ignore[arg-type]


def test_layout_carries_bad_config() -> None:
    layout = BadSprintLayout(
        project_root=Path("."),
        epics_md=Path("_bmad-output/planning-artifacts/epics.md"),
        sprint_status_yaml=Path("_bmad-output/implementation-artifacts/sprint-status.yaml"),
        bmad_config_yaml=Path("_bmad/config.yaml"),
    )
    assert layout.config.auto_pr_merge is False


def test_bmad_plan_hitl_gate_defaults_false() -> None:
    plan = BmadPlan(
        prd_path=Path("docs/PRD.md"),
        architecture_path=Path("docs/architecture.md"),
        epics_md=Path("_bmad-output/planning-artifacts/epics.md"),
    )
    assert plan.hitl1_approved is False  # HITL 1 non franchi par défaut
