"""Étape B — Scaffold-first SaaS.

Invoque `copier` sur la cible (targets/fastapi-saas) PUIS greffe les briques SaaS
retenues, AVANT tout agent (décision canonique 02 — premier garde-fou). Le conductor
ne réimplémente ni copier ni le template : il séquence des commandes via un *runner*
injectable (subprocess en prod, fake en test — aucune dépendance réseau pour les tests).
"""

from __future__ import annotations

from pathlib import Path

from conductor.catalog import resolve_bricks
from conductor.contracts import MissionConfig, ScaffoldResult
from conductor.process import ProcessRunner, SubprocessProcessRunner
from conductor.profiles import FASTAPI_SAAS, TargetProfile

# Cible déterministe (spike S-3). Consommée par génération Copier, pas comme dépendance.
TEMPLATE_REF = "gh:fastapi/full-stack-fastapi-template"


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


def _copier_args(config: MissionConfig, dest: Path) -> list[str]:
    """Commande copier en ``list[str]`` (P-08 : pas de f-string shell ; chemins sûrs)."""
    args = ["copier", "copy"]
    for key, value in _copier_answers(config).items():
        args += ["--data", f"{key}={value}"]
    args += [TEMPLATE_REF, str(dest)]
    return args


def scaffold(
    config: MissionConfig,
    dest: Path,
    *,
    runner: ProcessRunner | None = None,
    profile: TargetProfile = FASTAPI_SAAS,
) -> ScaffoldResult:
    """B · génère le squelette de production puis greffe les briques (build-vs-buy).

    P-08 : tout passe par le `ProcessRunner` (``list[str]``, ``shell=False``, ``shutil.which``).
    P-11 : chaque action est exécutée dans le répertoire de son rôle (``profile.roles``), avec le
    gestionnaire du rôle substitué à ``{pm}`` ; un rôle absent du profil → action **skip tracée**.
    Lève RuntimeError si une commande échoue (le scaffold doit être sain avant tout agent).
    """
    run = (runner or SubprocessProcessRunner()).run
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Génération déterministe du squelette (apporte le harness CI = contrat code).
    copier_args = _copier_args(config, dest)
    if (res := run(copier_args, cwd=dest)).returncode != 0:
        raise RuntimeError(f"copier a échoué (code {res.returncode}) : {' '.join(copier_args)}")

    # 2. Greffe des briques (t0 forcées + choisies), dans l'ordre déterministe du catalogue.
    installed: list[str] = []
    skipped: list[str] = []
    for spec in resolve_bricks(config.saas_scope):
        for action in spec.actions:
            workdir = profile.roles.get(action.role)
            if workdir is None:  # rôle non applicable pour ce profil → skip tracé (do-no-harm)
                skipped.append(f"{spec.name}:{action.role}")
                continue
            pm = profile.pkg_managers.get(action.role, "")
            cmd = [pm if tok == "{pm}" else tok for tok in action.args]
            if (res := run(cmd, cwd=dest / workdir)).returncode != 0:
                raise RuntimeError(
                    f"Greffe '{spec.name}' a échoué (code {res.returncode}) : {' '.join(cmd)}"
                )
        installed.append(spec.name)

    return ScaffoldResult(
        repo_path=dest,
        bricks_installed=installed,
        ci_harness_ready=True,  # le template apporte ses 14 workflows (gate code)
        design_md_path=config.brand_charter,
    )


__all__ = ["scaffold"]
