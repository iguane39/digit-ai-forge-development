"""Backend de production du shim : traduit les besoins du shim en appels ``az`` réels.

Plomberie mince au-dessus du ``ProcessRunner`` unifié (P-07) : résout org/projet/dépôt depuis le
remote ``origin`` (via ``parse_azdo_remote``, robuste aux noms accentués) et émet les objets bruts
``az`` que ``translate`` mappe ensuite vers le schéma ``gh``. Toute la logique de mapping/risque
vit dans ``translate`` (testée avec un fake) ; ce module n'est que de l'I/O ``az``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conductor.harness._text import clip
from conductor.harness.gh_shim.translate import ShimResult
from conductor.harness.git_provider import _strip_ref, parse_azdo_remote
from conductor.process import ProcessResult, ProcessRunner, SubprocessProcessRunner

# GUID de ressource Azure DevOps (constant, public) pour `az account get-access-token`.
_AZDO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"


class SubprocessAzBackend:
    """Implémente ``AzBackend`` via la CLI ``az`` (portable, ``shutil.which`` + ``shell=False``)."""

    def __init__(
        self, cwd: Path, *, runner: ProcessRunner | None = None, timeout_s: int = 60
    ) -> None:
        self._cwd = cwd
        self._runner: ProcessRunner = runner or SubprocessProcessRunner()
        self._timeout_s = timeout_s
        self._scope = self._resolve_scope()

    # --- Résolution de portée & helpers az --------------------------------------------------
    def _resolve_scope(self) -> tuple[str, str, str] | None:
        try:
            url = self._runner.run(
                ["git", "remote", "get-url", "origin"], cwd=self._cwd, timeout_s=self._timeout_s
            ).stdout.strip()
        except RuntimeError:
            return None
        return parse_azdo_remote(url)

    def _az(self, args: list[str]) -> ProcessResult:
        return self._runner.run(
            ["az", *args, "--output", "json"], cwd=self._cwd, timeout_s=self._timeout_s
        )

    def _az_json(self, args: list[str]) -> Any:
        res = self._az(args)
        if res.returncode != 0:
            raise RuntimeError(f"az {' '.join(args)} : {clip(res.stderr, 300)}")
        out = res.stdout.strip()
        return json.loads(out) if out else None

    def _org_args(self) -> list[str]:
        return ["--org", self._scope[0]] if self._scope else ["--detect", "true"]

    def _repo_args(self) -> list[str]:
        if self._scope is None:
            return ["--detect", "true"]
        org, project, repo = self._scope
        return ["--org", org, "--project", project, "--repository", repo]

    def _project_args(self) -> list[str]:
        if self._scope is None:
            return ["--detect", "true"]
        org, project, _ = self._scope
        return ["--org", org, "--project", project]

    def _current_branch(self) -> str:
        try:
            res = self._runner.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self._cwd,
                timeout_s=self._timeout_s,
            )
        except RuntimeError:
            return ""
        return res.stdout.strip()

    # --- Surface AzBackend ------------------------------------------------------------------
    def pr_list(self, *, status: str) -> list[dict[str, Any]]:
        data = self._az_json(["repos", "pr", "list", "--status", status, *self._repo_args()])
        return data if isinstance(data, list) else []

    def pr_show(self, pr_id: int | None) -> dict[str, Any]:
        if pr_id is None:
            branch = self._current_branch()
            for pr in self.pr_list(status="active"):
                if _strip_ref(str(pr.get("sourceRefName", ""))) == branch:
                    return pr
            return {}
        data = self._az_json(["repos", "pr", "show", "--id", str(pr_id), *self._org_args()])
        return data if isinstance(data, dict) else {}

    def pr_policies(self, pr_id: int) -> list[dict[str, Any]]:
        # `policy list` n'accepte que --org (la PR id identifie projet/repo).
        args = ["repos", "pr", "policy", "list", "--id", str(pr_id)]
        args += ["--detect", "true"] if self._scope is None else ["--org", self._scope[0]]
        data = self._az_json(args)
        return data if isinstance(data, list) else []

    def pr_complete(self, pr_id: int, *, squash: bool, delete_branch: bool) -> ShimResult:
        args = ["repos", "pr", "update", "--id", str(pr_id), "--status", "completed"]
        args += self._org_args()
        if squash:
            args += ["--squash-merge", "true"]
        if delete_branch:
            args += ["--delete-source-branch", "true"]
        res = self._az(args)
        return ShimResult(stdout=res.stdout, stderr=res.stderr, returncode=res.returncode)

    def pr_diff(self, pr_id: int | None) -> str:
        pr = self.pr_show(pr_id)
        head = _strip_ref(str(pr.get("sourceRefName", "")))
        base = _strip_ref(str(pr.get("targetRefName", ""))) or "main"
        if not head:
            return ""
        res = self._runner.run(
            ["git", "diff", f"origin/{base}...origin/{head}"],
            cwd=self._cwd,
            timeout_s=self._timeout_s,
        )
        return res.stdout

    def issue_list(self) -> list[dict[str, Any]]:
        wiql = (
            "SELECT [System.Id],[System.Title],[System.State] FROM workitems "
            "WHERE [System.TeamProject] = @project"
        )
        args = ["boards", "query", "--wiql", wiql, *self._project_args()]
        data = self._az_json(args)
        out: list[dict[str, Any]] = []
        for wi in data if isinstance(data, list) else []:
            fields = wi.get("fields") or {}
            out.append(
                {
                    "number": wi.get("id"),
                    "title": fields.get("System.Title"),
                    "state": fields.get("System.State"),
                }
            )
        return out

    def issue_create(self, *, title: str, body: str) -> dict[str, Any]:
        args = ["boards", "work-item", "create", "--title", title, "--type", "Issue"]
        args += self._project_args()
        if body:
            args += ["--description", body]
        data = self._az_json(args)
        if not isinstance(data, dict):
            return {"number": None, "url": ""}
        links = data.get("_links") or {}
        html = links.get("html") or {}
        return {"number": data.get("id"), "url": html.get("href") or ""}

    def auth_token(self) -> str | None:
        try:
            data = self._az_json(
                ["account", "get-access-token", "--resource", _AZDO_RESOURCE]
            )
        except RuntimeError:
            return None
        return data.get("accessToken") if isinstance(data, dict) else None

    def auth_ok(self) -> bool:
        try:
            self._az_json(["account", "show"])
        except RuntimeError:
            return False
        return True
