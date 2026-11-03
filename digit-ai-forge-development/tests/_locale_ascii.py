"""Exécution d'une expression du produit sous une locale ASCII (TF-2068).

Les lectures de fichiers du conductor déclarent ``encoding="utf-8"`` pour ne pas dépendre de la
locale du poste. Cette déclaration n'est observable que si la locale n'est PAS UTF-8 : un poste
Windows en cp1252, un conteneur en ``LC_ALL=C``. La suite tourne en UTF-8 (CI Linux, devcontainer),
donc un mutant qui retire ou remplace ``encoding`` y vit sans que rien ne le contredise. Ce module
rejoue l'expression dans un processus fils dont la locale est ASCII et dont le mode UTF-8 est
désactivé : c'est l'entrée qui manquait pour distinguer ces mutants, pas un artifice de test.

Sous mutmut, le fils hérite de ``MUTANT_UNDER_TEST`` et importe le paquet depuis le même dossier
que le test (``mutants/``) : il exécute donc le mutant en cours, pas le source d'origine.
"""

from __future__ import annotations

import codecs
import json
import os
import subprocess
import sys
from pathlib import Path

import conductor

_PREAMBULE = (
    "import json, locale\n"
    "from pathlib import Path\n"
    "from conductor import sandbox\n"
    "from conductor.gates import ai_antipatterns_gate as g\n"
)


def evaluer_sous_locale_ascii(expression: str) -> object:
    """Évalue ``expression`` (noms disponibles : ``Path``, ``sandbox``, ``g`` = le gate
    anti-patterns) dans un processus fils en locale ASCII et rend son résultat JSON.

    Échoue si le fils plante (c'est ainsi qu'un mutant qui lit en ``strict`` se manifeste) ou si
    la locale du fils est restée UTF-8 : un banc qui ne force rien ne prouve rien.
    """
    racine = Path(conductor.__file__).resolve().parents[1]
    code = (
        _PREAMBULE
        + "print(json.dumps({'locale': locale.getpreferredencoding(False), 'valeur': "
        + expression
        + "}))\n"
    )
    env = {
        **os.environ,
        "LC_ALL": "C",
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONPATH": str(racine),
    }
    resultat = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert resultat.returncode == 0, resultat.stderr
    sortie = json.loads(resultat.stdout)
    assert codecs.lookup(sortie["locale"]).name != "utf-8", sortie["locale"]
    return sortie["valeur"]
