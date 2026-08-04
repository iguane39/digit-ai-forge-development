"""Cœur pur du shim : traduit une ligne de commande ``gh`` en action ``az`` + sortie iso-``gh``.

``translate(argv, backend)`` est **sans I/O direct** : tout accès à Azure DevOps passe par un
``AzBackend`` injectable (fake en test). La fonction renvoie un ``ShimResult`` (stdout/stderr/code)
que l'entrée CLI se contente d'émettre. Anti faux-positif : toute commande non traduisible
sûrement renvoie un code ≠ 0 tracé, jamais un faux succès.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from conductor.harness.git_provider import _AZ_STATUS, _strip_ref


@dataclass(frozen=True)
class ShimResult:
    """Ce qu'un vrai ``gh`` aurait écrit : stdout, stderr et code de sortie."""

    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class AzBackend(Protocol):
    """Opérations Azure DevOps dont le shim a besoin (impl prod = ``az`` ; fake en test)."""

    def pr_list(self, *, status: str) -> list[dict[str, Any]]: ...
    def pr_show(self, pr_id: int | None) -> dict[str, Any]: ...
    def pr_policies(self, pr_id: int) -> list[dict[str, Any]]: ...
    def pr_complete(self, pr_id: int, *, squash: bool, delete_branch: bool) -> ShimResult: ...
    def pr_diff(self, pr_id: int | None) -> str: ...
    def issue_list(self) -> list[dict[str, Any]]: ...
    def issue_create(self, *, title: str, body: str) -> dict[str, Any]: ...
    def auth_token(self) -> str | None: ...
    def auth_ok(self) -> bool: ...


# --- Mapping des champs az repos pr → schéma gh (parité des noms lus par BAD) ---------------
_GH_STATE = {"active": "OPEN", "completed": "MERGED", "abandoned": "CLOSED"}
_MERGEABLE = {"succeeded": "MERGEABLE", "conflicts": "CONFLICTING"}
_MERGE_STATE = {"succeeded": "CLEAN", "conflicts": "DIRTY"}
# gh --state → az --status. Défaut gh (sans --state) = "open".
_STATE_TO_AZ = {"open": "active", "merged": "completed", "closed": "abandoned", "all": "all"}
# gh pr checks : conclusion iso-gh → libellé d'état affiché par `gh pr checks`.
_CHECK_LABEL = {"SUCCESS": "pass", "FAILURE": "fail", "PENDING": "pending"}


def _rollup(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Policies AzDO bloquantes → ``statusCheckRollup`` iso-gh (même logique que #35)."""
    out: list[dict[str, Any]] = []
    for ev in policies:
        cfg = ev.get("configuration") or {}
        if not cfg.get("isBlocking"):
            continue
        conclusion = _AZ_STATUS.get(str(ev.get("status", "")).lower())
        if conclusion is not None:
            out.append({"conclusion": conclusion})
    return out


def _pr_to_gh(pr: dict[str, Any], rollup: list[dict[str, Any]]) -> dict[str, Any]:
    status = str(pr.get("status", "")).lower()
    merge = str(pr.get("mergeStatus", "")).lower()
    return {
        "number": pr.get("pullRequestId"),
        "title": pr.get("title"),
        "state": _GH_STATE.get(status, "OPEN"),
        "mergedAt": pr.get("closedDate") if status == "completed" else None,
        "mergeable": _MERGEABLE.get(merge, "UNKNOWN"),
        "mergeStateStatus": _MERGE_STATE.get(merge, "BLOCKED"),
        "headRefName": _strip_ref(str(pr.get("sourceRefName", ""))),
        "baseRefName": _strip_ref(str(pr.get("targetRefName", ""))),
        "statusCheckRollup": rollup,
    }


# --- Parsing d'arguments (léger, tolérant à l'ordre) ----------------------------------------
def _flag(argv: list[str], name: str) -> str | None:
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def _positional(argv: list[str], start: int) -> str | None:
    for a in argv[start:]:
        if not a.startswith("-"):
            return a
    return None


def _project(obj: dict[str, Any], fields: str | None) -> dict[str, Any]:
    """Restreint un objet aux champs demandés par ``--json f1,f2`` (comme gh)."""
    if fields is None:
        return obj
    keys = [f.strip() for f in fields.split(",") if f.strip()]
    return {k: obj.get(k) for k in keys}


def _unsupported(what: str) -> ShimResult:
    return ShimResult(
        stderr=(
            f"shim gh→az : '{what}' non pris en charge sur Azure DevOps. "
            "Surface couverte : pr list/view/checks/diff/merge, issue list/create, "
            "auth token/status, run view."
        ),
        returncode=2,
    )


# --- Dispatch par sous-commande -------------------------------------------------------------
def translate(argv: list[str], backend: AzBackend) -> ShimResult:
    """Traduit ``argv`` (sans le nom de programme ``gh``) en action ``az`` + sortie iso-gh."""
    if not argv:
        return _unsupported("(commande vide)")
    group = argv[0]
    if group == "pr":
        return _pr(argv, backend)
    if group == "issue":
        return _issue(argv, backend)
    if group == "auth":
        return _auth(argv, backend)
    if group == "run":
        return _run_view(argv)
    return _unsupported(group)


def _pr(argv: list[str], backend: AzBackend) -> ShimResult:
    if len(argv) < 2:
        return _unsupported("pr")
    verb = argv[1]
    if verb == "list":
        az_status = _STATE_TO_AZ.get(_flag(argv, "--state") or "open", "active")
        prs = backend.pr_list(status=az_status)
        rows = [_project(_pr_to_gh(p, []), _flag(argv, "--json")) for p in prs]
        return ShimResult(stdout=json.dumps(rows))
    if verb == "view":
        pos = _positional(argv, 2)
        pr = backend.pr_show(int(pos) if pos and pos.isdigit() else None)
        pr_id = pr.get("pullRequestId")
        rollup = _rollup(backend.pr_policies(pr_id)) if isinstance(pr_id, int) else []
        obj = _project(_pr_to_gh(pr, rollup), _flag(argv, "--json"))
        return ShimResult(stdout=json.dumps(obj))
    if verb == "checks":
        return _pr_checks(argv, backend)
    if verb == "diff":
        pos = _positional(argv, 2)
        return ShimResult(stdout=backend.pr_diff(int(pos) if pos and pos.isdigit() else None))
    if verb == "merge":
        pos = _positional(argv, 2)
        if not (pos and pos.isdigit()):
            return _unsupported("pr merge (numéro de PR requis)")
        return backend.pr_complete(
            int(pos),
            squash="--squash" in argv,
            delete_branch="--delete-branch" in argv,
        )
    return _unsupported(f"pr {verb}")


def _pr_checks(argv: list[str], backend: AzBackend) -> ShimResult:
    """`gh pr checks <n>` : policies bloquantes → lignes TSV + code de sortie iso-gh.

    Codes gh : 0 = tous verts · 1 = ≥1 échec · 8 = en attente / aucun check. ``--watch`` est
    ignoré (renvoi immédiat de l'état courant ; BAD re-poll de lui-même)."""
    pos = _positional(argv, 2)
    if not (pos and pos.isdigit()):
        return _unsupported("pr checks (numéro de PR requis)")
    rollup = _rollup(backend.pr_policies(int(pos)))
    if not rollup:
        return ShimResult(stdout="no checks reported on this pull request", returncode=8)
    lines: list[str] = []
    has_fail = has_pending = False
    for i, check in enumerate(rollup):
        conclusion = str(check.get("conclusion", ""))
        label = _CHECK_LABEL.get(conclusion, "pending")
        has_fail = has_fail or label == "fail"
        has_pending = has_pending or label == "pending"
        lines.append(f"policy-{i}\t{label}")
    code = 1 if has_fail else (8 if has_pending else 0)
    return ShimResult(stdout="\n".join(lines), returncode=code)


def _issue(argv: list[str], backend: AzBackend) -> ShimResult:
    if len(argv) < 2:
        return _unsupported("issue")
    verb = argv[1]
    if verb == "list":
        rows = [_project(i, _flag(argv, "--json")) for i in backend.issue_list()]
        return ShimResult(stdout=json.dumps(rows))
    if verb == "create":
        created = backend.issue_create(
            title=_flag(argv, "--title") or "", body=_flag(argv, "--body") or ""
        )
        # gh imprime l'URL de l'issue créée sur stdout.
        return ShimResult(stdout=str(created.get("url", "")))
    return _unsupported(f"issue {verb}")


def _auth(argv: list[str], backend: AzBackend) -> ShimResult:
    if len(argv) < 2:
        return _unsupported("auth")
    verb = argv[1]
    if verb == "token":
        token = backend.auth_token()
        if not token:
            return ShimResult(stderr="shim gh→az : jeton Azure DevOps indisponible", returncode=1)
        return ShimResult(stdout=token)
    if verb == "status":
        ok = backend.auth_ok()
        return ShimResult(
            stderr="Logged in to Azure DevOps" if ok else "not logged in",
            returncode=0 if ok else 1,
        )
    return _unsupported(f"auth {verb}")


def _run_view(argv: list[str]) -> ShimResult:
    """`gh run view` (GitHub Actions) : pas d'équivalent 1:1 sur AzDO. Best-effort **non
    terminal** — on renvoie ``in_progress`` (jamais un faux succès) ; la vraie porte CI passe par
    `gh pr checks` (branch policies). Chantier dédié si le pilote AzDO réclame l'observation fine
    des runs Pipelines."""
    obj: dict[str, Any] = {"status": "in_progress", "conclusion": None}
    return ShimResult(
        stdout=json.dumps(obj),
        stderr=(
            "shim gh→az : `run view` (Actions) non mappé sur Azure DevOps ; la CI est observée "
            "via `gh pr checks` (branch policies)."
        ),
    )
