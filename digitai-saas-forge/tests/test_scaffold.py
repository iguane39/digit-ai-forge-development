"""Vérifie l'étape B : copier d'abord, puis greffe des briques — via un runner factice.

Aucune dépendance réseau : le FakeRunner enregistre les commandes au lieu de les exécuter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.cadrage import cadrer
from conductor.contracts import BrickChoice
from conductor.scaffold import scaffold


class FakeRunner:
    """Enregistre les commandes ; renvoie 0, sauf pour les motifs de `fail`."""

    def __init__(self, fail: tuple[str, ...] = ()) -> None:
        self.calls: list[tuple[str, Path]] = []
        self.fail = fail

    def run(self, command: str, cwd: Path) -> int:
        self.calls.append((command, cwd))
        return 1 if any(f in command for f in self.fail) else 0


def test_scaffold_runs_copier_first_then_bricks(tmp_path: Path) -> None:
    runner = FakeRunner()
    cfg = cadrer("un CRM", bricks=[BrickChoice(name="billing", decision="buy")])
    result = scaffold(cfg, tmp_path / "app", runner=runner)

    commands = [c for c, _ in runner.calls]
    assert commands[0].startswith("copier copy")  # scaffold-first : génération d'abord
    # briques de t0 greffées
    assert any("uv add casbin" in c for c in commands)
    assert any("uv add authlib" in c for c in commands)
    assert any("add tenancy" in c for c in commands)
    # brique additionnelle choisie
    assert any("uv add stripe" in c for c in commands)

    assert result.ci_harness_ready is True
    assert {"multi-tenancy", "rbac", "auth-sso", "billing"} <= set(result.bricks_installed)


def test_scaffold_passes_t0_answers_to_copier(tmp_path: Path) -> None:
    runner = FakeRunner()
    scaffold(cadrer("idée"), tmp_path / "app", runner=runner)
    copier_cmd = runner.calls[0][0]
    assert "multi_tenancy=true" in copier_cmd
    assert "rbac=true" in copier_cmd
    assert "auth_sso=true" in copier_cmd


def test_scaffold_raises_if_copier_fails(tmp_path: Path) -> None:
    runner = FakeRunner(fail=("copier copy",))
    with pytest.raises(RuntimeError, match="copier"):
        scaffold(cadrer("idée"), tmp_path / "app", runner=runner)


def test_scaffold_raises_if_brick_graft_fails(tmp_path: Path) -> None:
    runner = FakeRunner(fail=("uv add casbin",))
    with pytest.raises(RuntimeError, match="rbac"):
        scaffold(cadrer("idée"), tmp_path / "app", runner=runner)
