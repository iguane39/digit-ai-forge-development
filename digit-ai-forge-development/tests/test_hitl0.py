"""HITL-0 : valider la normalisation / carte d'archi avant la planification (brownfield)."""

from __future__ import annotations

import pytest

from conductor.governance import DelegatedGate, HitlPending, require_hitl0


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


# --- DelegatedGate (TF-0009) : mode déléguable, refus par défaut ------------------


def test_delegated_gate_approves_a_listed_prefix() -> None:
    """Fixture verte : le préfixe déclaré couvre le checkpoint (suffixe dynamique inclus)."""
    gate = DelegatedGate(["HITL-0"])
    assert gate.approve("HITL-0 — carte d'archi", {"x": 1}) is True
    require_hitl0("carte d'archi", {"x": 1}, gate=gate)  # ne lève pas


def test_delegated_gate_refuses_checkpoints_outside_policy() -> None:
    """Fixture rouge : un checkpoint hors politique reste refusé (même repli que ManualGate)."""
    gate = DelegatedGate(["HITL-0"])
    assert gate.approve("merge final (HITL 2)", []) is False
    with pytest.raises(HitlPending, match="HITL-0"):
        require_hitl0("carte d'archi", {"x": 1}, gate=DelegatedGate(["merge final (HITL 2)"]))


def test_delegated_gate_empty_policy_refuses_everything() -> None:
    """Fixture rouge : une politique vide n'approuve jamais rien (delta nul avec ManualGate)."""
    assert DelegatedGate([]).approve("HITL-0 — carte d'archi", {}) is False
    assert DelegatedGate().approve("HITL-0 — carte d'archi", {}) is False
