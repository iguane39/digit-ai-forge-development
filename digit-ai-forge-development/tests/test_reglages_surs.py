"""TF-2228 (D-178) : la création de projet joue les réglages classés `defaut` du registre du pilot.

Aucun appel réel à une plateforme : une plateforme simulée répond aux commandes du registre
(`PlateformeSimulee`) et une API de gestion simulée reçoit les migrations (`ApiGestionSimulee`).
La plateforme simulée garde son état : les assertions lisent cet état, pas le rapport du script.

Fixtures à double sens :
- verte : plateforme neuve, puis plateforme déjà conforme (rien n'est réécrit) ;
- rouge : écriture sans effet, offre refusée, plage ouverte, connexion directe, variable absente,
  choix non consigné, secret qui fuit — chacune doit produire un verdict NON vert, pour la bonne
  raison.

Le registre est une COPIE de fixture (`fixtures/reglages-surs-par-defaut.json`, identique au
registre joint à l'étude du 06/11/2026) : la recette ne dépend pas du fichier réel du pilot.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from conductor.process import ProcessResult
from conductor.reglages_surs import (
    LECTEURS,
    Decision,
    Reglage,
    ReglagesError,
    TransportUrllib,
    appliquer_migrations,
    charger_decisions,
    charger_registre,
    chemin_registre_pilot,
    connexions_directes,
    decouper_commande,
    jouer,
    jouer_reglage,
    main,
    masquer,
    substituer,
)

FIXTURE = Path(__file__).parent / "fixtures" / "reglages-surs-par-defaut.json"
REF = "abcdefghijklmnopqrst"
JETON_SUPABASE = "sbp_SECRET_TOKEN_123"
JETON_CLOUDFLARE = "cf_SECRET_TOKEN_456"
ENV = {
    "PROJECT_REF": REF,
    "SUPABASE_ACCESS_TOKEN": JETON_SUPABASE,
    "OWNER": "acme",
    "REPO": "produit",
    "ZONE_ID": "zone123",
    "CLOUDFLARE_API_TOKEN": JETON_CLOUDFLARE,
    "CIDR_DECLAREE_V4": "203.0.113.0/24",
    "CIDR_DECLAREE_V6": "2001:db8::/32",
    "ORG_SLUG": "org-acme",
}
HSTS_VOULU = {
    "enabled": True,
    "max_age": 31536000,
    "include_subdomains": False,
    "preload": False,
    "nosniff": True,
}


# --------------------------------------------------------------------------- plateformes simulées


class PlateformeSimulee:
    """Répond aux commandes du registre comme Supabase, GitHub et Cloudflare, avec un état."""

    def __init__(self, evenements: list[str] | None = None) -> None:
        self.tls = False
        self.v4 = ["0.0.0.0/0"]
        self.v6 = ["::/0"]
        self.etat_restriction = "applied"
        self.entitlement = "allowed"
        self.alertes = False
        self.https = "off"
        self.hsts: dict[str, Any] = {"enabled": False, "max_age": 0}
        self.protection_secrets = "disabled"
        self.pitr = False
        self.ecritures_sans_effet: set[str] = set()
        self.stderr_ecriture = ""
        self.appels: list[list[str]] = []
        self.evenements = evenements if evenements is not None else []

    # -- aides
    def _ecritures(self) -> list[list[str]]:
        return [a for a in self.appels if self._est_ecriture(a)]

    @staticmethod
    def _est_ecriture(args: Sequence[str]) -> bool:
        return "-X" in args

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult:
        assert all(isinstance(a, str) for a in args)
        self.appels.append(list(args))
        methode = args[args.index("-X") + 1] if "-X" in args else "GET"
        corps = json.loads(args[args.index("-d") + 1]) if "-d" in args else {}
        cible = " ".join(args)
        if args[0] == "curl":
            adresse = next(a for a in args if a.startswith("https://"))
        else:
            adresse = next(
                a
                for i, a in enumerate(args[2:], start=2)
                if not a.startswith("-") and args[i - 1] not in ("-X", "-f", "--jq", "--input")
            )
        self.evenements.append(f"{methode} {adresse}")
        if self._est_ecriture(args) and self.stderr_ecriture:
            return ProcessResult(22, "", self.stderr_ecriture)
        sortie = self._repondre(methode, adresse, corps, cible)
        if isinstance(sortie, ProcessResult):
            return sortie
        return ProcessResult(0, sortie, "")

    def _repondre(
        self, methode: str, adresse: str, corps: dict[str, Any], cible: str
    ) -> ProcessResult | str:
        ecrit = methode != "GET"
        if adresse.endswith("/ssl-enforcement"):
            if ecrit and "tls" not in self.ecritures_sans_effet:
                self.tls = corps["requestedConfig"]["database"]
            return json.dumps({"currentConfig": {"database": self.tls}})
        if "/network-restrictions" in adresse:
            if ecrit and "restriction" not in self.ecritures_sans_effet:
                self.v4, self.v6 = corps["dbAllowedCidrs"], corps["dbAllowedCidrsV6"]
            return json.dumps(
                {
                    "entitlement": self.entitlement,
                    "config": {"dbAllowedCidrs": self.v4, "dbAllowedCidrsV6": self.v6},
                    "status": self.etat_restriction,
                }
            )
        if adresse.endswith("/vulnerability-alerts"):
            if ecrit and "alertes" not in self.ecritures_sans_effet:
                self.alertes = True
                return ""
            return "" if self.alertes else ProcessResult(1, "", "gh: Not Found (HTTP 404)")
        if adresse.endswith("/settings/always_use_https"):
            if ecrit and "https" not in self.ecritures_sans_effet:
                self.https = corps["value"]
            return json.dumps({"result": {"value": self.https}})
        if adresse.endswith("/settings/security_header"):
            if ecrit and "hsts" not in self.ecritures_sans_effet:
                self.hsts = corps["value"]["strict_transport_security"]
            return json.dumps({"result": {"value": {"strict_transport_security": self.hsts}}})
        if adresse == f"repos/{ENV['OWNER']}/{ENV['REPO']}":
            if ecrit:
                self.protection_secrets = "enabled"
            return self.protection_secrets + "\n"
        if adresse.endswith("/database/backups"):
            return json.dumps({"pitr_enabled": self.pitr})
        raise AssertionError(f"commande non prévue par la plateforme simulée : {cible}")


class ApiGestionSimulee:
    """API de gestion Supabase : `POST …/database/query` avec l'historique de migrations."""

    def __init__(self, evenements: list[str] | None = None, inscrites: Sequence[str] = ()) -> None:
        self.inscrites = set(inscrites)
        self.requetes: list[str] = []
        self.urls: list[str] = []
        self.jetons: list[str] = []
        self.echec_sur: str | None = None
        self.evenements = evenements if evenements is not None else []

    def post_json(self, url: str, jeton: str, corps: dict[str, Any]) -> tuple[int, str]:
        sql = corps["query"]
        self.urls.append(url)
        self.jetons.append(jeton)
        self.requetes.append(sql)
        self.evenements.append(f"POST {url}")
        if self.echec_sur and self.echec_sur in sql:
            return 500, f"erreur serveur pour le jeton {jeton}"
        if sql.startswith("select version"):
            return 200, json.dumps([{"version": v} for v in sorted(self.inscrites)])
        if sql.startswith("begin;"):
            inscription = re.search(r"values \('(\d{14})'", sql)
            assert inscription is not None
            self.inscrites.add(inscription.group(1))
        return 200, "[]"


def _projet(tmp_path: Path, migrations: Sequence[tuple[str, str]] = ()) -> Path:
    projet = tmp_path / "projet"
    projet.mkdir(parents=True)
    if migrations:
        dossier = projet / "supabase" / "migrations"
        dossier.mkdir(parents=True)
        for nom, sql in migrations:
            (dossier / nom).write_text(sql, encoding="utf-8")
    return projet


TROIS_MIGRATIONS = (
    ("20261106100000_creer_clients.sql", "create table clients (id int);"),
    ("20261106100100_creer_factures.sql", "create table factures (id int);"),
    ("20261106100200_creer_avoirs.sql", "create table avoirs (id int);"),
)


def _joue(
    plateforme: PlateformeSimulee,
    projet: Path,
    *,
    env: dict[str, str] | None = None,
    api: ApiGestionSimulee | None = None,
    **options: Any,
) -> Any:
    return jouer(
        charger_registre(FIXTURE),
        ENV if env is None else env,
        plateforme,
        api or ApiGestionSimulee(plateforme.evenements),
        projet=projet,
        **options,
    )


def _statuts(rapport: Any) -> dict[str, str]:
    return {r.reglage.split(" (")[0]: r.statut for r in rapport.reglages}


# --------------------------------------------------------------------------- registre


def test_la_copie_de_fixture_est_le_registre_de_l_etude() -> None:
    registre = charger_registre(FIXTURE)
    assert len(registre) == 9
    assert sum(r.classement == "defaut" for r in registre) == 5
    assert sum(r.classement == "decision" for r in registre) == 4


def test_chemin_du_registre_du_pilot_suit_forge_root(tmp_path: Path) -> None:
    attendu = tmp_path / "digit-ai-factory" / "references" / "REGLAGES-SURS-PAR-DEFAUT.json"
    assert chemin_registre_pilot({"FORGE_ROOT": str(tmp_path)}) == attendu
    # Sans FORGE_ROOT : le parent du dépôt (C:\dev), comme les autres références du pilot.
    par_defaut = chemin_registre_pilot({})
    assert par_defaut.parts[-3:] == attendu.parts[-3:]
    assert par_defaut.parents[2] == Path(__file__).resolve().parents[2].parent


def test_registre_absent_est_refuse(tmp_path: Path) -> None:
    with pytest.raises(ReglagesError, match="introuvable"):
        charger_registre(tmp_path / "absent.json")


def _registre_modifie(tmp_path: Path, modifier: Any) -> Path:
    donnees = json.loads(FIXTURE.read_text(encoding="utf-8"))
    modifier(donnees)
    chemin = tmp_path / "registre.json"
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    return chemin


def test_registre_refuse_un_defaut_dont_un_critere_echoue(tmp_path: Path) -> None:
    """Rouge : la règle du pilot (« defaut seulement si c1 à c5 tenus ») s'applique aussi ici."""

    def degrader(donnees: list[dict[str, Any]]) -> None:
        donnees[0]["criteres"]["c3"]["verdict"] = "echoue"

    with pytest.raises(ReglagesError, match="c3 n'est pas tenu"):
        charger_registre(_registre_modifie(tmp_path, degrader))


def test_registre_refuse_un_secret_en_clair(tmp_path: Path) -> None:
    def fuir(donnees: list[dict[str, Any]]) -> None:
        donnees[0]["cmd_lire"] = donnees[0]["cmd_lire"].replace(
            "$SUPABASE_ACCESS_TOKEN", "sbp_0123456789"
        )

    with pytest.raises(ReglagesError, match="secret en clair"):
        charger_registre(_registre_modifie(tmp_path, fuir))


def test_registre_refuse_une_cle_absente(tmp_path: Path) -> None:
    def amputer(donnees: list[dict[str, Any]]) -> None:
        del donnees[2]["attendu"]

    with pytest.raises(ReglagesError, match="attendu"):
        charger_registre(_registre_modifie(tmp_path, amputer))


# --------------------------------------------------------------------------- commandes


def test_la_commande_est_coupee_au_filtre_et_a_echo() -> None:
    assert decouper_commande("curl -sS https://x/y -H 'A: b' | jq '.a'") == [
        "curl",
        "-sS",
        "https://x/y",
        "-H",
        "A: b",
    ]
    assert decouper_commande("gh api repos/$OWNER/$REPO/z --silent; echo $?") == [
        "gh",
        "api",
        "repos/$OWNER/$REPO/z",
        "--silent",
    ]
    # Un `|` entre guillemets appartient à l'argument (filtre --jq de gh) : il n'est pas coupé.
    assert decouper_commande("gh api x --jq '[.[].type] | sort'")[-1] == "[.[].type] | sort"


def test_la_substitution_ne_passe_pas_par_un_shell() -> None:
    jetons = substituer(["curl", "-H", "Authorization: Bearer $T"], {"T": "a; rm -rf /"})
    assert jetons == ["curl", "-H", "Authorization: Bearer a; rm -rf /"]


def test_une_variable_absente_ou_vide_est_refusee() -> None:
    with pytest.raises(ReglagesError, match="PROJECT_REF"):
        substituer(["x/$PROJECT_REF"], {})
    with pytest.raises(ReglagesError, match="PROJECT_REF"):
        substituer(["x/$PROJECT_REF"], {"PROJECT_REF": ""})


def test_masquer_retire_les_valeurs_de_secret() -> None:
    assert masquer("jeton sbp_SECRET_TOKEN_123 ici", ENV) == "jeton $SUPABASE_ACCESS_TOKEN ici"
    assert masquer(f"zone {ENV['ZONE_ID']}", ENV) == "zone zone123"  # pas un secret


# --------------------------------------------------------------------------- création


def test_creation_sur_plateforme_neuve_applique_puis_relit_les_cinq_defauts(
    tmp_path: Path,
) -> None:
    plateforme = PlateformeSimulee()
    rapport = _joue(plateforme, _projet(tmp_path))
    # L'état de la plateforme simulée, pas le rapport, est l'oracle.
    assert plateforme.tls is True
    assert plateforme.v4 == ["203.0.113.0/24"] and plateforme.v6 == ["2001:db8::/32"]
    assert plateforme.alertes is True
    assert plateforme.https == "on"
    assert plateforme.hsts == HSTS_VOULU
    statuts = _statuts(rapport)
    assert [s for s in statuts.values() if s == "applique"] == ["applique"] * 5
    assert [s for s in statuts.values() if s == "decision_en_attente"] == [
        "decision_en_attente"
    ] * 4
    assert rapport.vert is True


def test_chaque_defaut_est_lu_puis_ecrit_puis_relu(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    _joue(plateforme, _projet(tmp_path))
    tls = [e for e in plateforme.evenements if e.endswith("/ssl-enforcement")]
    assert [e.split(" ")[0] for e in tls] == ["GET", "PUT", "GET"]
    restriction = [e for e in plateforme.evenements if "/network-restrictions" in e]
    assert [e.split(" ")[0] for e in restriction] == ["GET", "POST", "GET"]


def test_les_secrets_sont_substitues_dans_l_appel_et_absents_du_rapport(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    rapport = _joue(plateforme, _projet(tmp_path))
    appels = " ".join(" ".join(a) for a in plateforme.appels)
    assert f"Bearer {JETON_SUPABASE}" in appels and f"Bearer {JETON_CLOUDFLARE}" in appels
    sortie = "\n".join(rapport.lignes())
    assert JETON_SUPABASE not in sortie and JETON_CLOUDFLARE not in sortie
    assert all("$" in c or c.startswith("aucune") for r in rapport.reglages for c in r.commandes)


def test_les_reglages_classes_decision_ne_sont_jamais_ecrits_sans_choix(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    _joue(plateforme, _projet(tmp_path))
    touches = " ".join(plateforme.evenements)
    assert "rulesets" not in touches and "billing/addons" not in touches
    assert "PATCH repos/acme/produit" not in touches
    assert plateforme.protection_secrets == "disabled" and plateforme.pitr is False


def test_la_creation_est_rejouable_sans_rien_reecrire(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    projet = _projet(tmp_path)
    _joue(plateforme, projet)
    nombre_ecritures = len(plateforme._ecritures())
    rapport = _joue(plateforme, projet)
    assert len(plateforme._ecritures()) == nombre_ecritures
    assert sorted(set(_statuts(rapport).values())) == ["decision_en_attente", "deja_conforme"]
    assert rapport.vert is True


def test_ROUGE_une_ecriture_sans_effet_est_un_ecart_meme_si_la_commande_reussit(
    tmp_path: Path,
) -> None:
    plateforme = PlateformeSimulee()
    plateforme.ecritures_sans_effet = {"tls"}
    rapport = _joue(plateforme, _projet(tmp_path))
    statuts = _statuts(rapport)
    assert statuts["TLS imposé sur les connexions Postgres"] == "ecart"
    assert rapport.vert is False
    detail = next(r.detail for r in rapport.reglages if r.statut == "ecart")
    assert "currentConfig.database = False" in detail


def test_ROUGE_hsts_ecrit_mais_relu_avec_includesubdomains_est_un_ecart(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    plateforme.ecritures_sans_effet = {"hsts"}
    plateforme.hsts = {**HSTS_VOULU, "include_subdomains": True}
    rapport = _joue(plateforme, _projet(tmp_path))
    assert _statuts(rapport)["En-tête HSTS de la zone"] == "ecart"


def test_ROUGE_offre_refusee_n_ecrit_pas_et_n_est_pas_verte(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    plateforme.entitlement = "disallowed"
    rapport = _joue(plateforme, _projet(tmp_path))
    statuts = _statuts(rapport)
    assert statuts["Restriction des adresses admises sur Postgres et le pooler"] == "saut_offre"
    assert plateforme.v4 == ["0.0.0.0/0"]
    assert rapport.vert is False


def test_ROUGE_plage_declaree_ouverte_ou_absente_n_ecrit_rien(tmp_path: Path) -> None:
    ouverte = PlateformeSimulee()
    rapport = _joue(ouverte, _projet(tmp_path), env={**ENV, "CIDR_DECLAREE_V4": "0.0.0.0/0"})
    cle = "Restriction des adresses admises sur Postgres et le pooler"
    assert _statuts(rapport)[cle] == "condition_non_tenue"
    assert not any("network-restrictions" in e and e.startswith("POST") for e in ouverte.evenements)
    sans_plage = PlateformeSimulee()
    env = {k: v for k, v in ENV.items() if k != "CIDR_DECLAREE_V6"}
    rapport = _joue(sans_plage, _projet(tmp_path / "b"), env=env)
    assert _statuts(rapport)[cle] == "variables_absentes"
    assert rapport.vert is False


def test_ROUGE_une_connexion_directe_interdit_la_restriction(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    (projet / ".github" / "workflows").mkdir(parents=True)
    (projet / ".github" / "workflows" / "deploy.yml").write_text(
        "run: supabase db push --db-url $URL\n", encoding="utf-8"
    )
    assert connexions_directes(projet)
    plateforme = PlateformeSimulee()
    rapport = _joue(plateforme, projet)
    cle = "Restriction des adresses admises sur Postgres et le pooler"
    assert _statuts(rapport)[cle] == "condition_non_tenue"
    detail = next(r.detail for r in rapport.reglages if r.reglage.startswith("Restr"))
    assert "deploy.yml" in detail and "supabase db push" in detail
    assert plateforme.v4 == ["0.0.0.0/0"]
    assert rapport.vert is False


def test_VERT_un_projet_sans_connexion_directe_tient_la_condition(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    (projet / "scripts").mkdir()
    (projet / "scripts" / "migrer.mjs").write_text(
        "fetch('https://api.supabase.com/v1/projects/x/database/query')\n", encoding="utf-8"
    )
    assert connexions_directes(projet) == []


def test_ROUGE_une_edge_function_compte_comme_connexion_directe(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    (projet / "supabase" / "functions" / "f").mkdir(parents=True)
    assert connexions_directes(projet) != []


def test_ROUGE_variables_absentes_sont_nommees_et_rien_n_est_lance(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    env = {k: v for k, v in ENV.items() if k not in ("ZONE_ID", "CLOUDFLARE_API_TOKEN")}
    rapport = _joue(plateforme, _projet(tmp_path), env=env)
    cloudflare = [r for r in rapport.reglages if r.plateforme == "Cloudflare"]
    assert {r.statut for r in cloudflare if r.classement == "defaut"} == {"variables_absentes"}
    assert "ZONE_ID" in cloudflare[0].detail and "CLOUDFLARE_API_TOKEN" in cloudflare[0].detail
    assert not any("cloudflare" in e for e in plateforme.evenements)
    assert rapport.vert is False


def test_une_plateforme_exclue_par_l_appelant_est_tracee_et_verte(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    env = {k: v for k, v in ENV.items() if k not in ("ZONE_ID", "CLOUDFLARE_API_TOKEN")}
    rapport = _joue(plateforme, _projet(tmp_path), env=env, plateformes=["Supabase", "GitHub"])
    assert {r.statut for r in rapport.reglages if r.plateforme == "Cloudflare"} == {"exclu"}
    assert rapport.vert is True


def test_simulation_ne_lance_aucune_commande_mais_signale_les_variables(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    api = ApiGestionSimulee()
    projet = _projet(tmp_path, TROIS_MIGRATIONS)
    rapport = _joue(plateforme, projet, api=api, simulation=True)
    assert plateforme.appels == [] and api.requetes == []
    assert {r.statut for r in rapport.reglages if r.classement == "defaut"} == {"simule"}
    assert rapport.migrations is not None and rapport.migrations.statut == "simule"
    manque = _joue(plateforme, projet, env={}, simulation=True)
    assert manque.vert is False


def test_lire_seulement_n_ecrit_jamais_et_rend_l_ecart(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    rapport = _joue(plateforme, _projet(tmp_path), lire_seulement=True)
    assert plateforme._ecritures() == []
    assert {r.statut for r in rapport.reglages if r.classement == "defaut"} == {"ecart"}
    assert rapport.vert is False
    assert rapport.migrations is None


def test_ROUGE_un_reglage_sans_lecteur_n_est_pas_vert() -> None:
    inconnu = Reglage(
        "Autre", "Réglage neuf", "curl -sS https://a/b", "curl https://a/c", "x", "y", "defaut"
    )
    resultat = jouer_reglage(inconnu, ENV, PlateformeSimulee(), projet=Path("."))
    assert resultat.statut == "lecteur_inconnu" and resultat.vert is False


def test_ROUGE_un_echec_d_ecriture_ne_laisse_fuir_aucun_secret(tmp_path: Path) -> None:
    plateforme = PlateformeSimulee()
    plateforme.stderr_ecriture = f"401 Unauthorized, jeton {JETON_SUPABASE} {JETON_CLOUDFLARE}"
    rapport = _joue(plateforme, _projet(tmp_path))
    echecs = [r for r in rapport.reglages if r.statut == "echec_commande"]
    assert echecs and rapport.vert is False
    sortie = "\n".join(rapport.lignes())
    assert JETON_SUPABASE not in sortie and JETON_CLOUDFLARE not in sortie
    assert "$SUPABASE_ACCESS_TOKEN" in sortie


# --------------------------------------------------------------------------- lecteurs


@pytest.mark.parametrize(
    ("fragment", "vert", "rouge"),
    [
        ("/ssl-enforcement", {"currentConfig": {"database": True}}, {"currentConfig": {}}),
        (
            "/settings/always_use_https",
            {"result": {"value": "on"}},
            {"result": {"value": "off"}},
        ),
        (
            "/settings/security_header",
            {"result": {"value": {"strict_transport_security": HSTS_VOULU}}},
            {"result": {"value": {"strict_transport_security": {**HSTS_VOULU, "max_age": 300}}}},
        ),
        (
            "/settings/security_header",
            {"result": {"value": {"strict_transport_security": HSTS_VOULU}}},
            {"result": {"value": {"strict_transport_security": {**HSTS_VOULU, "preload": True}}}},
        ),
        ("/database/backups", {"pitr_enabled": True}, {"pitr_enabled": False}),
        (
            "/rules/branches/",
            ["deletion", "non_fast_forward", "pull_request"],
            ["deletion", "pull_request"],
        ),
    ],
)
def test_lecteurs_json_vert_et_rouge(fragment: str, vert: Any, rouge: Any) -> None:
    lecteur = next(lec for motif, lec in LECTEURS if motif.search(fragment))
    assert lecteur.juger(ProcessResult(0, json.dumps(vert), ""), ENV).conforme is True
    assert lecteur.juger(ProcessResult(0, json.dumps(rouge), ""), ENV).conforme is False
    assert lecteur.juger(ProcessResult(0, "pas du json", ""), ENV).conforme is False


def test_lecteur_restriction_exige_les_plages_declarees_et_status_applied() -> None:
    lecteur = next(lec for motif, lec in LECTEURS if motif.search("/network-restrictions"))

    def etat(v4: list[str], v6: list[str], statut: str) -> ProcessResult:
        config = {"dbAllowedCidrs": v4, "dbAllowedCidrsV6": v6}
        return ProcessResult(0, json.dumps({"config": config, "status": statut}), "")

    ok = etat(["203.0.113.0/24"], ["2001:db8::/32"], "applied")
    assert lecteur.juger(ok, ENV).conforme is True
    assert (
        lecteur.juger(etat(["203.0.113.0/24"], ["2001:db8::/32"], "stored"), ENV).conforme is False
    )
    assert (
        lecteur.juger(etat(["198.51.100.0/24"], ["2001:db8::/32"], "applied"), ENV).conforme
        is False
    )
    assert lecteur.juger(etat(["0.0.0.0/0"], ["::/0"], "applied"), ENV).conforme is False


# --------------------------------------------------------------------------- décisions


def _decisions(tmp_path: Path, contenu: dict[str, Any]) -> Path:
    chemin = tmp_path / "decisions.json"
    chemin.write_text(json.dumps(contenu), encoding="utf-8")
    return chemin


CHOIX_SECRETS = (
    "Protection des secrets à la poussée d'un dépôt privé (secret_scanning_push_protection)"
)


def test_un_choix_consigne_appliquer_ecrit_puis_relit_un_reglage_decision(tmp_path: Path) -> None:
    decisions = charger_decisions(
        _decisions(
            tmp_path,
            {CHOIX_SECRETS: {"choix": "appliquer", "decide_par": "porteur", "date": "2026-11-06"}},
        )
    )
    plateforme = PlateformeSimulee()
    rapport = _joue(plateforme, _projet(tmp_path), decisions=decisions)
    assert plateforme.protection_secrets == "enabled"
    resultat = next(r for r in rapport.reglages if r.reglage == CHOIX_SECRETS)
    assert resultat.statut == "applique"


def test_une_exception_decidee_n_ecrit_rien_et_reste_verte(tmp_path: Path) -> None:
    decisions = {
        CHOIX_SECRETS: Decision("ne_pas_appliquer", "porteur", "2026-11-06"),
    }
    plateforme = PlateformeSimulee()
    rapport = _joue(plateforme, _projet(tmp_path), decisions=decisions)
    resultat = next(r for r in rapport.reglages if r.reglage == CHOIX_SECRETS)
    assert resultat.statut == "decision_consignee_non_appliquee"
    assert "porteur" in resultat.detail and plateforme.protection_secrets == "disabled"
    assert rapport.vert is True


def test_ROUGE_un_choix_flou_n_est_pas_un_choix_consigne(tmp_path: Path) -> None:
    for flou in (
        {"choix": "peut-être", "decide_par": "porteur", "date": "2026-11-06"},
        {"choix": "appliquer", "decide_par": "", "date": "2026-11-06"},
        {"choix": "appliquer", "decide_par": "porteur", "date": "demain"},
    ):
        with pytest.raises(ReglagesError, match="mal formée"):
            charger_decisions(_decisions(tmp_path, {CHOIX_SECRETS: flou}))


def test_ROUGE_un_choix_appliquer_sans_commande_est_un_geste_humain_non_vert(
    tmp_path: Path,
) -> None:
    mfa = (
        "Double vérification imposée aux membres de l'organisation "
        "(Require MFA to access organization)"
    )
    decisions = {mfa: Decision("appliquer", "porteur", "2026-11-06")}
    rapport = _joue(PlateformeSimulee(), _projet(tmp_path), decisions=decisions)
    resultat = next(r for r in rapport.reglages if r.reglage == mfa)
    assert resultat.statut == "geste_humain" and resultat.vert is False
    assert rapport.vert is False


# --------------------------------------------------------------------------- migrations


def test_migrations_par_l_api_de_gestion_en_https_dans_l_ordre_avec_inscription(
    tmp_path: Path,
) -> None:
    projet = _projet(tmp_path, TROIS_MIGRATIONS)
    api = ApiGestionSimulee()
    resultat = appliquer_migrations(projet, ENV, api)
    assert resultat.statut == "appliquees"
    assert resultat.appliquees == tuple(nom for nom, _ in TROIS_MIGRATIONS)
    assert api.inscrites == {nom[:14] for nom, _ in TROIS_MIGRATIONS}
    assert set(api.urls) == {f"https://api.supabase.com/v1/projects/{REF}/database/query"}
    assert set(api.jetons) == {JETON_SUPABASE}
    transactions = [r for r in api.requetes if r.startswith("begin;")]
    assert len(transactions) == 3 and all(t.rstrip().endswith("commit;") for t in transactions)
    assert [t for t in transactions if "create table clients" in t][0].index("insert into") > 0


def test_migrations_deja_inscrites_ne_sont_pas_rejouees(tmp_path: Path) -> None:
    projet = _projet(tmp_path, TROIS_MIGRATIONS)
    api = ApiGestionSimulee(inscrites=["20261106100000"])
    resultat = appliquer_migrations(projet, ENV, api)
    assert resultat.appliquees == (TROIS_MIGRATIONS[1][0], TROIS_MIGRATIONS[2][0])
    assert resultat.deja_inscrites == 1
    avant = len(api.requetes)
    deuxieme = appliquer_migrations(projet, ENV, api)
    assert deuxieme.statut == "a_jour" and deuxieme.appliquees == ()
    assert not any(r.startswith("begin;") for r in api.requetes[avant:])


def test_ROUGE_un_echec_de_l_api_arrete_la_suite_et_masque_le_jeton(tmp_path: Path) -> None:
    projet = _projet(tmp_path, TROIS_MIGRATIONS)
    api = ApiGestionSimulee()
    api.echec_sur = "create table factures"
    resultat = appliquer_migrations(projet, ENV, api)
    assert resultat.statut == "echec" and resultat.vert is False
    assert resultat.appliquees == (TROIS_MIGRATIONS[0][0],)
    assert "20261106100200" not in api.inscrites  # la troisième n'a pas été tentée
    assert "500" in resultat.detail and JETON_SUPABASE not in resultat.detail


def test_migrations_ignorent_les_fichiers_hors_convention_et_l_absence_de_dossier(
    tmp_path: Path,
) -> None:
    sans = appliquer_migrations(_projet(tmp_path / "a"), ENV, ApiGestionSimulee())
    assert sans.statut == "aucune" and sans.vert is True
    projet = _projet(tmp_path / "b", [("README.md", "x"), ("mauvais nom.sql", "x")])
    assert appliquer_migrations(projet, ENV, ApiGestionSimulee()).statut == "aucune"


def test_ROUGE_migrations_exigent_une_reference_de_projet_valide(tmp_path: Path) -> None:
    projet = _projet(tmp_path, TROIS_MIGRATIONS)
    api = ApiGestionSimulee()
    resultat = appliquer_migrations(projet, {**ENV, "PROJECT_REF": "../../autre"}, api)
    assert resultat.statut == "variables_absentes" and resultat.vert is False
    assert api.requetes == []


def test_le_transport_de_production_refuse_le_clair() -> None:
    with pytest.raises(ReglagesError, match="HTTPS"):
        TransportUrllib().post_json("http://api.supabase.com/v1/projects/x", "t", {"query": "x"})


def test_les_reglages_precedent_les_migrations_et_supabase_ref_sert_de_project_ref(
    tmp_path: Path,
) -> None:
    evenements: list[str] = []
    plateforme = PlateformeSimulee(evenements)
    api = ApiGestionSimulee(evenements)
    env = {k: v for k, v in ENV.items() if k != "PROJECT_REF"}
    env["SUPABASE_PROJECT_REF"] = REF
    projet = _projet(tmp_path, TROIS_MIGRATIONS)
    rapport = _joue(plateforme, projet, env=env, api=api)
    assert rapport.vert is True and rapport.migrations is not None
    premiere_migration = next(i for i, e in enumerate(evenements) if "database/query" in e)
    dernier_reglage = max(i for i, e in enumerate(evenements) if "database/query" not in e)
    assert dernier_reglage < premiere_migration
    # Le TLS imposé redémarre la base : il est écrit avant que la première migration ne parte.
    ecriture_tls = next(i for i, e in enumerate(evenements) if e.startswith("PUT") and "ssl" in e)
    assert ecriture_tls < premiere_migration


# --------------------------------------------------------------------------- ligne de commande


def test_main_rend_0_sur_vert_1_sur_manque_2_sur_registre_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    projet = _projet(tmp_path)
    arguments = ["--registre", str(FIXTURE), "--projet", str(projet)]
    vert = main(arguments, runner=PlateformeSimulee(), transport=ApiGestionSimulee(), env=ENV)
    assert vert == 0
    assert "VERDICT : VERT" in capsys.readouterr().out
    manque = main(arguments, runner=PlateformeSimulee(), transport=ApiGestionSimulee(), env={})
    assert manque == 1
    assert "variables_absentes" in capsys.readouterr().out
    assert main(["--registre", str(tmp_path / "absent.json")]) == 2
