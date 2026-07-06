"""GitProvider (P-04) : détection par remote + stub tracé pour providers non implémentés."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from conductor.harness.git_provider import GitHubProvider, detect_provider, resolve_git_provider
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


def test_resolve_azure_stub_raises_on_use(tmp_path: Path) -> None:
    prov = resolve_git_provider(tmp_path, runner=_FakeRunner("https://dev.azure.com/o/p/_git/r"))
    with pytest.raises(NotImplementedError, match="azure-devops"):
        prov.list_prs(tmp_path)
