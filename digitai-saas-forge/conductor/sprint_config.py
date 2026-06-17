"""Étape D — Adapter de sprint (ex-« compilateur »).

CORRECTION spike S-1 : BAD construit lui-même le graphe de dépendances depuis le backlog.
D NE compile PAS de graphe (cela réimplémenterait BAD = violation décision 01). D est un
adapter de *placement & configuration* :
  - garantit la layout attendue par /bad (`_bmad-output/...`, spike S-1b) ;
  - initialise `sprint-status.yaml` ;
  - écrit la section `bad:` de `_bmad/config.yaml` (auto_pr_merge=False → HITL 2).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from conductor.contracts import BadConfig, BadSprintLayout, BmadPlan

CONFIG_FILE = Path("_bmad/config.yaml")
IMPL_DIR = Path("_bmad-output/implementation-artifacts")
SPRINT_STATUS_FILE = IMPL_DIR / "sprint-status.yaml"


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def preparer_sprint(
    plan: BmadPlan,
    project_root: Path,
    *,
    config: BadConfig | None = None,
) -> BadSprintLayout:
    """D · place le backlog + écrit la config `bad:` pour que /bad démarre.

    Exige que la planification ait franchi HITL 1 (sinon on ne configure rien).
    """
    if not plan.hitl1_approved:
        raise RuntimeError("HITL 1 non franchi : la planification n'est pas approuvée.")

    cfg = config or BadConfig()

    # 1. Statut initial des stories (statuts BMAD/BAD — spike S-1b).
    status = {s.id: "ready-for-dev" for s in plan.stories} or {"_": "backlog"}
    _write_yaml(project_root / SPRINT_STATUS_FILE, {"stories": status})

    # 2. Section bad: de _bmad/config.yaml. auto_pr_merge est forcé False par le type.
    _write_yaml(project_root / CONFIG_FILE, {"bad": cfg.model_dump()})

    return BadSprintLayout(
        project_root=project_root,
        epics_md=plan.epics_md,
        sprint_status_yaml=project_root / SPRINT_STATUS_FILE,
        bmad_config_yaml=project_root / CONFIG_FILE,
        config=cfg,
    )
