"""Résolution de profil générique (P-14…P-18) : cascade, cas full-stack, gate par rôle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor import profiles as profiles_mod
from conductor.cadrage import cadrer
from conductor.capabilities import detect_capabilities
from conductor.gates.code_gate import run_code_gate
from conductor.governance import HitlPending, require_hitl0
from conductor.onramp import select_onramp
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.onramp.detect import detect_stack
from conductor.onramp.no_onramp import NoOnramp
from conductor.profiles import (
    FASTAPI_SAAS,
    RoleCommands,
    TargetProfile,
    resolve_profile,
    synthesize_profile,
)


class _CodeRunner:
    def __init__(self, rc: int = 0) -> None:
        self.rc = rc
        self.calls: list[tuple[str, Path]] = []

    def run(self, command: str, cwd: Path) -> int:
        self.calls.append((command, cwd))
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


def _fullstack(tmp: Path) -> Path:
    """Cas de référence : backend Flask + frontend React, AUCUN marqueur racine."""
    (tmp / "backend").mkdir(parents=True, exist_ok=True)
    (tmp / "backend" / "requirements.txt").write_text("flask\n", encoding="utf-8")
    (tmp / "frontend").mkdir(parents=True, exist_ok=True)
    (tmp / "frontend" / "package.json").write_text(
        '{"scripts":{"build":"vite build"},"dependencies":{"react":"^18"}}', encoding="utf-8"
    )
    return tmp


# --- §7.1 Cas de référence full-stack non-FastAPI --------------------------------------------
def test_fullstack_is_generic_and_does_not_raise(tmp_path: Path) -> None:
    repo = _fullstack(tmp_path)
    assert detect_stack(repo) == "generic"
    mission = cadrer("i", mode="brownfield", existing_repo=repo)
    assert isinstance(select_onramp(mission), BuilderOnramp)  # ne lève plus


def test_fullstack_synthesizes_profile_with_roles_and_commands(tmp_path: Path) -> None:
    repo = _fullstack(tmp_path)
    res = resolve_profile(repo)
    assert res.confidence == "inferred"
    prof = res.profile
    assert prof.has_ui is True
    assert set(prof.roles) == {"backend", "frontend"}
    assert prof.commands["backend"].test == "pytest"
    assert prof.pkg_managers["backend"] == "pip"
    assert prof.commands["frontend"].build == "npm run build"


def test_fullstack_substrate_declares_degradation_and_confidence(tmp_path: Path) -> None:
    repo = _fullstack(tmp_path)
    res = resolve_profile(repo)
    onramp = BuilderOnramp(
        profile=res.profile,
        confidence=res.confidence,
        code_runner=_CodeRunner(0),
        design_linter=_Linter(),
    )
    substrate = onramp.prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert substrate.declared_degradation  # non vide → HITL-0 déclenché en aval
    assert substrate.profile_confidence == "inferred"


# --- §7.7 HITL-0 sur profil résolu -----------------------------------------------------------
def test_hitl0_required_for_inferred_profile(tmp_path: Path) -> None:
    repo = _fullstack(tmp_path)
    res = resolve_profile(repo)
    substrate = BuilderOnramp(
        profile=res.profile, confidence=res.confidence,
        code_runner=_CodeRunner(0), design_linter=_Linter(),
    ).prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    with pytest.raises(HitlPending):
        require_hitl0("profil résolu", substrate)  # ManualGate par défaut → pause


# --- §7.2 Manifeste prioritaire (P-18) -------------------------------------------------------
_MANIFEST = """\
name = "flask-react"
has_ui = true

[roles]
backend = "backend"
frontend = "frontend"

[pkg_managers]
backend = "pip"
frontend = "npm"

[commands.backend]
test = "pytest -q"

[commands.frontend]
test = "npm test"
build = "npm run build"
"""


def test_manifest_wins_over_inference(tmp_path: Path) -> None:
    repo = _fullstack(tmp_path)  # signaux d'inférence présents...
    (repo / ".forge").mkdir()
    (repo / ".forge" / "profile.toml").write_text(_MANIFEST, encoding="utf-8")
    res = resolve_profile(repo)
    assert res.confidence == "manifest"  # ...mais le manifeste prime
    assert res.profile.name == "flask-react"
    assert res.profile.commands["backend"].test == "pytest -q"


def test_manifest_requires_name_and_roles(tmp_path: Path) -> None:
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge" / "profile.toml").write_text('has_ui = true\n', encoding="utf-8")
    with pytest.raises(ValueError, match="name"):
        resolve_profile(tmp_path)


# --- §7.3 Curés intacts ----------------------------------------------------------------------
def test_curated_fastapi_resolves_curated(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    res = resolve_profile(tmp_path)
    assert res.confidence == "curated"
    assert res.profile is FASTAPI_SAAS


def test_curated_fastapi_distance_a_no_hitl0_degradation(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "DESIGN.md").write_text("# D\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    sub = NoOnramp(code_runner=_CodeRunner(0), design_linter=_Linter()).prepare(
        cadrer("i", mode="brownfield", existing_repo=tmp_path), tmp_path
    )
    assert sub.profile_confidence == "curated"
    assert sub.declared_degradation == []  # tout vert → pas de HITL-0


# --- §7.4 Commandes par rôle (P-16) ----------------------------------------------------------
def test_role_gate_runs_each_role_in_its_dir_and_skips_empty(tmp_path: Path) -> None:
    profile = TargetProfile(
        name="g", code_check=None, has_ui=False,
        roles={"backend": "backend", "frontend": "frontend"},
        commands={"backend": RoleCommands(test="pytest"), "frontend": RoleCommands()},
    )
    rec = _CodeRunner(0)
    verdict = run_code_gate(tmp_path, profile=profile, runner=rec)
    assert verdict.passed is True
    assert rec.calls == [("pytest", tmp_path / "backend")]  # frontend (sans test) sauté
    assert any("frontend" in str(f) for f in verdict.findings)  # skip tracé


def test_role_gate_fails_if_a_role_command_fails(tmp_path: Path) -> None:
    profile = TargetProfile(
        name="g", code_check=None, has_ui=False,
        roles={"api": "api"}, commands={"api": RoleCommands(test="go test ./...")},
    )
    verdict = run_code_gate(tmp_path, profile=profile, runner=_CodeRunner(1))
    assert verdict.passed is False


# --- §7.5 Repo opaque ------------------------------------------------------------------------
def test_opaque_repo_raises_actionable_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"profile\.toml"):
        resolve_profile(tmp_path)


# --- §7.6 Analyse LLM (④) --------------------------------------------------------------------
class _FakeCli:
    def run(self, prompt: str, cwd: Path) -> str:
        return 'blabla {"has_ui": true, "commands": {"api": {"test": "go test ./..."}}} fin'


def test_analyze_fills_missing_commands(tmp_path: Path) -> None:
    from conductor.harness.profile_analyzer import analyze_profile_with_claude

    base = TargetProfile(
        name="g", code_check=None, has_ui=False,
        roles={"api": "."}, commands={"api": RoleCommands(test=None)},
    )
    out = analyze_profile_with_claude(tmp_path, base=base, cli=_FakeCli())
    assert out is not None
    assert out.commands["api"].test == "go test ./..."
    assert out.code_check == "go test ./..."
    assert out.has_ui is True


def test_resolve_uses_analyzer_when_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _fullstack(tmp_path)
    analyzed = synthesize_profile(repo, detect_capabilities(repo)).model_copy(
        update={"name": "analyzed-profile"}
    )
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "1")
    monkeypatch.setattr(profiles_mod, "_is_incomplete", lambda p: True)
    monkeypatch.setattr(
        "conductor.harness.profile_analyzer.analyze_profile_with_claude",
        lambda repo, *, base, cli=None: analyzed,
    )
    res = resolve_profile(repo)
    assert res.confidence == "analyzed"
    assert res.profile.name == "analyzed-profile"


def test_resolve_stays_inferred_without_opt_in(tmp_path: Path) -> None:
    res = resolve_profile(_fullstack(tmp_path))
    assert res.confidence == "inferred"  # ③ seul, pas d'appel LLM
