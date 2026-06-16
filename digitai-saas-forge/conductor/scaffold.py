"""Étape B — Scaffold-first SaaS.

Invoque `copier` sur la cible (targets/fastapi-saas) PUIS greffe les briques SaaS
retenues, AVANT tout agent (décision canonique 02 — premier garde-fou). Le conductor
ne réimplémente ni copier ni le template : il séquence des commandes via un *runner*
injectable (subprocess en prod, fake en test — aucune dépendance réseau pour les tests).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from conductor.catalog import resolve_bricks
from conductor.contracts import MissionConfig, ScaffoldResult

# Cible déterministe (spike S-3). Consommée par génération Copier, pas comme dépendance.
TEMPLATE_REF = "gh:fastapi/full-stack-fastapi-template"


class CommandRunner(Protocol):
    """Exécute une commande shell dans un répertoire et renvoie son code de sortie."""

    def run(self, command: str, cwd: Path) -> int: ...


class SubprocessRunner:
    """Runner de production : délègue au shell. Aucun état."""

    def run(self, command: str, cwd: Path) -> int:
        cwd.mkdir(parents=True, exist_ok=True)
        return subprocess.run(command, cwd=cwd, shell=True, check=False).returncode


def _copier_answers(config: MissionConfig) -> dict[str, str]:
    """Traduit le scope de mission vers les questions de targets/fastapi-saas/copier.yml."""
    selected = {b.name for b in config.saas_scope if b.decision != "skip"}
    answers: dict[str, str] = {
        "project_name": config.idea[:60],
        # Briques de t0 (toujours vraies — décision 05)
        "multi_tenancy": "true",
        "rbac": "true",
        "auth_sso": "true",
        # Briques à la demande
        "billing": "stripe" if "billing" in selected else "none",
        "jobs_async": "arq" if "jobs-async" in selected else "none",
        "analytics": "posthog" if "analytics" in selected else "none",
        "feature_flags": "openfeature-unleash" if "feature-flags" in selected else "none",
        "emailing": "resend" if "emailing" in selected else "smtp",
    }
    return answers


def _copier_command(config: MissionConfig, dest: Path) -> str:
    data = " ".join(f"--data {k}={v}" for k, v in _copier_answers(config).items())
    return f"copier copy {data} {TEMPLATE_REF} {dest}"


def scaffold(
    config: MissionConfig,
    dest: Path,
    *,
    runner: CommandRunner | None = None,
) -> ScaffoldResult:
    """B · génère le squelette de production puis greffe les briques (build-vs-buy).

    Lève RuntimeError si une commande échoue (le scaffold doit être sain avant tout agent).
    """
    run = (runner or SubprocessRunner()).run

    # 1. Génération déterministe du squelette (apporte le harness CI = contrat code).
    cmd = _copier_command(config, dest)
    if (rc := run(cmd, dest)) != 0:
        raise RuntimeError(f"copier a échoué (code {rc}) : {cmd}")

    # 2. Greffe des briques (t0 forcées + choisies), dans l'ordre déterministe du catalogue.
    installed: list[str] = []
    for spec in resolve_bricks(config.saas_scope):
        for action in spec.actions:
            if (rc := run(action, dest)) != 0:
                raise RuntimeError(f"Greffe '{spec.name}' a échoué (code {rc}) : {action}")
        installed.append(spec.name)

    return ScaffoldResult(
        repo_path=dest,
        bricks_installed=installed,
        ci_harness_ready=True,  # le template apporte ses 14 workflows (gate code)
        design_md_path=config.brand_charter,
    )


__all__ = ["CommandRunner", "SubprocessRunner", "scaffold"]
