"""Test d'intégration maître (story 0.5).

À l'Epic 0, il vérifie le CÂBLAGE de la chaîne (l'ordre A→B→C→D→E est en place et
les étapes sont encore des stubs). À mesure que les Epics 1→3 implémentent les
étapes, ce test deviendra un vrai run de bout en bout et **cassera au moindre
breaking change d'un upstream** (NFR-3, risque 8 — décision 06).
"""

from __future__ import annotations

from collections.abc import Callable

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


def test_downstream_steps_not_yet_implemented() -> None:
    """A/B implémentés (Epic 1) ; C/D/E restent des stubs jusqu'à l'Epic 3."""
    from conductor.bmad_bridge import lancer_planification

    with pytest.raises(NotImplementedError):
        lancer_planification(object())  # type: ignore[arg-type]
