"""Contrats d'interface typés du pipeline A→E.

Chaque étape consomme et produit un de ces modèles (pipeline typé, invariant
d'architecture §8.3). Les schémas sont alignés sur ../../docs/architecture.md §3
et sur les résultats des spikes S-1/S-1b (format réel attendu par BAD).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# --- A → B ------------------------------------------------------------------

BrickDecision = Literal["build", "buy", "skip"]


class BrickChoice(BaseModel):
    """Une brique SaaS et sa décision build-vs-buy (cf. Toolkit, spike S-3)."""

    name: str  # "multi-tenancy", "rbac", "auth-sso", "billing", ...
    decision: BrickDecision


class MissionConfig(BaseModel):
    """Sortie de l'étape A (cadrage). Paramétrable — aucune valeur figée (décision 08)."""

    idea: str
    target: str = "fastapi-saas"
    budget: str | None = None
    deadline: str | None = None
    # multi-tenancy / rbac / auth-sso sont forcés à t0 (décision canonique 05).
    saas_scope: list[BrickChoice] = Field(default_factory=list)
    brand_charter: Path  # chemin vers le DESIGN.md client
    style_slug: str  # style awesome-design-skills retenu (copie locale, DE-2)


# --- B → C ------------------------------------------------------------------


class ScaffoldResult(BaseModel):
    """Sortie de l'étape B (scaffold-first). Le squelette existe avant tout agent."""

    repo_path: Path
    bricks_installed: list[str] = Field(default_factory=list)
    ci_harness_ready: bool = False  # le contrat code (CI du template) est en place
    design_md_path: Path  # DESIGN.md greffé, lintable


# --- C → D ------------------------------------------------------------------

StoryStatus = Literal[
    "backlog", "ready-for-dev", "atdd-done", "in-progress", "review", "done"
]


class Story(BaseModel):
    """Une story BMAD. Vit comme une section de epics.md (spike S-1b)."""

    id: str  # ex. "6.1"
    epic: str
    title: str
    acceptance: list[str] = Field(default_factory=list)
    gh_issue: int | None = None  # champ **GH Issue:** (optionnel en mode local)
    status: StoryStatus = "backlog"


class BmadPlan(BaseModel):
    """Sortie de l'étape C (pont BMAD). Pose HITL 1 (hitl1_approved)."""

    prd_path: Path
    architecture_path: Path
    epics_md: Path  # _bmad-output/planning-artifacts/epics.md
    stories: list[Story] = Field(default_factory=list)
    hitl1_approved: bool = False


# --- D → E ------------------------------------------------------------------


class BadConfig(BaseModel):
    """Section `bad:` de _bmad/config.yaml — défauts réels de BAD v1.2.0 (spike S-1b)."""

    max_parallel_stories: int = 3
    worktree_base_path: str = ".worktrees"
    model_standard: str = "sonnet"
    model_quality: str = "opus"
    run_ci_locally: bool = False
    # FORCÉ false → préserve HITL 2 (décision canonique 07). Ne pas exposer en override.
    auto_pr_merge: Literal[False] = False


class BadSprintLayout(BaseModel):
    """Sortie de l'étape D. PAS un graphe : BAD le construit lui-même (spike S-1).

    D est un adapter de *placement & configuration* : il garantit que le backlog
    BMAD est au bon endroit et que la section bad: est écrite.
    """

    project_root: Path
    epics_md: Path  # _bmad-output/planning-artifacts/epics.md
    sprint_status_yaml: Path  # _bmad-output/implementation-artifacts/sprint-status.yaml
    bmad_config_yaml: Path  # _bmad/config.yaml AVEC section bad:
    config: BadConfig = Field(default_factory=BadConfig)


# --- Gates ------------------------------------------------------------------

GateName = Literal["code", "design"]


class GateVerdict(BaseModel):
    """Verdict d'un gate. Pour le design, calculé par une politique de sévérité (S-2.3)."""

    gate: GateName
    passed: bool
    findings: list[dict[str, str]] = Field(default_factory=list)
    log_ref: str = ""
