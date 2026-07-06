"""Abstraction du provider Git (portabilité — backlog P-04).

Découple la forge de GitHub. Interface ``GitProvider`` (observation des PR/MR, source de vérité
du run) + implémentations : **GitHub** (parité actuelle, via la CLI ``gh``), **Azure DevOps** et
**GitLab** (stubs tracés, à implémenter). Sélection par l'URL du remote ``origin``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from conductor.harness.gh import GhRunner, SubprocessGh
from conductor.process import ProcessRunner, SubprocessProcessRunner


class GitProvider(Protocol):
    """Observe l'état des PR/MR d'un dépôt (source de vérité du run)."""

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]: ...


class GitHubProvider:
    """Provider GitHub : délègue à la CLI ``gh`` (parité du comportement actuel)."""

    def __init__(self, runner: GhRunner | None = None) -> None:
        self._gh = runner or SubprocessGh()

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        return self._gh.list_prs(cwd)


class UnsupportedProvider:
    """Stub tracé pour un provider pas encore implémenté (Azure DevOps, GitLab)."""

    def __init__(self, name: str) -> None:
        self.name = name

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        raise NotImplementedError(
            f"Provider Git '{self.name}' non implémenté : seul GitHub (gh) l'est aujourd'hui. "
            "Ajouter une impl GitProvider pour cette forge (list_prs via son API/CLI)."
        )


def detect_provider(cwd: Path, *, runner: ProcessRunner | None = None) -> str:
    """Devine le provider depuis l'URL du remote ``origin`` (github par défaut/inconnu)."""
    r = runner or SubprocessProcessRunner()
    try:
        url = r.run(["git", "remote", "get-url", "origin"], cwd=cwd).stdout.strip().lower()
    except RuntimeError:
        return "github"  # git absent ou pas de remote → défaut GitHub
    if "dev.azure.com" in url or "visualstudio.com" in url:
        return "azure-devops"
    if "gitlab" in url:
        return "gitlab"
    return "github"


def resolve_git_provider(cwd: Path, *, runner: ProcessRunner | None = None) -> GitProvider:
    """Sélectionne l'impl GitProvider selon le remote (GitHub réel ; AzDO/GitLab → stub tracé)."""
    name = detect_provider(cwd, runner=runner)
    if name == "github":
        return GitHubProvider()
    return UnsupportedProvider(name)
