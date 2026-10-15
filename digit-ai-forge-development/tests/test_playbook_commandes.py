"""Les commandes que `docs/run-playbook.md` prescrit aux produits tournent sur leur cible.

Lot Produit-83 du 15/10/2026 (RV-2, RV-3, RV-4, RV-6 ; TF-1779, TF-1780, TF-1781, TF-1786) : quatre
passages du playbook, rejoués tels qu'écrits pendant un run réel, ont échoué ou menti.

- le filtre jq du gate de complétude lisait `.[].id` sur `EXIGENCES.json`, qui est un OBJET
  (`{"projet": …, "exigences": [...]}`) : jq s'arrête sur « Cannot index string with string "id" »
  (exit 5, mesuré sur un vrai référentiel de 80 exigences) ;
- l'exemple de nommage `test_facture_sans_client_E-042` n'est pas un identifiant Python : la
  définition `def test_facture_sans_client_E-042():` lève SyntaxError ;
- le playbook affirmait qu'aucune section « Contrat du projet audité » n'existe côté forge-tests,
  alors que le README de forge-tests la porte ;
- le motif grep « textes dans le fichier de ressources » signalait 17 fichiers React d'un produit
  internationalisé pour des valeurs d'attributs JSX (`"col"` 30 fois, `"button"` 26 fois).

Ces cas lisent le playbook lui-même : la commande corrigée ici est celle que les produits copient.
"""

from __future__ import annotations

import re
from pathlib import Path

PLAYBOOK = Path(__file__).resolve().parents[2] / "docs" / "run-playbook.md"


def _texte() -> str:
    return PLAYBOOK.read_text(encoding="utf-8")


def _bloc_bash_apres(repere: str) -> str:
    """Le premier bloc ```bash qui suit le repère donné dans le playbook."""
    texte = _texte()
    debut = texte.index(repere)
    ouverture = texte.index("```bash", debut)
    fermeture = texte.index("```", ouverture + len("```bash"))
    return texte[ouverture:fermeture]


def test_tf1779_le_filtre_jq_du_gate_lit_la_liste_exigences() -> None:
    bloc = _bloc_bash_apres("## Traçabilité des exigences")

    assert "'.[].id'" not in bloc, "EXIGENCES.json est un objet : .[] rend ses valeurs"
    assert ".exigences[]" in bloc, "le filtre parcourt la liste exigences du référentiel"
    assert 'select(.palier == "MVP")' in bloc, "le gate de complétude porte sur les exigences MVP"


def test_tf1780_les_noms_de_test_cites_en_exemple_sont_des_identifiants_python() -> None:
    noms = re.findall(r"`(test_[^`\s(]+)", _texte())

    assert noms, "le playbook cite au moins un exemple de nom de test"
    invalides = [n for n in noms if not n.isidentifier()]
    assert invalides == [], f"exemples qui lèvent SyntaxError dans un def : {invalides}"


def test_tf1781_le_playbook_ne_nie_plus_la_section_contrat_de_forge_tests() -> None:
    texte = _texte()

    assert "aucune section « Contrat du projet" not in texte
    assert "« Contrat du projet audité »" in texte, "le playbook renvoie à la section qui existe"


def _motifs_textes_affiches() -> list[re.Pattern[str]]:
    """Les motifs `grep -E` du contrôle 1, traduits de POSIX ERE vers `re`."""
    bloc = _bloc_bash_apres("Les textes du produit suivent le plancher d'écriture")
    bloc = bloc.split("# 2.")[0]
    motifs = re.findall(r"grep -[a-zA-Z]*E[a-zA-Z]* '([^']+)'", bloc)
    assert motifs, "le contrôle 1 porte au moins un motif grep -E"
    return [re.compile(m.replace("[[:space:]]", r"\s")) for m in motifs]


def _signale(ligne: str) -> bool:
    return any(m.search(ligne) for m in _motifs_textes_affiches())


def test_tf1786_une_valeur_d_attribut_jsx_n_est_pas_un_texte_affiche() -> None:
    """Cas conforme, mesuré sur un produit internationalisé : aucune de ces lignes ne s'affiche."""
    conformes = [
        '<td className="col">{t("liste.nom")}</td>',
        '<button type="button" onClick={ouvrir}>{t("actions.ouvrir")}</button>',
        '<Bouton variante="btn secondaire" />',
        'const etat = "carton";',
        "<p>{t('carte.vide')}</p>",
    ]
    signalees = [ligne for ligne in conformes if _signale(ligne)]

    assert signalees == [], f"faux positifs : {signalees}"


def test_tf1786_un_texte_affiche_en_litteral_est_signale() -> None:
    """Cas fautif : le texte que la personne lit est écrit en dur dans le composant."""
    fautives = [
        '<h1 className="titre">Oups, une erreur est survenue</h1>',
        "<button onClick={recharger}>Recharger</button>",
        '<button aria-label="Fermer la fenêtre" onClick={fermer}>×</button>',
        '<input placeholder="Rechercher un établissement" />',
    ]
    manquees = [ligne for ligne in fautives if not _signale(ligne)]

    assert manquees == [], f"textes affichés non signalés : {manquees}"
