"""is_isolated / require_isolation_for_real_effects (TF-0103.1) — détection & refus."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.sandbox import (
    IsolationRequiredError,
    _cgroup_indicates_container,
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


def test_require_isolation_message_complet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture rouge (TF-0120) : le message d'erreur complet — chemins de doc, variable
    d'opt-in, ponctuation — est vérifié mot pour mot. Un message d'aide tronqué ou déformé
    est un vrai défaut (l'opérateur bloqué doit pouvoir suivre l'indication)."""
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: False)
    with pytest.raises(IsolationRequiredError) as exc_info:
        require_isolation_for_real_effects("CONDUCTOR_ENABLE_REAL_BAD")
    assert str(exc_info.value) == (
        "CONDUCTOR_ENABLE_REAL_BAD=1 refusé hors isolation processus détectée : lance le run "
        "dans le devcontainer fourni (.devcontainer/devcontainer.json) ou exporte "
        "CONDUCTOR_SANDBOXED=1 si l'isolation est assurée autrement (cf. "
        "docs/superpowers/unattended-run-playbook.md § Isolation). Aucun mode réel "
        "hors isolation : le seul garde-fou actuel sans elle est git (TF-0103)."
    )


def test_cgroup_octets_non_utf8_ignores(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-0120) : `/proc/1/cgroup` est un pseudo-fichier noyau, pas une
    source garantie UTF-8 stricte — `errors="ignore"` doit avaler un octet invalide plutôt
    que de faire planter la détection d'isolation. Sans lui (comportement par défaut
    'strict'), un octet égaré ferait échouer `is_isolated()` au lieu de simplement l'ignorer."""
    cgroup = tmp_path / "cgroup"
    cgroup.write_bytes(b"1:name=systemd:/docker/\xff\xfe/abcdef0123456789\n")
    assert _cgroup_indicates_container(cgroup) is True
