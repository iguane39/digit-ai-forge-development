"""Isolation processus — prérequis des flags d'effets réels (TF-0103, sous-item 1).

Le mode unattended peut activer des flags "effets réels" (``CONDUCTOR_ENABLE_REAL_BAD``,
``CONDUCTOR_ENABLE_REAL_BMAD``) qui invoquent le CLI ``claude`` en ``--dangerously-skip-
permissions`` : un agent autonome peut alors écrire des fichiers, créer des worktrees git
et appeler ``gh``/``az`` sans confirmation humaine. Les seuls garde-fous actuels sont git
(retour arrière possible) — aucune isolation processus (conteneur/microVM) n'empêche un
run mal aiguillé d'endommager le poste hôte lui-même (réseau, autres dépôts, secrets du
profil). Docker Sandboxes (30/01/2026) et la doc sécurité Claude Code posent l'isolation
processus comme prérequis d'un agent autonome à effets réels.

Ce module fournit la détection portable (aucun spawn) et le contrôle qui **refuse** les
flags d'effets réels hors isolation détectée — cf. ``.devcontainer/devcontainer.json``
(configuration fournie) et ``docs/superpowers/unattended-run-playbook.md`` § Isolation.
"""

from __future__ import annotations

import os
from pathlib import Path

# Marqueurs d'environnement posés par les tooling de devcontainer usuels — jamais présents
# hors de ces outils (VS Code Dev Containers / GitHub Codespaces), donc fiables en détection
# automatique (contrairement à une variable que l'opérateur pourrait positionner à la main).
_SANDBOX_ENV_MARKERS = (
    "REMOTE_CONTAINERS",  # VS Code Dev Containers CLI
    "CODESPACES",  # GitHub Codespaces
)

# Opt-in explicite pour les isolations non auto-détectables par les marqueurs ci-dessus
# (ex. Docker Sandboxes, microVM managée, sandbox maison). À ne positionner QUE si
# l'isolation est réellement assurée par un autre mécanisme documenté : ce drapeau est un
# engagement déclaratif de l'opérateur, pas une preuve technique — le poser sans isolation
# réelle contourne le garde-fou en connaissance de cause.
_MANUAL_OPT_IN = "CONDUCTOR_SANDBOXED"

_DOCKERENV = Path("/.dockerenv")
_CGROUP = Path("/proc/1/cgroup")
_CONTAINER_CGROUP_MARKERS = ("docker", "containerd", "kubepods")


def _cgroup_indicates_container(cgroup_path: Path) -> bool:
    """Vrai si `/proc/1/cgroup` porte un marqueur de runtime conteneur (Linux)."""
    try:
        text = cgroup_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _CONTAINER_CGROUP_MARKERS)


def is_isolated(*, dockerenv: Path = _DOCKERENV, cgroup: Path = _CGROUP) -> bool:
    """Vrai si le processus courant tourne dans un environnement isolé détectable.

    Ordre de détection (le premier qui matche suffit) :
    1. Opt-in explicite ``CONDUCTOR_SANDBOXED=1`` (isolation assurée autrement, déclarée).
    2. Marqueurs d'environnement des devcontainers usuels (Dev Containers, Codespaces).
    3. Marqueurs de conteneur Linux (``/.dockerenv``, ``/proc/1/cgroup``).

    Chemins de détection injectables (tests) ; en production les valeurs par défaut
    pointent le système de fichiers réel.
    """
    if os.environ.get(_MANUAL_OPT_IN) == "1":
        return True
    if any(os.environ.get(marker) for marker in _SANDBOX_ENV_MARKERS):
        return True
    if dockerenv.exists():
        return True
    return _cgroup_indicates_container(cgroup)


class IsolationRequiredError(RuntimeError):
    """Levée quand un flag d'effets réels est activé hors isolation processus détectée."""


def require_isolation_for_real_effects(flag_name: str) -> None:
    """Prérequis des flags d'effets réels (TF-0103.1) : refuse le mode réel hors isolation.

    Appelé par les ``resolve_*`` du harness avant de construire un runner à effets réels
    (``--dangerously-skip-permissions``). Ne lève rien quand le flag est désactivé (les
    résolutions stub restent inchangées) — uniquement quand le flag est actif ET qu'aucune
    isolation n'est détectée : c'est un refus, pas un repli silencieux vers le stub, pour
    que l'opérateur voie explicitement pourquoi le mode réel n'a pas démarré.
    """
    if not is_isolated():
        raise IsolationRequiredError(
            f"{flag_name}=1 refusé hors isolation processus détectée : lance le run dans "
            "le devcontainer fourni (.devcontainer/devcontainer.json) ou exporte "
            f"{_MANUAL_OPT_IN}=1 si l'isolation est assurée autrement (cf. "
            "docs/superpowers/unattended-run-playbook.md § Isolation). Aucun mode réel "
            "hors isolation : le seul garde-fou actuel sans elle est git (TF-0103)."
        )
