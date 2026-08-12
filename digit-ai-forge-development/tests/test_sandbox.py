"""is_isolated / require_isolation_for_real_effects (TF-0103.1) — détection & refus."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.sandbox import (
    IsolationRequiredError,
    is_isolated,
    require_isolation_for_real_effects,
)


def _clear_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_SANDBOXED", raising=False)
    monkeypatch.delenv("REMOTE_CONTAINERS", raising=False)
    monkeypatch.delenv("CODESPACES", raising=False)


def test_non_isolated_par_defaut_est_rouge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture rouge : aucun marqueur, aucun fichier conteneur → pas isolé."""
    _clear_markers(monkeypatch)
    assert is_isolated(dockerenv=tmp_path / "absent", cgroup=tmp_path / "absent-cgroup") is False


def test_opt_in_manuel_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : CONDUCTOR_SANDBOXED=1 déclare l'isolation assurée autrement."""
    _clear_markers(monkeypatch)
    monkeypatch.setenv("CONDUCTOR_SANDBOXED", "1")
    assert is_isolated(dockerenv=tmp_path / "absent", cgroup=tmp_path / "absent-cgroup") is True


def test_marqueur_devcontainer_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : marqueur d'env posé par VS Code Dev Containers / Codespaces."""
    _clear_markers(monkeypatch)
    monkeypatch.setenv("REMOTE_CONTAINERS", "true")
    assert is_isolated(dockerenv=tmp_path / "absent", cgroup=tmp_path / "absent-cgroup") is True


def test_dockerenv_present_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : `/.dockerenv` présent (conteneur Docker/Linux)."""
    _clear_markers(monkeypatch)
    dockerenv = tmp_path / ".dockerenv"
    dockerenv.write_text("", encoding="utf-8")
    assert is_isolated(dockerenv=dockerenv, cgroup=tmp_path / "absent-cgroup") is True


def test_cgroup_docker_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : `/proc/1/cgroup` porte un marqueur de runtime conteneur."""
    _clear_markers(monkeypatch)
    cgroup = tmp_path / "cgroup"
    cgroup.write_text("1:name=systemd:/docker/abcdef0123456789\n", encoding="utf-8")
    assert is_isolated(dockerenv=tmp_path / "absent", cgroup=cgroup) is True


def test_cgroup_hors_conteneur_non_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture rouge : `/proc/1/cgroup` présent mais sans marqueur conteneur."""
    _clear_markers(monkeypatch)
    cgroup = tmp_path / "cgroup"
    cgroup.write_text("1:name=systemd:/init.scope\n", encoding="utf-8")
    assert is_isolated(dockerenv=tmp_path / "absent", cgroup=cgroup) is False


def test_require_isolation_refuse_hors_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture rouge : le flag d'effets réels est refusé (exception), pas de repli silencieux."""
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: False)
    with pytest.raises(IsolationRequiredError, match="CONDUCTOR_ENABLE_REAL_BAD"):
        require_isolation_for_real_effects("CONDUCTOR_ENABLE_REAL_BAD")


def test_require_isolation_passe_si_isole(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : isolation détectée → aucune exception."""
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: True)
    require_isolation_for_real_effects("CONDUCTOR_ENABLE_REAL_BAD")  # ne lève pas
