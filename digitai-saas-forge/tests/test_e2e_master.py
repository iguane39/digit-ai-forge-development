"""Test d'intégration maître (story 0.5).

À l'Epic 0, il vérifie le CÂBLAGE de la chaîne (l'ordre A→B→C→D→E est en place et
les étapes sont encore des stubs). À mesure que les Epics 1→3 implémentent les
étapes, ce test deviendra un vrai run de bout en bout et **cassera au moindre
breaking change d'un upstream** (NFR-3, risque 8 — décision 06).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import conductor.__main__ as cli


def test_cli_version_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0


def test_pipeline_order_is_wired_scaffold_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() câble A → onramp(B) → C → D → E ; l'onramp (scaffold-first) précède C."""
    from conductor.onramp.base import Substrate
    from conductor.profiles import FASTAPI_SAAS

    calls: list[str] = []

    def rec(name: str) -> Callable[..., object]:
        def _f(*_a: object, **_k: object) -> object:
            calls.append(name)
            return object()

        return _f

    class RecOnramp:
        def prepare(self, config: object, dest: Path) -> Substrate:
            calls.append("B")
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    monkeypatch.setattr(cli, "cadrer", rec("A"))
    monkeypatch.setattr(cli, "select_onramp", lambda _mission: RecOnramp())
    monkeypatch.setattr(cli, "lancer_planification", rec("C"))
    monkeypatch.setattr(cli, "preparer_sprint", rec("D"))
    monkeypatch.setattr(cli, "superviser", rec("E"))

    cli.run("idée de test")
    assert calls == ["A", "B", "C", "D", "E"]


def test_run_pauses_at_hitl1_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Défaut greenfield : on neutralise l'onramp (pas de copier) et l'install BMAD (pas de npx) ;
    la logique réelle de C atteint le point HITL non approuvé → HitlPending."""
    from conductor.contracts import MissionConfig
    from conductor.governance import HitlPending
    from conductor.onramp.base import Substrate
    from conductor.profiles import FASTAPI_SAAS

    class FakeOnramp:
        def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    monkeypatch.setattr(cli, "select_onramp", lambda _mission: FakeOnramp())
    monkeypatch.setattr("conductor.bmad_bridge.subprocess.run", lambda *a, **k: None)

    with pytest.raises(HitlPending):
        cli.run("un CRM pour artisans", workdir=tmp_path)
