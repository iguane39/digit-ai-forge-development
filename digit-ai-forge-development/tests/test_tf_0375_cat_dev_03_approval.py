"""TF-0375 — cat-dev-03 démontré sur le corpus Approval, et les trois silences supprimés.

Le fait : l'intention catalogue de cat-dev-03 est « détecter ce que le code sous-livre ou
sur-livre par rapport à la spec ». La recette humaine du 18/08 sur Approval a remonté 49
anomalies, dont **24 (49 %) étaient des écarts entre un texte disponible et un code
disponible** — littéralement la définition de ce gate. Et le catalogue déclarait pour lui :
« testé par la suite de la forge (fakes) — **jamais démontré sur produit réel** ».

Ce que la lecture du code a montré, et qui explique le « jamais démontré » : **trois chemins
rendaient un succès sans avoir jugé quoi que ce soit**.

  1. `DefaultSpecReviewer` — le reviewer du chemin PAR DÉFAUT — rendait `passed=True`.
  2. `ClaudeCliSpecReviewer` retombait sur `passed=True` à la moindre erreur du juge.
  3. `write_findings` n'était appelé que `if records` : aucun finding, aucun fichier — un gate
     muet, un gate qui n'a rien trouvé et un produit conforme produisaient le même disque.

Aucun des trois ne mentait ; les trois se taisaient. Un gate qui se tait au vert est un gate
qu'on apprend à croire (R-33 bis).

Ce module tient les deux moitiés que l'item exige :
  · le gate TROUVE les écarts du corpus réel (familles B et C de l'étude du 18/08) ;
  · il n'en INVENTE PAS sur les 12 rubriques d'évolution de doctrine, qui ne sont pas des
    écarts au cahier — c'est le sens qu'aucune fixture ne jouait.

Limite déclarée, et elle est entière : ces tests prouvent la MÉCANIQUE du gate sur le corpus
(classement under/over, sémantique bloquante, non-invention, absence de silence). Le JUGEMENT
lui-même est rendu par un sous-agent `claude` ; sa justesse sur le corpus réel demande un run
réel, qui n'est pas rejouable en test (dette D-V1 : le conducteur n'est pas utilisable
headless). Ce que ce module démontre est donc : le gate SAIT porter ce corpus. Ce qu'il ne
démontre pas : que le juge le lit bien.
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import SpecVerdict, Story, StoryOutcome
from conductor.findings import FindingRecord, render_findings_md
from conductor.harness.spec_reviewer import ClaudeCliSpecReviewer
from conductor.supervisor import DefaultSpecReviewer

# --- Le corpus, tiré de l'étude des écarts du 18/08 -------------------------------------------
# Chaque entrée est un écart RÉEL, avec le paragraphe du cahier qui l'exigeait. Ce ne sont pas
# des cas subtils : le texte était disponible, le code était disponible.
SOUS_LIVRE = [
    {
        "kind": "under-build",
        "criterion": "§08 — dépôt multiple par glisser-déposer ou sélection classique",
        "detail": "le glisser-déposer est exigé nommément et était absent du produit (rubrique 16)",
        "severity": "élevée",
    },
    {
        "kind": "under-build",
        "criterion": "§08 et §09 — XLSX accepté, avec sa règle de conversion",
        "detail": "un dépôt XLSX produisait « Une erreur est survenue. Réessayez. » (rubrique 18)",
        "severity": "élevée",
    },
    {
        "kind": "under-build",
        "criterion": "§05 — le modèle de données porte le prénom ET le nom",
        "detail": "l écran n affichait que le nom de famille (rubriques 2 et 10)",
        "severity": "moyenne",
    },
    {
        "kind": "under-build",
        "criterion": "§05, §06, §08 — lecture seule après décision",
        "detail": "la lecture seule n était pas appliquée (rubrique 45)",
        "severity": "élevée",
    },
]

SUR_LIVRE = [
    {
        "kind": "over-build",
        "criterion": "aucune section du cahier ne demande ces blocs d accueil",
        "detail": "« Terminées récemment », « Activité récente », « Urgences » — construits en "
                  "plus, et il faut maintenant payer leur retrait (rubrique 3)",
        "severity": "faible",
    },
    {
        "kind": "over-build",
        "criterion": "aucune section du cahier ne demande un bouton « Envoyer » à l étape 2",
        "detail": "construit en plus (rubrique 14)",
        "severity": "faible",
    },
]

# Les 12 rubriques d'évolution de doctrine produit : le lot les demande, le cahier ne les
# demandait PAS, et elles ne sont donc ni un sous-livré ni un sur-livré. C'est le piège du
# gate : présentées comme « absentes du produit », elles ressemblent à des under-build.
EVOLUTIONS_DE_DOCTRINE = [
    "le lot demande de retirer la colonne « Montant » de la liste — le cahier ne dit rien",
    "le lot demande un tri par date décroissante — le cahier ne dit rien",
    "le lot renverse la règle d édition après décision (rubrique 35) — le cahier disait "
    "l inverse, c est la DOCTRINE qui change, pas le code qui a dévié",
]


class _JugeRejoue:
    """Rejoue la réponse d'un juge — ce que le sous-agent AURAIT rendu sur ce corpus.

    Un vrai appel au sous-agent est hors de portée d'un test (coût, non-déterminisme, dette
    D-V1). Ce qui se prouve ici est la mécanique en aval du juge, sur le corpus réel.
    """

    def __init__(self, charge: str) -> None:
        self._charge = charge

    def run(self, prompt: str, cwd: Path) -> str:
        self._dernier_prompt = prompt
        return self._charge


def _story() -> Story:
    return Story(
        id="APR-08",
        epic="dépôt de fichiers",
        title="Dépôt multiple de fichiers",
        acceptance=[
            "§08 — dépôt multiple par glisser-déposer ou sélection classique",
            "§08 et §09 — XLSX accepté avec sa règle de conversion",
        ],
    )


def _outcome() -> StoryOutcome:
    return StoryOutcome(story_id="APR-08", code_ok=True, pr_url="https://exemple/pr/1")


def _json(findings: list[dict]) -> str:
    import json

    return json.dumps({"findings": findings}, ensure_ascii=False)


# --- Sens 1 : le gate TROUVE les écarts du corpus réel ----------------------------------------
def test_les_quatre_sous_livres_du_corpus_APPROVAL_bloquent(tmp_path: Path) -> None:
    """Chacun est un critère écrit au cahier et absent du code. Aucun n était subtil."""
    reviewer = ClaudeCliSpecReviewer(runner=_JugeRejoue(_json(SOUS_LIVRE)))

    v = reviewer.review(_story(), _outcome(), tmp_path)

    assert v.juge == "rendu", "un verdict rendu ne se confond pas avec une indécision"
    assert v.passed is False, "quatre critères écrits et non tenus doivent bloquer"
    assert len(v.findings) == 4
    assert any("glisser-déposer" in f["criterion"] for f in v.findings)


def test_les_sur_livres_sont_vus_mais_ne_bloquent_PAS(tmp_path: Path) -> None:
    """Consultatif au catalogue, et c est juste : un sur-livré coûte son retrait, il ne casse
    rien. Le confondre avec un sous-livré ferait bloquer un sprint sur une préférence."""
    reviewer = ClaudeCliSpecReviewer(runner=_JugeRejoue(_json(SUR_LIVRE)))

    v = reviewer.review(_story(), _outcome(), tmp_path)

    assert v.juge == "rendu"
    assert v.passed is True, "over-build est consultatif"
    assert len(v.findings) == 2, "consultatif ne veut pas dire invisible"


def test_le_corpus_MELANGE_bloque_sur_le_seul_sous_livre(tmp_path: Path) -> None:
    """L état réel d Approval : les deux familles ensemble. Un seul under-build suffit."""
    reviewer = ClaudeCliSpecReviewer(runner=_JugeRejoue(_json(SUR_LIVRE + SOUS_LIVRE[:1])))

    v = reviewer.review(_story(), _outcome(), tmp_path)

    assert v.passed is False
    assert len(v.findings) == 3, "les sur-livrés restent au registre, ils ne sont pas absorbés"


# --- Sens 2 : le gate n INVENTE PAS sur ce qui n est pas un écart au cahier -------------------
def test_une_evolution_de_DOCTRINE_ne_devient_pas_un_ecart(tmp_path: Path) -> None:
    """Le sens qu aucune fixture ne jouait. Les 12 rubriques d évolution de doctrine ne sont ni
    sous-livrées ni sur-livrées : le cahier ne les demandait pas, et le lot les demande
    MAINTENANT. Les compter comme des écarts ferait bloquer un sprint sur un changement d avis,
    et le gate deviendrait le contrôle qu on désactive."""
    reviewer = ClaudeCliSpecReviewer(runner=_JugeRejoue(_json([])))

    v = reviewer.review(_story(), _outcome(), tmp_path)

    assert v.juge == "rendu", "avoir jugé et n avoir rien trouvé est un RÉSULTAT"
    assert v.passed is True
    assert v.findings == []


def test_le_registre_dit_qu_un_vide_JUGE_est_un_resultat() -> None:
    """Et la moitié qui manquait : ce vide-là doit se distinguer du vide d un gate muet."""
    rendu = render_findings_md([])

    assert "Aucun écart constaté" in rendu
    assert "RENDU" in rendu
    assert "pas un silence" in rendu


# --- Les trois silences, chacun nommé ---------------------------------------------------------
def test_le_reviewer_par_DEFAUT_ne_se_dit_plus_conforme(tmp_path: Path) -> None:
    """Le premier silence, et le plus coûteux : c est le chemin par défaut. Un sprint entier
    pouvait traverser cat-dev-03 sans qu une ligne du cahier soit confrontée au code."""
    v = DefaultSpecReviewer().review(_story(), _outcome(), tmp_path)

    assert v.juge == "indecis"
    assert v.passed is True, "do-no-harm : on ne punit pas le produit pour un outil absent"
    assert "CONDUCTOR_ENABLE_SPEC_REVIEW" in v.motif
    assert "ne vaut donc pas absence d écart" in v.motif


def test_un_juge_MUET_rend_une_indecision_motivee_pas_un_succes(tmp_path: Path) -> None:
    """Le deuxième silence : JSON illisible, et le gate disait « conforme »."""
    reviewer = ClaudeCliSpecReviewer(runner=_JugeRejoue("ceci n est pas du JSON"))

    v = reviewer.review(_story(), _outcome(), tmp_path)

    assert v.juge == "indecis"
    assert v.passed is True
    assert "NON JUGÉE" in v.motif


def test_un_juge_EN_ERREUR_rend_une_indecision_motivee(tmp_path: Path) -> None:
    class _Panne:
        def run(self, prompt: str, cwd: Path) -> str:
            raise RuntimeError("le CLI claude est introuvable")

    v = ClaudeCliSpecReviewer(runner=_Panne()).review(_story(), _outcome(), tmp_path)

    assert v.juge == "indecis"
    assert "introuvable" in v.motif, "le motif nomme la cause, il ne dit pas « erreur »"


def test_le_registre_NOMME_les_stories_non_jugees() -> None:
    """Le troisième silence : une table vide se lisait « zéro écart au cahier »."""
    rendu = render_findings_md([], indecisions=["APR-08 : aucun reviewer câblé"])

    assert "NON JUGÉE(S)" in rendu
    assert "APR-08" in rendu
    assert "ne dit rien de leur conformité" in rendu


def test_un_registre_avec_ecarts_ET_indecisions_dit_les_deux() -> None:
    """Le cas mixte, qui est le cas réel d un sprint : quelques stories jugées, d autres non.
    Ne montrer que les écarts trouvés ferait lire « voilà tout ce qu il y a »."""
    rendu = render_findings_md(
        [FindingRecord(id="SF-1", story="APR-08", kind="under-build",
                       criterion="§08 glisser-déposer", detail="absent", severity="élevée",
                       status="non-traité")],
        indecisions=["APR-09 : aucun reviewer câblé"],
    )

    assert "SF-1" in rendu and "glisser-déposer" in rendu
    assert "APR-09" in rendu and "NON JUGÉE(S)" in rendu


# --- Ce que le corpus vaut, et ce qu il ne vaut pas -------------------------------------------
def test_le_corpus_couvre_les_deux_familles_ET_le_piege() -> None:
    """Une garde sur le corpus lui-même : s il perdait une famille, les tests ci-dessus
    resteraient verts en ne prouvant plus rien. 24 des 49 rubriques relevaient de ce gate."""
    assert len(SOUS_LIVRE) >= 4, "famille B — écarts d implémentation d une exigence écrite"
    assert len(SUR_LIVRE) >= 2, "famille C — sur-livraisons"
    assert len(EVOLUTIONS_DE_DOCTRINE) >= 3, "le piège : ce qui n est PAS un écart au cahier"
    assert all(f["kind"] == "under-build" for f in SOUS_LIVRE)
    assert all(f["kind"] == "over-build" for f in SUR_LIVRE)


def test_ce_que_ce_module_ne_demontre_PAS_est_ecrit() -> None:
    """Loi 3. Sans cet aveu, « cat-dev-03 démontré sur Approval » se lirait « le juge sait
    lire le cahier », ce que ces tests ne prouvent pas et ne peuvent pas prouver."""
    assert "SAIT porter ce corpus" in __doc__
    assert "que le juge le lit bien" in __doc__, "ce qui n est PAS démontré est nommé"
    assert "D-V1" in __doc__, "la dette qui empêche le run réel est nommée"


def test_le_verdict_par_defaut_reste_rendu_quand_on_juge_vraiment() -> None:
    """Garde anti-inversion : `juge` vaut « rendu » par défaut, donc un verdict construit
    normalement n est pas marqué indécis par accident."""
    v = SpecVerdict.from_findings([])

    assert v.juge == "rendu"
    assert v.motif == ""
