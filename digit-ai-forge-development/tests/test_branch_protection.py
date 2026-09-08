"""decrire_protection / resume_citable : lecture SOURCÉE de la protection de branche
(D-26 (a), TF-0886) — jamais une description reformulée de mémoire.

Deux fixtures à double sens :
- rouge (`_PROTECTION_REELLE_MESUREE_20260906`) : réponse RÉELLE de
  `gh api repos/iguane39/digit-ai-forge-development/branches/main/protection`, lue le
  06/09/2026 — `enforce_admins=false` DOIT produire un constat de contournement.
- verte (`_PROTECTION_SANS_CONTOURNEMENT`) : configuration synthétique où les
  administrateurs sont soumis — ne DOIT produire aucun constat.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from conductor.harness.branch_protection import (
    SubprocessGhBranchProtection,
    decrire_protection,
    resume_citable,
)

# Fixture rouge : réponse brute mesurée le 06/09/2026 (cf. docstring du module). Le compte
# propriétaire contourne d'office la revue et les deux contrôles requis.
_PROTECTION_REELLE_MESUREE_20260906: dict[str, Any] = {
    "required_status_checks": {"strict": True, "contexts": ["code", "design"]},
    "required_pull_request_reviews": {
        "dismiss_stale_reviews": False,
        "require_code_owner_reviews": False,
        "required_approving_review_count": 1,
    },
    "enforce_admins": {"enabled": False},
    "allow_force_pushes": {"enabled": False},
}

# Fixture verte : même revue/contrôles, mais administrateurs SOUMIS — aucun contournement.
_PROTECTION_SANS_CONTOURNEMENT: dict[str, Any] = {
    "required_status_checks": {"strict": True, "contexts": ["code", "design"]},
    "required_pull_request_reviews": {"required_approving_review_count": 1},
    "enforce_admins": {"enabled": True},
    "allow_force_pushes": {"enabled": False},
}


def test_configuration_reelle_declare_le_contournement_d_office() -> None:
    """Rouge : enforce_admins=false → contourne_d_office=True + constat nommé, jamais silencieux."""
    description = decrire_protection(_PROTECTION_REELLE_MESUREE_20260906)
    assert description.revue_requise is True
    assert description.approbations_requises == 1
    assert description.contextes_requis == ("code", "design")
    assert description.contexte_strict is True
    assert description.admins_soumis is False
    assert description.contourne_d_office is True
    assert any("enforce_admins=false" in c for c in description.constats)
    resume = resume_citable(description)
    assert "administrateurs NON soumis" in resume
    assert "Constats :" in resume


def test_configuration_sans_contournement_ne_declare_rien() -> None:
    """Verte : administrateurs soumis → aucun constat de contournement."""
    description = decrire_protection(_PROTECTION_SANS_CONTOURNEMENT)
    assert description.admins_soumis is True
    assert description.contourne_d_office is False
    assert description.constats == ()
    resume = resume_citable(description)
    assert "administrateurs soumis" in resume
    assert "Constats" not in resume


def test_force_push_autorise_est_aussi_un_constat_nomme() -> None:
    config: dict[str, Any] = {
        **_PROTECTION_SANS_CONTOURNEMENT,
        "allow_force_pushes": {"enabled": True},
    }
    description = decrire_protection(config)
    assert description.force_push_autorise is True
    assert any("allow_force_pushes=true" in c for c in description.constats)


def test_champs_absents_ne_font_pas_planter_la_lecture() -> None:
    """Une réponse API partielle (ex. dépôt sans revue configurée) reste décrite, pas une
    exception : les valeurs manquantes se lisent comme « non exigé », jamais une supposition
    de conformité."""
    description = decrire_protection({})
    assert description.revue_requise is False
    assert description.contextes_requis == ()
    assert description.admins_soumis is False
    assert description.contourne_d_office is True


def _completed(stdout: str, rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["gh"], returncode=rc, stdout=stdout, stderr="")


def test_subprocess_reader_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "conductor.harness.branch_protection.subprocess.run",
        lambda *a, **k: _completed(json.dumps(_PROTECTION_REELLE_MESUREE_20260906)),
    )
    config = SubprocessGhBranchProtection().read("iguane39", "digit-ai-forge-development", "main")
    assert config == _PROTECTION_REELLE_MESUREE_20260906


def test_subprocess_reader_nonzero_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "conductor.harness.branch_protection.subprocess.run",
        lambda *a, **k: _completed("", rc=1),
    )
    with pytest.raises(RuntimeError, match="gh"):
        SubprocessGhBranchProtection().read("iguane39", "digit-ai-forge-development")


def test_subprocess_reader_empty_output_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "conductor.harness.branch_protection.subprocess.run",
        lambda *a, **k: _completed(""),
    )
    with pytest.raises(RuntimeError, match="vide"):
        SubprocessGhBranchProtection().read("iguane39", "digit-ai-forge-development")
