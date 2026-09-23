"""Découverte des oracles de la forge (TF-1319) : les gates exécutables, LUS SUR LE DISQUE.

Le juge d'enclenchement du pilot confronte ce que cette forge DÉCOUVRE aux verdicts consignés au
ledger d'un run. La découverte vit à la racine du dépôt (`oracles/decouvrir-oracles.mjs`, contrat
commun du parc `digit-ai/decouverte-oracles@1`) ; cette recette la joue dans les deux sens :

  VERT  : un gate qui porte son propre point d'entrée est découvert, où que la règle commune
          `oracle[-_]*` en trouve d'autres ; un gate AJOUTÉ l'est au passage suivant.
  ROUGE : un gate sans point d'entrée, un `__init__.py`, une recette, une dépendance vendorisée,
          un environnement virtuel et une fixture ne sont JAMAIS pris pour des oracles ; une
          racine absente sort en 2 avec son motif.

Et un croisement sur le dépôt réel : l'attendu est recalculé ICI, en Python, sur les mêmes
fichiers — deux lectures indépendantes du disque doivent rendre la même liste.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

RACINE_DEPOT = Path(__file__).resolve().parents[2]
DECOUVRIR = RACINE_DEPOT / "oracles" / "decouvrir-oracles.mjs"
GATES = Path("digit-ai-forge-development") / "conductor" / "gates"
NODE = shutil.which("node")
SE_LANCE_SEUL = re.compile(r"^if\s+__name__\s*==\s*[\"']__main__[\"']\s*:", re.MULTILINE)

pytestmark = pytest.mark.skipif(
    NODE is None,
    reason="node absent du poste : la découverte (script Node, contrat commun du parc) "
    "n'est pas jouable ici — prérequis du poste, pas un défaut de la forge",
)


def _decouvre(racine: Path | None = None) -> tuple[int, dict[str, Any]]:
    assert NODE is not None
    args = [NODE, str(DECOUVRIR)] + (["--racine", str(racine)] if racine else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=False)
    donnees: dict[str, Any] = json.loads(r.stdout)
    return r.returncode, donnees


def _poser(racine: Path, rel: str, contenu: str = "# fixture de découverte\n") -> None:
    p = racine / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(contenu, encoding="utf-8")


_AVEC_ENTREE = 'def main() -> int:\n    return 0\n\n\nif __name__ == "__main__":\n    main()\n'
_SANS_ENTREE = "def evaluer() -> bool:\n    return True\n"


def test_le_depot_reel_rend_les_gates_executables_et_seulement_eux() -> None:
    code, j = _decouvre()
    assert code == 0
    assert j["contrat"] == "digit-ai/decouverte-oracles@1"
    assert j["forge"] == "digit-ai-forge-development"
    decouverts = {o["nom"] for o in j["oracles"]}
    for o in j["oracles"]:
        assert (RACINE_DEPOT / o["chemin"]).exists(), o["chemin"]
    attendus = {
        f.stem
        for f in (RACINE_DEPOT / GATES).glob("*_gate.py")
        if SE_LANCE_SEUL.search(f.read_text(encoding="utf-8"))
    }
    assert attendus, "aucun gate exécutable relu : le croisement ne prouverait rien"
    assert attendus <= decouverts, f"gates exécutables non découverts : {attendus - decouverts}"
    sans_entree = sorted(
        f.stem for f in (RACINE_DEPOT / GATES).glob("*_gate.py") if f.stem not in attendus
    )
    for nom in sans_entree:
        assert nom not in decouverts
        assert any(nom in n for n in j["non_juge"]), f"gate sans entrée non NOMMÉ : {nom}"


def test_fixture_verte_et_leurres_ROUGES(tmp_path: Path) -> None:
    _poser(tmp_path, f"{GATES.as_posix()}/alpha_gate.py", _AVEC_ENTREE)
    _poser(tmp_path, "scripts/oracle_beta.py")
    leurres = [
        f"{GATES.as_posix()}/beta_gate.py",
        f"{GATES.as_posix()}/__init__.py",
        "digit-ai-forge-development/tests/test_alpha_gate.py",
        "digit-ai-forge-development/vendor/bad/oracle_vendu.py",
        "digit-ai-forge-development/.venv/Lib/site-packages/oracle_dep.py",
        "fixtures/oracle_faux.py",
    ]
    for rel in leurres:
        _poser(tmp_path, rel, _SANS_ENTREE if rel.endswith("beta_gate.py") else _AVEC_ENTREE)
    code, j = _decouvre(tmp_path)
    assert code == 0
    assert sorted(o["nom"] for o in j["oracles"]) == ["alpha_gate", "oracle_beta"]
    chemins = {o["chemin"] for o in j["oracles"]}
    assert not chemins.intersection(leurres), chemins.intersection(leurres)
    assert any("beta_gate" in n for n in j["non_juge"]), "le gate sans point d'entrée n'est pas DIT"


def test_un_gate_AJOUTE_est_decouvert_sans_liste_a_tenir(tmp_path: Path) -> None:
    _poser(tmp_path, f"{GATES.as_posix()}/alpha_gate.py", _AVEC_ENTREE)
    assert [o["nom"] for o in _decouvre(tmp_path)[1]["oracles"]] == ["alpha_gate"]
    _poser(tmp_path, f"{GATES.as_posix()}/gamma_gate.py", _AVEC_ENTREE)
    assert [o["nom"] for o in _decouvre(tmp_path)[1]["oracles"]] == ["alpha_gate", "gamma_gate"]


def test_une_racine_absente_sort_en_2_avec_son_motif_ROUGE(tmp_path: Path) -> None:
    code, j = _decouvre(tmp_path / "n-existe-pas")
    assert code == 2
    assert j["oracles"] == []
    assert "introuvable" in j["motif"]
