"""Vérifie l'étape B : copier d'abord, puis greffe des briques par rôle — via un ProcessRunner
factice (aucune dépendance réseau ; on enregistre les args au lieu d'exécuter)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from conductor.cadrage import cadrer
from conductor.contracts import BrickChoice
from conductor.process import ProcessResult
from conductor.profiles import TargetProfile
from conductor.scaffold import scaffold


class FakeRunner:
    """Enregistre les args (list[str]) ; renvoie 0, sauf pour les motifs de `fail`."""

    def __init__(self, fail: tuple[str, ...] = ()) -> None:
        self.calls: list[tuple[list[str], Path | None]] = []
        self.fail = fail

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult:
        argv = list(args)
        self.calls.append((argv, cwd))
        joined = " ".join(argv)
        return ProcessResult(1 if any(f in joined for f in self.fail) else 0, "", "")


def test_scaffold_runs_copier_first_then_bricks(tmp_path: Path) -> None:
    runner = FakeRunner()
    cfg = cadrer("un CRM", bricks=[BrickChoice(name="billing", decision="buy")])
    result = scaffold(cfg, tmp_path / "app", runner=runner)

    cmds = [" ".join(a) for a, _ in runner.calls]
    assert cmds[0].startswith("copier copy")  # scaffold-first : génération d'abord
    # {pm} résolu (backend → uv) et actions par rôle
    assert any("uv add casbin" in c for c in cmds)
    assert any("uv add authlib" in c for c in cmds)
    assert any("add tenancy" in c for c in cmds)
    assert any("uv add stripe" in c for c in cmds)

    assert result.ci_harness_ready is True
    assert {"multi-tenancy", "rbac", "auth-sso", "billing"} <= set(result.bricks_installed)


def test_scaffold_resolves_role_workdir(tmp_path: Path) -> None:
    """P-11 : l'action frontend s'exécute dans le répertoire du rôle (frontend), pas via `cd`."""
    runner = FakeRunner()
    scaffold(
        cadrer("x", bricks=[BrickChoice(name="analytics", decision="buy")]),
        tmp_path / "app",
        runner=runner,
    )
    frontend_calls = [(a, cwd) for a, cwd in runner.calls if "posthog-js" in " ".join(a)]
    assert frontend_calls
    args, cwd = frontend_calls[0]
    assert args == ["npm", "i", "posthog-js"]  # {pm} → npm (frontend)
    assert cwd == tmp_path / "app" / "frontend"


def test_scaffold_passes_t0_answers_to_copier(tmp_path: Path) -> None:
    runner = FakeRunner()
    scaffold(cadrer("idée"), tmp_path / "app", runner=runner)
    copier_cmd = " ".join(runner.calls[0][0])
    assert "multi_tenancy=true" in copier_cmd
    assert "rbac=true" in copier_cmd
    assert "auth_sso=true" in copier_cmd


def test_scaffold_skips_actions_when_role_absent(tmp_path: Path) -> None:
    """P-11 : rôle absent du profil → action non applicable (skip tracé), jamais un échec."""
    prof = TargetProfile(name="x", code_check=None, has_ui=False)  # roles={} par défaut
    runner = FakeRunner()
    result = scaffold(
        cadrer("idée", bricks=[BrickChoice(name="billing", decision="buy")]),
        tmp_path / "app",
        runner=runner,
        profile=prof,
    )
    cmds = [" ".join(a) for a, _ in runner.calls]
    assert cmds[0].startswith("copier copy")
    assert not any("add" in c for c in cmds[1:])  # aucune action greffée (rôles absents)
    assert "billing" in result.bricks_installed  # brique traitée (actions skip)


def test_scaffold_raises_if_copier_fails(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="copier"):
        scaffold(cadrer("idée"), tmp_path / "app", runner=FakeRunner(fail=("copier copy",)))


CIBLE = Path(__file__).resolve().parents[1] / "targets" / "fastapi-saas"


def _briques_ecrites() -> list[str]:
    return sorted(p.name for p in (CIBLE / "bricks").iterdir() if p.name != ".gitkeep")


def test_tf1778_une_cible_sans_briques_se_declare_non_disponible() -> None:
    """Lot Produit-83 du 15/10/2026 (RV-1) : `bricks/` ne porte que `.gitkeep`, et `copier.yml`
    annonçait multi-locataire, RBAC Casbin et SSO « requis t0 » sans une ligne qui les implémente.

    Tant qu'aucune brique n'est écrite, la cible le DIT là où on la lit : au README de la cible et
    dans l'avertissement que copier affiche avant de copier. Le jour où une brique arrive, ce cas
    rougit pour que la déclaration soit retirée en même temps : elle ne survit pas à sa vérité."""
    readme = CIBLE / "README.md"
    copier_yml = yaml.safe_load((CIBLE / "copier.yml").read_text(encoding="utf-8"))
    avertissement = str(copier_yml.get("_message_before_copy", ""))

    if _briques_ecrites():
        assert "NON DISPONIBLE" not in avertissement, "des briques existent : retirer l'avis"
        return
    assert readme.exists(), "la cible vide se déclare dans son README"
    texte = readme.read_text(encoding="utf-8")
    assert "NON DISPONIBLE" in texte
    assert "NON DISPONIBLE" in avertissement, "copier avertit avant de copier une cible vide"
    for brique in ("multi-tenancy", "rbac", "auth-sso"):
        assert brique in texte, f"le README nomme la brique non écrite {brique}"


def test_scaffold_raises_if_brick_graft_fails(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="rbac"):
        scaffold(cadrer("idée"), tmp_path / "app", runner=FakeRunner(fail=("add casbin",)))
