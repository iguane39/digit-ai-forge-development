"""HITL-0 : valider la normalisation / carte d'archi avant la planification (brownfield)."""

from __future__ import annotations

import pytest

from conductor.governance import HitlPending, require_hitl0


class _Approve:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


class _Reject:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return False


def test_hitl0_passes_when_approved() -> None:
    require_hitl0("carte d'archi", {"x": 1}, gate=_Approve())  # ne lève pas


def test_hitl0_pauses_when_rejected() -> None:
    with pytest.raises(HitlPending, match="HITL-0"):
        require_hitl0("carte d'archi", {"x": 1}, gate=_Reject())


def test_hitl0_default_gate_pauses() -> None:
    with pytest.raises(HitlPending):
        require_hitl0("carte d'archi", {"x": 1})
