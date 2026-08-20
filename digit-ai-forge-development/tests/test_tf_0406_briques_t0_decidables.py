"""TF-0406 (RF-8, lot SCC-FR) — le contrat exposait une décision que le code écrasait.

`cadrer()` accepte `bricks: [{name, decision: build|buy|skip}]` — mais multi-tenancy, rbac et
auth-sso étaient FORCÉES en build, le skip écrasé en silence. Pour une vitrine sans espace
connecté (redirection simple, aucune auth côté site), les trois étaient greffées sans objet.
Second point du même ordre : une seule cible de scaffold (fastapi-saas), qu'un produit
Next.js/Strapi n'apprenait qu'en lisant scaffold.py. Un contrat qui accepte un argument sans
effet coûte plus cher qu'un contrat qui le refuse.
"""

from __future__ import annotations

import pytest

from conductor.cadrage import CIBLES_CONNUES, cadrer
from conductor.catalog import T0_BRICKS, resolve_bricks
from conductor.contracts import BrickChoice


def test_le_cas_vitrine_les_trois_t0_skippees_ne_sont_pas_greffees() -> None:
    """Le cas fondateur : SCC.FR, vitrine sans espace connecté."""
    scope = [BrickChoice(name=n, decision="skip") for n in T0_BRICKS]

    assert resolve_bricks(scope) == []


def test_une_t0_absente_du_scope_reste_forcee() -> None:
    """Le défaut PROTECTEUR survit : ne rien dire n'est pas skipper — seule une décision
    explicite est honorée, l'oubli ne désactive rien."""
    resolved = [b.name for b in resolve_bricks([])]

    assert set(T0_BRICKS) <= set(resolved)


def test_une_cible_inconnue_est_refusee_en_nommant_les_admises() -> None:
    """La mono-cible se déclare au contrat, plus au seul code."""
    with pytest.raises(ValueError) as erreur:
        cadrer("une idee", target="node-ts")

    assert "fastapi-saas" in str(erreur.value), "les cibles admises sont NOMMÉES dans le refus"
    assert "brownfield" in str(erreur.value), "le refus dit la voie de sortie, pas juste non"


def test_la_cible_admise_passe() -> None:
    config = cadrer("une idee", target=CIBLES_CONNUES[0])

    assert config.target == "fastapi-saas"
