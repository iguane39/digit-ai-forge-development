"""Abstraction du provider Git (portabilité — backlog P-04).

Découple la forge de GitHub. Interface ``GitProvider`` (observation des PR/MR, source de vérité
du run) + implémentations : **GitHub** (via la CLI ``gh``), **Azure DevOps** (via la CLI ``az
repos``) et **GitLab** (stub tracé, à implémenter). Sélection par l'URL du remote ``origin``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urlsplit

from conductor.harness._text import clip
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


class AzRunner(Protocol):
    """Observe les PR Azure DevOps via ``az repos`` (injectable ; fake en test)."""

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]: ...
    def list_policies(self, cwd: Path, pr_id: int) -> list[dict[str, Any]]: ...
    def web_base(self, cwd: Path) -> str | None: ...


def parse_azdo_remote(url: str) -> tuple[str, str, str] | None:
    """``(org_url, project, repo)`` depuis une URL de remote Azure DevOps, ou ``None``.

    Gère ``https://dev.azure.com/{org}/{project}/_git/{repo}`` et
    ``https://{org}.visualstudio.com/{project}/_git/{repo}``. **Décode le %-encoding** (noms de
    projet/repo accentués ou espacés) — robustesse que ``az --detect`` n'a pas (il minusculise et
    bute sur les caractères non-ASCII → 404)."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    segs = [unquote(s) for s in parts.path.split("/") if s]
    if "_git" not in segs:
        return None
    gi = segs.index("_git")
    if gi + 1 >= len(segs) or gi < 1:
        return None
    repo = segs[gi + 1]
    repo = repo[:-4] if repo.endswith(".git") else repo
    project = segs[gi - 1]
    if host == "dev.azure.com" and gi >= 2:
        return (f"https://dev.azure.com/{segs[0]}", project, repo)
    if host.endswith(".visualstudio.com"):
        return (f"https://{host}", project, repo)
    return None


class SubprocessAz:
    """Runner de prod : ``az repos pr …`` via le ProcessRunner (P-07, portable).

    Dérive org/projet/dépôt de l'URL du remote ``origin`` et les passe en **arguments explicites**
    (robuste aux noms accentués/espacés) ; repli sur ``--detect true`` si le remote n'est pas une
    URL Azure DevOps parsable."""

    def __init__(self, *, runner: ProcessRunner | None = None, timeout_s: int = 60) -> None:
        self._runner: ProcessRunner = runner or SubprocessProcessRunner()
        self._timeout_s = timeout_s

    def _remote(self, cwd: Path) -> tuple[str, str, str] | None:
        try:
            url = self._runner.run(
                ["git", "remote", "get-url", "origin"], cwd=cwd, timeout_s=self._timeout_s
            ).stdout.strip()
        except RuntimeError:
            return None
        return parse_azdo_remote(url)

    def _az_json(self, args: list[str], cwd: Path) -> list[dict[str, Any]]:
        res = self._runner.run(
            ["az", *args, "--output", "json"], cwd=cwd, timeout_s=self._timeout_s
        )
        if res.returncode != 0:
            joined = " ".join(args)
            raise RuntimeError(
                f"az {joined} a échoué (code {res.returncode}) : {clip(res.stderr, 500)}"
            )
        out = res.stdout.strip()
        return json.loads(out) if out else []

    def _repo_id(self, cwd: Path, org: str, project: str, repo_name: str) -> str | None:
        """GUID (ASCII) du dépôt — évite de passer un nom accentué en argv à ``az.cmd``, que
        cmd.exe corromprait (codepage). Repli sur ``None`` si non résolu."""
        try:
            repos = self._az_json(["repos", "list", "--org", org, "--project", project], cwd)
        except RuntimeError:
            return None
        for r in repos:
            if r.get("name") == repo_name:
                rid = r.get("id")
                return str(rid) if rid else None
        return None

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        scope = self._remote(cwd)
        args = ["repos", "pr", "list", "--status", "active"]
        if scope is None:
            args += ["--detect", "true"]
        else:
            org, project, repo = scope
            repo_ref = self._repo_id(cwd, org, project, repo) or repo
            args += ["--org", org, "--project", project, "--repository", repo_ref]
        return self._az_json(args, cwd)

    def list_policies(self, cwd: Path, pr_id: int) -> list[dict[str, Any]]:
        scope = self._remote(cwd)
        args = ["repos", "pr", "policy", "list", "--id", str(pr_id)]
        # `policy list` n'accepte que --org (la PR id identifie projet/repo).
        args += ["--detect", "true"] if scope is None else ["--org", scope[0]]
        return self._az_json(args, cwd)

    def web_base(self, cwd: Path) -> str | None:
        """Base d'URL web du dépôt (``{org}/{project}/_git/{repo}``) pour les liens de PR."""
        scope = self._remote(cwd)
        if scope is None:
            return None
        org, project, repo = scope
        return f"{org}/{project}/_git/{repo}"


# Statut d'évaluation de policy AzDO → conclusion iso-GitHub (cf. bad_runner._PASS).
# `notApplicable`/inconnu → non mappé (ignoré) : anti faux-positif.
_AZ_STATUS: dict[str, str] = {
    "approved": "SUCCESS",
    "rejected": "FAILURE",
    "queued": "PENDING",
    "running": "PENDING",
}


def _strip_ref(ref: str) -> str:
    """`refs/heads/feature/x` → `feature/x` (headRefName iso-GitHub)."""
    return ref.removeprefix("refs/heads/")


class AzureDevOpsProvider:
    """Provider Azure DevOps : observe les PR actives via ``az repos`` et mappe vers le contrat
    commun (``headRefName`` / ``url`` / ``statusCheckRollup``).

    Les « checks » proviennent des *branch policies* **bloquantes** de la PR (build validation).
    Anti faux-positif : une PR sans policy bloquante évaluée → rollup vide → traitée comme « non
    terminée » par ``bad_runner._code_ok`` (parité avec GitHub sans statusCheck)."""

    def __init__(self, runner: AzRunner | None = None) -> None:
        self._az: AzRunner = runner or SubprocessAz()

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        base = self._az.web_base(cwd)
        out: list[dict[str, Any]] = []
        for pr in self._az.list_prs(cwd):
            pr_id = pr.get("pullRequestId")
            rollup = self._rollup(cwd, pr_id) if isinstance(pr_id, int) else []
            url = f"{base}/pullrequest/{pr_id}" if base and pr_id is not None else None
            out.append(
                {
                    "headRefName": _strip_ref(str(pr.get("sourceRefName", ""))),
                    "url": url,
                    "statusCheckRollup": rollup,
                }
            )
        return out

    def _rollup(self, cwd: Path, pr_id: int) -> list[dict[str, Any]]:
        rollup: list[dict[str, Any]] = []
        for ev in self._az.list_policies(cwd, pr_id):
            cfg = ev.get("configuration") or {}
            if not cfg.get("isBlocking"):
                continue  # seules les policies bloquantes comptent comme "check"
            conclusion = _AZ_STATUS.get(str(ev.get("status", "")).lower())
            if conclusion is not None:
                rollup.append({"conclusion": conclusion})
        return rollup


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
    """Sélectionne l'impl selon le remote (GitHub + Azure DevOps réels ; GitLab → stub)."""
    name = detect_provider(cwd, runner=runner)
    if name == "azure-devops":
        return AzureDevOpsProvider()
    if name == "gitlab":
        return UnsupportedProvider(name)
    return GitHubProvider()  # github + défaut inconnu
