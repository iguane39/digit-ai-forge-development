"""Le skill de référence `integre-openai-gemini` (TF-2108) tient dans la recette de la forge.

Le skill vit à la racine du dépôt (`.claude/skills/integre-openai-gemini/`) ; son contrôle est
un script Node, comme la découverte des oracles (`test_decouvrir_oracles.py`). Cette recette le
joue dans les deux sens et vérifie que la règle des données volatiles du playbook y renvoie
(loi n° 1 : une affordance est câblée ou n'existe pas).

  VERT  : le skill réel ne cite aucun identifiant de modèle ni prix hors de
          `modeles-et-dates.md` ; sa fixture verte passe ; son auto-test (cas à double sens)
          sort en 0.
  ROUGE : la fixture rouge (un identifiant et un prix dans le texte du skill) échoue en exit 1
          et nomme les fichiers fautifs, pas la table.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

RACINE_DEPOT = Path(__file__).resolve().parents[2]
SKILL = RACINE_DEPOT / ".claude" / "skills" / "integre-openai-gemini"
CONTROLE = SKILL / "scripts" / "controle-modeles.mjs"
SELF_TEST = SKILL / "scripts" / "self-test.mjs"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(
    NODE is None,
    reason="node absent du poste : le contrôle du skill (script Node, comme celui des skills du "
    "parc) n'est pas jouable ici — prérequis du poste, pas un défaut de la forge",
)


def _jouer(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    return subprocess.run(
        [NODE, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _controle(*args: str) -> tuple[int, dict[str, Any]]:
    r = _jouer(CONTROLE, *args)
    donnees: dict[str, Any] = json.loads(r.stdout)
    return r.returncode, donnees


def test_le_skill_existe_avec_ses_cinq_references() -> None:
    assert (SKILL / "SKILL.md").is_file()
    for nom in (
        "choisir",
        "modeles-et-dates",
        "tester-sans-depenser",
        "cles-donnees-couts",
        "migrations",
    ):
        assert (SKILL / "references" / f"{nom}.md").is_file(), nom


def test_le_skill_reel_ne_cite_aucun_modele_ni_prix_hors_de_sa_table() -> None:
    code, j = _controle()

    assert code == 0, j["constats"][:3]
    assert j["verdict"] == "PASS"
    assert "references/modeles-et-dates.md" in j["autorises"]


def test_la_fixture_rouge_echoue_pour_la_bonne_raison() -> None:
    code, j = _controle(
        str(SKILL / "fixtures" / "rouge" / "skill-fautif"),
        "--autorise",
        "references/modeles-et-dates.md",
    )

    assert code == 1
    fautifs = {c["fichier"] for c in j["constats"]}
    assert {"SKILL.fixture.md", "references/choisir.md"} <= fautifs
    assert "references/modeles-et-dates.md" not in fautifs


def test_la_fixture_verte_passe() -> None:
    code, j = _controle(
        str(SKILL / "fixtures" / "vert" / "skill-sain"),
        "--autorise",
        "references/modeles-et-dates.md",
    )

    assert code == 0
    assert j["constats"] == []


def test_l_auto_test_du_skill_sort_en_zero_sans_cas_rouge() -> None:
    r = _jouer(SELF_TEST)

    assert r.returncode == 0, r.stdout[-600:]
    assert " 0 ko," in r.stdout, r.stdout[-300:]


def test_le_playbook_renvoie_au_skill_pour_les_produits_qui_appellent_ces_api() -> None:
    playbook = (RACINE_DEPOT / "docs" / "run-playbook.md").read_text(encoding="utf-8")
    debut = playbook.index("Données volatiles en base")
    fin = playbook.index("Zéro affordance inerte", debut)

    assert "integre-openai-gemini" in playbook[debut:fin]
    assert "controle-modeles.mjs" in playbook[debut:fin]
