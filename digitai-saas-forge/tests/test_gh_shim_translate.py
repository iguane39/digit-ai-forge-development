"""Cœur du shim gh→az : traduction de chaque sous-commande réelle de BAD, schéma iso-gh + codes."""

from __future__ import annotations

import json
from typing import Any

from conductor.harness.gh_shim.translate import ShimResult, translate


class _FakeBackend:
    """AzBackend factice : renvoie des objets `az` bruts fixés et enregistre les appels."""

    def __init__(
        self,
        *,
        prs: list[dict[str, Any]] | None = None,
        pr: dict[str, Any] | None = None,
        policies: list[dict[str, Any]] | None = None,
        diff: str = "",
        issues: list[dict[str, Any]] | None = None,
        created: dict[str, Any] | None = None,
        token: str | None = "tok",
        authed: bool = True,
        merge: ShimResult | None = None,
    ) -> None:
        self._prs = prs or []
        self._pr = pr or {}
        self._policies = policies or []
        self._diff = diff
        self._issues = issues or []
        self._created = created or {}
        self._token = token
        self._authed = authed
        self._merge = merge or ShimResult()
        self.list_status: str | None = None
        self.shown: int | None = -1
        self.completed: tuple[int, bool, bool] | None = None
        self.issue_args: tuple[str, str] | None = None

    def pr_list(self, *, status: str) -> list[dict[str, Any]]:
        self.list_status = status
        return self._prs

    def pr_show(self, pr_id: int | None) -> dict[str, Any]:
        self.shown = pr_id
        return self._pr

    def pr_policies(self, pr_id: int) -> list[dict[str, Any]]:
        return self._policies

    def pr_complete(self, pr_id: int, *, squash: bool, delete_branch: bool) -> ShimResult:
        self.completed = (pr_id, squash, delete_branch)
        return self._merge

    def pr_diff(self, pr_id: int | None) -> str:
        return self._diff

    def issue_list(self) -> list[dict[str, Any]]:
        return self._issues

    def issue_create(self, *, title: str, body: str) -> dict[str, Any]:
        self.issue_args = (title, body)
        return self._created

    def auth_token(self) -> str | None:
        return self._token

    def auth_ok(self) -> bool:
        return self._authed


_ACTIVE_PR = {
    "pullRequestId": 42,
    "title": "Story 1",
    "status": "active",
    "sourceRefName": "refs/heads/story-1-1-login",
    "targetRefName": "refs/heads/main",
    "mergeStatus": "succeeded",
}


# --- pr list -------------------------------------------------------------------------------
def test_pr_list_maps_state_and_projects_json() -> None:
    be = _FakeBackend(prs=[_ACTIVE_PR])
    res = translate(["pr", "list", "--state", "all", "--json", "number,title,state"], be)
    assert be.list_status == "all"
    assert json.loads(res.stdout) == [{"number": 42, "title": "Story 1", "state": "OPEN"}]


def test_pr_list_default_state_is_active() -> None:
    be = _FakeBackend(prs=[])
    translate(["pr", "list", "--json", "number"], be)
    assert be.list_status == "active"


def test_pr_list_merged_state_maps_to_completed() -> None:
    be = _FakeBackend(prs=[])
    translate(["pr", "list", "--state", "merged", "--json", "number"], be)
    assert be.list_status == "completed"


# --- pr view -------------------------------------------------------------------------------
def test_pr_view_completed_maps_merged_and_mergedat() -> None:
    pr = {**_ACTIVE_PR, "status": "completed", "closedDate": "2026-07-06T00:00:00Z"}
    be = _FakeBackend(pr=pr)
    res = translate(["pr", "view", "42", "--json", "state,mergedAt"], be)
    assert be.shown == 42
    assert json.loads(res.stdout) == {"state": "MERGED", "mergedAt": "2026-07-06T00:00:00Z"}


def test_pr_view_open_has_null_mergedat() -> None:
    be = _FakeBackend(pr=_ACTIVE_PR)
    res = translate(["pr", "view", "42", "--json", "state,mergedAt,mergeable"], be)
    assert json.loads(res.stdout) == {"state": "OPEN", "mergedAt": None, "mergeable": "MERGEABLE"}


def test_pr_view_without_number_resolves_current_branch() -> None:
    be = _FakeBackend(pr=_ACTIVE_PR)
    translate(["pr", "view", "--json", "state"], be)
    assert be.shown is None  # backend résout la PR de la branche courante


def test_pr_view_includes_rollup_from_blocking_policies() -> None:
    be = _FakeBackend(
        pr=_ACTIVE_PR,
        policies=[
            {"status": "approved", "configuration": {"isBlocking": True}},
            {"status": "rejected", "configuration": {"isBlocking": False}},  # non bloquant
        ],
    )
    res = translate(["pr", "view", "42", "--json", "statusCheckRollup"], be)
    assert json.loads(res.stdout) == {"statusCheckRollup": [{"conclusion": "SUCCESS"}]}


# --- pr checks -----------------------------------------------------------------------------
def test_pr_checks_all_green_exits_zero() -> None:
    be = _FakeBackend(policies=[{"status": "approved", "configuration": {"isBlocking": True}}])
    res = translate(["pr", "checks", "42"], be)
    assert res.returncode == 0


def test_pr_checks_failure_exits_one() -> None:
    be = _FakeBackend(policies=[{"status": "rejected", "configuration": {"isBlocking": True}}])
    res = translate(["pr", "checks", "42"], be)
    assert res.returncode == 1


def test_pr_checks_pending_exits_eight() -> None:
    be = _FakeBackend(policies=[{"status": "queued", "configuration": {"isBlocking": True}}])
    res = translate(["pr", "checks", "42"], be)
    assert res.returncode == 8


def test_pr_checks_no_blocking_policy_exits_eight() -> None:
    be = _FakeBackend(policies=[{"status": "approved", "configuration": {"isBlocking": False}}])
    res = translate(["pr", "checks", "42"], be)
    assert res.returncode == 8


def test_pr_checks_watch_flag_ignored() -> None:
    be = _FakeBackend(policies=[{"status": "approved", "configuration": {"isBlocking": True}}])
    res = translate(["pr", "checks", "42", "--watch", "--interval", "30"], be)
    assert res.returncode == 0


# --- pr diff / merge -----------------------------------------------------------------------
def test_pr_diff_returns_backend_diff() -> None:
    be = _FakeBackend(diff="diff --git a b\n+x\n")
    res = translate(["pr", "diff", "42"], be)
    assert res.stdout == "diff --git a b\n+x\n"


def test_pr_merge_forwards_flags_to_backend() -> None:
    be = _FakeBackend(merge=ShimResult(stdout="done", returncode=0))
    res = translate(["pr", "merge", "7", "--squash", "--auto", "--delete-branch"], be)
    assert be.completed == (7, True, True)
    assert res.returncode == 0


def test_pr_merge_without_number_is_error() -> None:
    res = translate(["pr", "merge", "--squash"], _FakeBackend())
    assert res.returncode == 2


# --- issue ---------------------------------------------------------------------------------
def test_issue_list_projects_fields() -> None:
    be = _FakeBackend(issues=[{"number": 3, "title": "Story 3", "state": "Active"}])
    res = translate(["issue", "list", "--json", "number,title,state"], be)
    assert json.loads(res.stdout) == [{"number": 3, "title": "Story 3", "state": "Active"}]


def test_issue_create_prints_url() -> None:
    be = _FakeBackend(created={"number": 9, "url": "https://dev.azure.com/o/p/_workitems/edit/9"})
    res = translate(["issue", "create", "--title", "T", "--body", "B"], be)
    assert be.issue_args == ("T", "B")
    assert res.stdout == "https://dev.azure.com/o/p/_workitems/edit/9"


# --- auth ----------------------------------------------------------------------------------
def test_auth_token_prints_token() -> None:
    res = translate(["auth", "token"], _FakeBackend(token="secret"))
    assert res.stdout == "secret"
    assert res.returncode == 0


def test_auth_token_missing_is_error() -> None:
    res = translate(["auth", "token"], _FakeBackend(token=None))
    assert res.returncode == 1


def test_auth_status_ok_exits_zero() -> None:
    assert translate(["auth", "status"], _FakeBackend(authed=True)).returncode == 0


def test_auth_status_not_logged_in_exits_one() -> None:
    assert translate(["auth", "status"], _FakeBackend(authed=False)).returncode == 1


# --- run view / inconnu --------------------------------------------------------------------
def test_run_view_is_non_terminal_never_false_green() -> None:
    res = translate(["run", "view", "--json", "status,conclusion"], _FakeBackend())
    obj = json.loads(res.stdout)
    assert obj["status"] == "in_progress"  # jamais "completed"/"success"
    assert obj["conclusion"] is None


def test_unknown_command_is_error() -> None:
    assert translate(["repo", "clone", "x"], _FakeBackend()).returncode == 2


def test_empty_argv_is_error() -> None:
    assert translate([], _FakeBackend()).returncode == 2
