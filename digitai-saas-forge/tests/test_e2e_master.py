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
    """run() doit câbler A→B→C→D→E ; B (scaffold) appelé avant C (BMAD) — décision 02."""
    calls: list[str] = []

    def rec(name: str) -> Callable[..., object]:
        def _f(*_a: object, **_k: object) -> object:
            calls.append(name)
            return object()

        return _f

    monkeypatch.setattr(cli, "cadrer", rec("A"))
    monkeypatch.setattr(cli, "scaffold", rec("B"))
    monkeypatch.setattr(cli, "lancer_planification", rec("C"))
    monkeypatch.setattr(cli, "preparer_sprint", rec("D"))
    monkeypatch.setattr(cli, "superviser", rec("E"))

    cli.run("idée de test")
    assert calls == ["A", "B", "C", "D", "E"]
    assert calls.index("B") < calls.index("C")  # scaffold-first


def test_run_pauses_at_hitl1_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Avec les défauts (ManualGate), la chaîne s'arrête à HITL 1 : gouvernance, pas échec.

    On neutralise le scaffold (B, pas de copier réseau) et l'install BMAD (pas de npx),
    puis on laisse la logique réelle de C atteindre le point HITL non approuvé.
    """
    import conductor.__main__ as cli
    from conductor.contracts import ScaffoldResult
    from conductor.governance import HitlPending

    def fake_scaffold(_config: object, dest: Path, **_kw: object) -> ScaffoldResult:
        return ScaffoldResult(repo_path=dest, ci_harness_ready=True, design_md_path=dest / "d.md")

    monkeypatch.setattr(cli, "scaffold", fake_scaffold)
    # pas de réseau : on neutralise l'install BMAD (npx)
    monkeypatch.setattr("conductor.bmad_bridge.subprocess.run", lambda *a, **k: None)

    with pytest.raises(HitlPending):
        cli.run("un CRM pour artisans", workdir=tmp_path)
