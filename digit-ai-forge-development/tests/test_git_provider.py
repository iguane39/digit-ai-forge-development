"""GitProvider (P-04) : détection par remote + stub tracé pour providers non implémentés."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from conductor.harness.git_provider import (
    AzureDevOpsProvider,
    GitHubProvider,
    UnsupportedProvider,
    detect_provider,
    parse_azdo_remote,
    resolve_git_provider,
)
from conductor.process import ProcessResult


class _FakeRunner:
    """ProcessRunner factice : renvoie une URL de remote fixée."""

    def __init__(self, url: str) -> None:
        self._url = url

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult:
        return ProcessResult(0, self._url, "")


def test_detect_github(tmp_path: Path) -> None:
    assert detect_provider(tmp_path, runner=_FakeRunner("https://github.com/x/y.git")) == "github"


def test_detect_azure_devops(tmp_path: Path) -> None:
    url = "https://dev.azure.com/org/proj/_git/repo"
    assert detect_provider(tmp_path, runner=_FakeRunner(url)) == "azure-devops"


def test_detect_gitlab(tmp_path: Path) -> None:
    assert detect_provider(tmp_path, runner=_FakeRunner("git@gitlab.com:x/y.git")) == "gitlab"


def test_resolve_github_is_github_provider(tmp_path: Path) -> None:
    prov = resolve_git_provider(tmp_path, runner=_FakeRunner("https://github.com/x/y"))
    assert isinstance(prov, GitHubProvider)


def test_resolve_azure_is_azure_provider(tmp_path: Path) -> None:
    prov = resolve_git_provider(tmp_path, runner=_FakeRunner("https://dev.azure.com/o/p/_git/r"))
    assert isinstance(prov, AzureDevOpsProvider)


def test_resolve_gitlab_stub_raises_on_use(tmp_path: Path) -> None:
    prov = resolve_git_provider(tmp_path, runner=_FakeRunner("https://gitlab.com/x/y.git"))
    assert isinstance(prov, UnsupportedProvider)
    with pytest.raises(NotImplementedError, match="gitlab"):
        prov.list_prs(tmp_path)


class _FakeAz:
    """AzRunner factice : PR actives + policies canned (schéma `az repos`)."""

    def __init__(
        self, prs: list[dict[str, Any]], policies: dict[int, list[dict[str, Any]]]
    ) -> None:
        self._prs = prs
        self._policies = policies

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        return self._prs

    def list_policies(self, cwd: Path, pr_id: int) -> list[dict[str, Any]]:
        return self._policies.get(pr_id, [])

    def web_base(self, cwd: Path) -> str:
        return "https://dev.azure.com/o/p/_git/r"


def test_azure_provider_maps_to_common_contract(tmp_path: Path) -> None:
    prs = [
        {
            "pullRequestId": 42,
            "sourceRefName": "refs/heads/feature/tests-d08",
        }
    ]
    policies = {
        42: [
            {"status": "approved", "configuration": {"isBlocking": True}},
            {"status": "queued", "configuration": {"isBlocking": True}},
            {"status": "rejected", "configuration": {"isBlocking": False}},  # non bloquant → ignoré
            {"status": "notApplicable", "configuration": {"isBlocking": True}},  # inconnu → ignoré
        ]
    }
    prov = AzureDevOpsProvider(runner=_FakeAz(prs, policies))
    out = prov.list_prs(tmp_path)
    assert out == [
        {
            "headRefName": "feature/tests-d08",
            "url": "https://dev.azure.com/o/p/_git/r/pullrequest/42",
            "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "PENDING"}],
        }
    ]


def test_parse_azdo_remote_dev_azure() -> None:
    assert parse_azdo_remote("https://dev.azure.com/Nhood-DevOps/APP-IA/_git/repo") == (
        "https://dev.azure.com/Nhood-DevOps",
        "APP-IA",
        "repo",
    )


def test_parse_azdo_remote_accented_repo_urlencoded() -> None:
    # Cas réel : nom de repo accentué %-encodé — ce que `az --detect` ne sait pas gérer.
    url = "https://dev.azure.com/Nhood-DevOps/APP-IA/_git/IAC_Plateforme_Vid%C3%A9o_IA_Ceetrus"
    assert parse_azdo_remote(url) == (
        "https://dev.azure.com/Nhood-DevOps",
        "APP-IA",
        "IAC_Plateforme_Vidéo_IA_Ceetrus",
    )


def test_parse_azdo_remote_visualstudio_and_gitsuffix() -> None:
    assert parse_azdo_remote("https://myorg.visualstudio.com/Proj/_git/my-repo.git") == (
        "https://myorg.visualstudio.com",
        "Proj",
        "my-repo",
    )


def test_parse_azdo_remote_non_azdo_returns_none() -> None:
    assert parse_azdo_remote("https://github.com/x/y.git") is None


def test_azure_provider_empty_rollup_when_no_blocking_policy(tmp_path: Path) -> None:
    prs = [{"pullRequestId": 7, "sourceRefName": "refs/heads/x", "repository": {"webUrl": "u"}}]
    prov = AzureDevOpsProvider(runner=_FakeAz(prs, {7: []}))
    assert prov.list_prs(tmp_path)[0]["statusCheckRollup"] == []
