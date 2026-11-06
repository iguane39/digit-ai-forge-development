"""Création de projet : réglages sûrs par défaut et migrations par l'API de gestion (TF-2228).

Décision D-178 (a) du 06/11/2026 : « réglage admissible appliqué à la création, vérifié à chaque
livraison, exception décidée ». Ce module est le point d'injection de l'implémentation. Il LIT le
registre du pilot (`references/REGLAGES-SURS-PAR-DEFAUT.json`, racine résolue comme pour les autres
références du pilot : `FORGE_ROOT`, sinon le parent de ce dépôt), puis :

- pour chaque réglage classé `defaut` : lit l'état (`cmd_lire`), n'écrit (`cmd_appliquer`) que s'il
  n'est pas déjà conforme, relit, et compare à l'attendu. Le verdict vient de la RELECTURE, jamais
  du code de sortie de l'écriture ;
- pour chaque réglage classé `decision` : n'écrit rien sans un choix consigné par l'humain
  (`--decisions`) ; sans choix, le réglage est rendu « en attente », sans échec ;
- les migrations de `supabase/migrations/` passent par l'API de gestion en HTTPS, comme dans le
  produit de référence (`scripts/migrer.mjs`) : aucune connexion directe à Postgres, ce qui est la
  condition de la restriction des adresses (les exécuteurs de GitHub n'ont pas d'adresse fixe).

Les commandes du registre portent des secrets sous la forme `$NOM` : ils sont lus dans
l'environnement, substitués jeton par jeton (jamais par un shell : P-08, `shell=False`), et ne
figurent ni dans le rapport ni dans les messages d'erreur. Aucun `.env` n'est lu.

Tout passe par des points d'injection (`ProcessRunner`, `TransportHttps`) : la recette joue ce
module sur des réponses simulées, sans appel réel à une plateforme.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from conductor.harness._text import clip
from conductor.process import ProcessResult, ProcessRunner, SubprocessProcessRunner

NOM_REGISTRE = Path("digit-ai-factory") / "references" / "REGLAGES-SURS-PAR-DEFAUT.json"
CLES_REGISTRE = (
    "plateforme",
    "reglage",
    "criteres",
    "cmd_appliquer",
    "cmd_lire",
    "attendu",
    "cmd_retour",
    "classement",
)
CRITERES = ("c1", "c2", "c3", "c4", "c5")
PREFIXE_GESTE_HUMAIN = "aucune commande"
OPERATEURS_SHELL = frozenset({"|", ";", "&&", "||", "&"})
_VARIABLE = re.compile(r"\$([A-Z][A-Z0-9_]*)")
_SECRET = re.compile(r"TOKEN|KEY|SECRET|PASSWORD", re.IGNORECASE)
_BEARER_EN_CLAIR = re.compile(r"Bearer\s+(?!\$)")
_REF_PROJET = re.compile(r"^[a-z0-9]{20}$")
_FICHIER_MIGRATION = re.compile(r"^\d{14}_[a-z0-9_]+\.sql$")
PLAGES_OUVERTES = frozenset({"0.0.0.0/0", "::/0"})
URL_GESTION = "https://api.supabase.com/v1/projects"

# Statuts d'un réglage. Un statut vert n'interdit rien ; tout autre statut est nommé au rapport
# et fait sortir le script en code 1 : un manque ne passe jamais pour une réussite.
STATUTS_VERTS = frozenset(
    {
        "deja_conforme",
        "applique",
        "simule",
        "exclu",
        "decision_en_attente",
        "decision_consignee_non_appliquee",
    }
)
STATUTS_MIGRATIONS_VERTS = frozenset({"aucune", "a_jour", "appliquees", "simule"})


class ReglagesError(RuntimeError):
    """Registre, décisions ou environnement inexploitables : le script refuse de jouer."""


# --------------------------------------------------------------------------- registre


@dataclass(frozen=True)
class Reglage:
    plateforme: str
    reglage: str
    cmd_appliquer: str
    cmd_lire: str
    attendu: str
    cmd_retour: str
    classement: str


def chemin_registre_pilot(env: Mapping[str, str] | None = None) -> Path:
    """Racine du pilot comme pour les autres références : `FORGE_ROOT`, sinon le parent du dépôt."""
    source = os.environ if env is None else env
    base = source.get("FORGE_ROOT")
    racine = Path(base) if base else Path(__file__).resolve().parents[3]
    return racine / NOM_REGISTRE


def charger_registre(chemin: Path | None = None) -> list[Reglage]:
    """Lit le registre et refuse tout ce que sa propre règle interdit.

    Règle du pilot : un réglage n'est classé `defaut` que si ses cinq criteres sont `tenu`.
    Un secret en clair dans une commande est refusé (les secrets s'écrivent `$NOM`).
    """
    cible = chemin if chemin is not None else chemin_registre_pilot()
    if not cible.is_file():
        raise ReglagesError(f"registre des réglages sûrs introuvable : {cible}")
    try:
        brut = json.loads(cible.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReglagesError(f"registre illisible ({cible.name}) : {exc}") from exc
    if not isinstance(brut, list) or not brut:
        raise ReglagesError("registre : une liste non vide d'entrées est attendue")
    reglages: list[Reglage] = []
    for position, entree in enumerate(brut, start=1):
        if not isinstance(entree, dict):
            raise ReglagesError(f"registre, entrée {position} : un objet est attendu")
        manquantes = [cle for cle in CLES_REGISTRE if cle not in entree]
        if manquantes:
            raise ReglagesError(f"registre, entrée {position} : clés absentes {manquantes}")
        classement = entree["classement"]
        if classement not in ("defaut", "decision"):
            raise ReglagesError(f"registre, entrée {position} : classement {classement!r} inconnu")
        if classement == "defaut":
            criteres = entree["criteres"]
            non_tenus = [
                c
                for c in CRITERES
                if not isinstance(criteres, dict)
                or (criteres.get(c) or {}).get("verdict") != "tenu"
            ]
            if non_tenus:
                raise ReglagesError(
                    f"registre, entrée {position} ({entree['reglage']}) : classé defaut alors que "
                    f"{', '.join(non_tenus)} n'est pas tenu"
                )
        for cle in ("cmd_appliquer", "cmd_lire", "cmd_retour"):
            if _BEARER_EN_CLAIR.search(str(entree[cle])):
                raise ReglagesError(
                    f"registre, entrée {position} : secret en clair dans {cle} (écrire $NOM)"
                )
        reglages.append(
            Reglage(
                plateforme=str(entree["plateforme"]),
                reglage=str(entree["reglage"]),
                cmd_appliquer=str(entree["cmd_appliquer"]),
                cmd_lire=str(entree["cmd_lire"]),
                attendu=str(entree["attendu"]),
                cmd_retour=str(entree["cmd_retour"]),
                classement=str(classement),
            )
        )
    return reglages


# --------------------------------------------------------------------------- décisions


@dataclass(frozen=True)
class Decision:
    choix: str  # "appliquer" | "ne_pas_appliquer"
    decide_par: str
    date: str


def charger_decisions(chemin: Path | None) -> dict[str, Decision]:
    """Choix consignés, clé = intitulé exact du réglage. Une entrée mal formée est refusée : un
    choix flou ne vaut pas choix consigné, et ne s'interprète pas en silence."""
    if chemin is None:
        return {}
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReglagesError(f"décisions illisibles ({chemin}) : {exc}") from exc
    if not isinstance(brut, dict):
        raise ReglagesError("décisions : un objet {intitulé du réglage: choix} est attendu")
    decisions: dict[str, Decision] = {}
    for intitule, valeur in brut.items():
        if (
            not isinstance(valeur, dict)
            or valeur.get("choix") not in ("appliquer", "ne_pas_appliquer")
            or not str(valeur.get("decide_par", "")).strip()
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(valeur.get("date", "")))
        ):
            raise ReglagesError(
                f"décision mal formée pour « {intitule} » : choix (appliquer | ne_pas_appliquer), "
                "decide_par et date (AAAA-MM-JJ) sont requis"
            )
        decisions[intitule] = Decision(valeur["choix"], str(valeur["decide_par"]), valeur["date"])
    return decisions


# --------------------------------------------------------------------------- commandes


def decouper_commande(commande: str) -> list[str]:
    """Jetons de la commande, coupés au premier opérateur shell (`|`, `;`...) : le filtre `jq` et
    `echo $?` du registre sont rejoués ici, en Python, par les lecteurs."""
    lexeur = shlex.shlex(commande, posix=True, punctuation_chars=True)
    lexeur.whitespace_split = True
    jetons: list[str] = []
    for jeton in lexeur:
        if jeton in OPERATEURS_SHELL:
            break
        jetons.append(jeton)
    if not jetons:
        raise ReglagesError(f"commande vide : {commande!r}")
    return jetons


def variables_requises(jetons: Sequence[str]) -> list[str]:
    noms: list[str] = []
    for jeton in jetons:
        for nom in _VARIABLE.findall(jeton):
            if nom not in noms:
                noms.append(nom)
    return noms


def substituer(jetons: Sequence[str], env: Mapping[str, str]) -> list[str]:
    """Remplace `$NOM` par sa valeur, jeton par jeton, sans shell. Variable absente ou vide :
    refus (une chaîne vide produirait un appel visant autre chose que prévu)."""
    absentes = [nom for nom in variables_requises(jetons) if not env.get(nom)]
    if absentes:
        raise ReglagesError(f"variables absentes : {', '.join(absentes)}")
    return [_VARIABLE.sub(lambda m: env[m.group(1)], jeton) for jeton in jetons]


def masquer(texte: str, env: Mapping[str, str]) -> str:
    """Retire du texte toute valeur de secret de l'environnement (jeton, clé, mot de passe)."""
    for nom, valeur in env.items():
        if _SECRET.search(nom) and len(valeur) >= 4:
            texte = texte.replace(valeur, f"${nom}")
    return texte


# --------------------------------------------------------------------------- lecteurs


@dataclass(frozen=True)
class Verdict:
    conforme: bool
    constat: str


def _json(sortie: str) -> Any:
    try:
        return json.loads(sortie)
    except json.JSONDecodeError:
        return None


def _champ(donnee: Any, *chemin: str) -> Any:
    for cle in chemin:
        if not isinstance(donnee, dict):
            return None
        donnee = donnee.get(cle)
    return donnee


def _lire_tls(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    valeur = _champ(_json(res.stdout), "currentConfig", "database")
    return Verdict(valeur is True, f"currentConfig.database = {valeur!r} (attendu true)")


def _plages_declarees(env: Mapping[str, str]) -> tuple[list[str], list[str]]:
    return [env.get("CIDR_DECLAREE_V4", "")], [env.get("CIDR_DECLAREE_V6", "")]


def _refus_plages(env: Mapping[str, str]) -> str | None:
    """Avant d'écrire : une plage ouverte ou absente ne restreint rien."""
    v4, v6 = _plages_declarees(env)
    if not all(v4 + v6):
        return "au moins une plage v4 et une plage v6 doivent être déclarées"
    if PLAGES_OUVERTES & set(v4 + v6):
        return "une plage déclarée est ouverte à tous (0.0.0.0/0 ou ::/0) : aucune restriction"
    return None


def _lire_restriction(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    donnee = _json(res.stdout)
    v4 = _champ(donnee, "config", "dbAllowedCidrs")
    v6 = _champ(donnee, "config", "dbAllowedCidrsV6")
    etat = _champ(donnee, "status")
    declarees_v4, declarees_v6 = _plages_declarees(env)
    constat = f"v4 = {v4!r}, v6 = {v6!r}, status = {etat!r}"
    ouverte = isinstance(v4, list) and isinstance(v6, list) and bool(PLAGES_OUVERTES & set(v4 + v6))
    conforme = v4 == declarees_v4 and v6 == declarees_v6 and etat == "applied" and not ouverte
    return Verdict(bool(conforme), constat + " (attendu : plages déclarées, status applied)")


def _offre_restriction_refusee(res: ProcessResult) -> bool:
    return bool(_champ(_json(res.stdout), "entitlement") == "disallowed")


def _lire_alertes(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    return Verdict(res.returncode == 0, f"code de sortie de gh = {res.returncode} (attendu 0)")


def _lire_https(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    valeur = _champ(_json(res.stdout), "result", "value")
    return Verdict(valeur == "on", f"result.value = {valeur!r} (attendu 'on')")


def _lire_hsts(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    hsts = _champ(_json(res.stdout), "result", "value", "strict_transport_security")
    duree = hsts.get("max_age") if isinstance(hsts, dict) else None
    conforme = (
        isinstance(hsts, dict)
        and hsts.get("enabled") is True
        and isinstance(duree, int)
        and duree >= 31536000
        and hsts.get("include_subdomains") is False
        and hsts.get("preload") is False
    )
    return Verdict(
        bool(conforme),
        f"strict_transport_security = {hsts!r} (attendu : actif, max_age >= 31536000, "
        "sans includeSubDomains ni preload)",
    )


def _lire_protection_secrets(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    valeur = res.stdout.strip()
    return Verdict(valeur == "enabled", f"secret_scanning_push_protection = {valeur!r}")


def _lire_ruleset(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    types = _json(res.stdout)
    requis = {"deletion", "non_fast_forward", "pull_request"}
    conforme = isinstance(types, list) and requis <= set(types)
    return Verdict(conforme, f"règles de la branche = {types!r} (attendu : {sorted(requis)})")


def _lire_pitr(res: ProcessResult, env: Mapping[str, str]) -> Verdict:
    valeur = _champ(_json(res.stdout), "pitr_enabled")
    return Verdict(valeur is True, f"pitr_enabled = {valeur!r} (attendu true)")


@dataclass(frozen=True)
class Lecteur:
    """Ce que `jq` et la comparaison à `attendu` font dans le registre, rejoué en Python."""

    juger: Callable[[ProcessResult, Mapping[str, str]], Verdict]
    refus_prealable: Callable[[Mapping[str, str]], str | None] | None = None
    offre_refusee: Callable[[ProcessResult], bool] | None = None
    exige_voie_api: bool = False


LECTEURS: tuple[tuple[re.Pattern[str], Lecteur], ...] = (
    (re.compile(r"/ssl-enforcement\b"), Lecteur(_lire_tls)),
    (
        re.compile(r"/network-restrictions\b"),
        Lecteur(
            _lire_restriction,
            refus_prealable=_refus_plages,
            offre_refusee=_offre_restriction_refusee,
            exige_voie_api=True,
        ),
    ),
    (re.compile(r"/vulnerability-alerts\b"), Lecteur(_lire_alertes)),
    (re.compile(r"/settings/always_use_https\b"), Lecteur(_lire_https)),
    (re.compile(r"/settings/security_header\b"), Lecteur(_lire_hsts)),
    (re.compile(r"secret_scanning_push_protection"), Lecteur(_lire_protection_secrets)),
    (re.compile(r"/rules/branches/"), Lecteur(_lire_ruleset)),
    (re.compile(r"/database/backups\b"), Lecteur(_lire_pitr)),
)


def lecteur_de(reglage: Reglage) -> Lecteur | None:
    for motif, lecteur in LECTEURS:
        if motif.search(reglage.cmd_lire):
            return lecteur
    return None


# --------------------------------------------------------------------------- connexions directes


MOTIFS_CONNEXION_DIRECTE = (
    re.compile(r"\bpsql\b"),
    re.compile(r"postgres(?:ql)?://"),
    re.compile(r"\bpsycopg"),
    re.compile(r"supabase\s+db\s+push"),
    re.compile(r"sslmode"),
)
DOSSIERS_CONTROLES = (".github", "scripts", "tests")
DOSSIERS_IGNORES = frozenset({".git", "node_modules", ".venv", "__pycache__"})


def connexions_directes(projet: Path) -> list[str]:
    """Traces d'une connexion directe à Postgres dans le projet (même contrôle que l'étude du
    06/11/2026 : `.github/`, `scripts/`, `tests/`, aucune Edge Function). Liste vide = condition
    de la restriction des adresses tenue."""
    traces: list[str] = []
    if (projet / "supabase" / "functions").is_dir():
        traces.append("supabase/functions : une Edge Function se connecte à Postgres")
    for nom in DOSSIERS_CONTROLES:
        racine = projet / nom
        if not racine.is_dir():
            continue
        for fichier in sorted(racine.rglob("*")):
            relatif = fichier.relative_to(projet)
            if not fichier.is_file() or DOSSIERS_IGNORES & set(relatif.parts):
                continue
            try:
                texte = fichier.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for motif in MOTIFS_CONNEXION_DIRECTE:
                if trouve := motif.search(texte):
                    traces.append(f"{relatif.as_posix()} : « {trouve.group(0)} »")
    return traces


# --------------------------------------------------------------------------- jeu d'un réglage


@dataclass(frozen=True)
class ResultatReglage:
    plateforme: str
    reglage: str
    classement: str
    statut: str
    detail: str = ""
    commandes: tuple[str, ...] = ()  # formes du registre, avec `$NOM` : jamais de secret

    @property
    def vert(self) -> bool:
        return self.statut in STATUTS_VERTS


def _executer(
    runner: ProcessRunner, commande: str, env: Mapping[str, str], projet: Path
) -> ProcessResult:
    jetons = substituer(decouper_commande(commande), env)
    return runner.run(jetons, cwd=projet, timeout_s=120)


def jouer_reglage(
    reglage: Reglage,
    env: Mapping[str, str],
    runner: ProcessRunner,
    *,
    projet: Path,
    decision: Decision | None = None,
    simulation: bool = False,
    lire_seulement: bool = False,
) -> ResultatReglage:
    def rendre(statut: str, detail: str = "", *commandes: str) -> ResultatReglage:
        return ResultatReglage(
            reglage.plateforme,
            reglage.reglage,
            reglage.classement,
            statut,
            masquer(detail, env),
            commandes,
        )

    if reglage.classement == "decision":
        if decision is None:
            return rendre("decision_en_attente", "aucun choix consigné : rien n'est écrit")
        if decision.choix == "ne_pas_appliquer":
            detail = f"exception décidée par {decision.decide_par} le {decision.date}"
            return rendre("decision_consignee_non_appliquee", detail)

    if reglage.cmd_appliquer.startswith(PREFIXE_GESTE_HUMAIN):
        return rendre("geste_humain", reglage.cmd_appliquer)
    lecteur = lecteur_de(reglage)
    if lecteur is None:
        return rendre("lecteur_inconnu", "aucun lecteur ne sait comparer ce réglage à son attendu")

    try:
        jetons_lire = decouper_commande(reglage.cmd_lire)
        jetons_appliquer = decouper_commande(reglage.cmd_appliquer)
    except ReglagesError as exc:
        return rendre("echec_commande", str(exc))
    absentes = variables_requises(jetons_lire + jetons_appliquer)
    absentes = [nom for nom in absentes if not env.get(nom)]
    if absentes:
        return rendre("variables_absentes", ", ".join(absentes))
    if lecteur.refus_prealable is not None and (refus := lecteur.refus_prealable(env)):
        return rendre("condition_non_tenue", refus)
    if lecteur.exige_voie_api and (traces := connexions_directes(projet)):
        return rendre(
            "condition_non_tenue",
            "la restriction des adresses exige des migrations par l'API de gestion ; "
            "connexion directe trouvée : " + " ; ".join(traces[:5]),
        )
    commandes = (reglage.cmd_lire, reglage.cmd_appliquer, reglage.cmd_lire)
    if simulation:
        return rendre("simule", "aucune commande lancée", *commandes)

    try:
        avant = _executer(runner, reglage.cmd_lire, env, projet)
        if lecteur.offre_refusee is not None and lecteur.offre_refusee(avant):
            return rendre("saut_offre", "l'offre de la plateforme n'autorise pas ce réglage")
        etat_avant = lecteur.juger(avant, env)
        if etat_avant.conforme:
            return rendre("deja_conforme", "relu conforme avant écriture : rien n'est écrit")
        if lire_seulement:
            return rendre("ecart", etat_avant.constat)
        ecriture = _executer(runner, reglage.cmd_appliquer, env, projet)
        if ecriture.returncode != 0:
            detail = f"écriture : code {ecriture.returncode}, {clip(ecriture.stderr, 300)}"
            return rendre("echec_commande", detail)
        apres = _executer(runner, reglage.cmd_lire, env, projet)
    except (RuntimeError, OSError) as exc:  # outil introuvable (ToolNotFound), délai dépassé
        return rendre("echec_commande", str(exc))

    verdict = lecteur.juger(apres, env)
    if verdict.conforme:
        return rendre("applique", "écrit puis relu conforme : " + verdict.constat)
    return rendre("ecart", "relu non conforme après écriture : " + verdict.constat)


# --------------------------------------------------------------------------- migrations


class TransportHttps(Protocol):
    def post_json(self, url: str, jeton: str, corps: dict[str, Any]) -> tuple[int, str]: ...


class TransportUrllib:
    """Transport de production : HTTPS seulement, délai borné. Jamais joué par la recette."""

    def __init__(self, *, timeout_s: int = 120) -> None:
        self._timeout_s = timeout_s

    def post_json(self, url: str, jeton: str, corps: dict[str, Any]) -> tuple[int, str]:
        if not url.startswith("https://"):
            raise ReglagesError(f"l'API de gestion ne se joint qu'en HTTPS : {url}")
        requete = urllib.request.Request(
            url,
            data=json.dumps(corps).encode("utf-8"),
            headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(requete, timeout=self._timeout_s) as reponse:
                return int(reponse.status), reponse.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")


@dataclass(frozen=True)
class ResultatMigrations:
    statut: str
    total: int = 0
    deja_inscrites: int = 0
    appliquees: tuple[str, ...] = ()
    detail: str = ""

    @property
    def vert(self) -> bool:
        return self.statut in STATUTS_MIGRATIONS_VERTS


def appliquer_migrations(
    projet: Path,
    env: Mapping[str, str],
    transport: TransportHttps,
    *,
    simulation: bool = False,
) -> ResultatMigrations:
    """Applique les migrations de `supabase/migrations/` non encore inscrites, par l'API de gestion.

    Même mécanique que `scripts/migrer.mjs` du produit de référence : l'historique est tenu dans
    `supabase_migrations.schema_migrations` (celui de la CLI de Supabase), et chaque migration
    passe dans une transaction avec son inscription. Aucune connexion directe à Postgres.
    """
    dossier = projet / "supabase" / "migrations"
    if not dossier.is_dir():
        return ResultatMigrations("aucune", detail="pas de supabase/migrations/")
    fichiers = sorted(f.name for f in dossier.iterdir() if _FICHIER_MIGRATION.match(f.name))
    if not fichiers:
        return ResultatMigrations("aucune", detail="supabase/migrations/ ne porte aucune migration")
    ref = env.get("PROJECT_REF", "")
    jeton = env.get("SUPABASE_ACCESS_TOKEN", "")
    if not _REF_PROJET.match(ref) or not jeton:
        return ResultatMigrations(
            "variables_absentes",
            total=len(fichiers),
            detail="PROJECT_REF (20 caractères) et SUPABASE_ACCESS_TOKEN sont requis",
        )
    if simulation:
        return ResultatMigrations(
            "simule",
            total=len(fichiers),
            appliquees=tuple(fichiers),
            detail="à appliquer sous réserve de l'historique (non lu en simulation)",
        )
    url = f"{URL_GESTION}/{ref}/database/query"

    def requete(sql: str) -> Any:
        code, corps = transport.post_json(url, jeton, {"query": sql})
        if not 200 <= code < 300:
            raise ReglagesError(f"API de gestion {code} : {clip(masquer(corps, env), 500)}")
        return json.loads(corps or "[]")

    appliquees: list[str] = []
    try:
        requete(
            "create schema if not exists supabase_migrations; "
            "create table if not exists supabase_migrations.schema_migrations "
            "(version text primary key, statements text[], name text);"
        )
        lignes = requete("select version from supabase_migrations.schema_migrations")
        inscrites = {ligne["version"] for ligne in lignes}
        for nom in fichiers:
            version, titre = nom[:14], nom[15:-4]
            if version in inscrites:
                continue
            sql = (dossier / nom).read_text(encoding="utf-8")
            requete(
                f"begin;\n{sql}\n;\ninsert into supabase_migrations.schema_migrations "
                f"(version, name) values ('{version}', '{titre}');\ncommit;"
            )
            appliquees.append(nom)
    except (ReglagesError, json.JSONDecodeError, KeyError, TypeError, OSError) as exc:
        return ResultatMigrations(
            "echec",
            total=len(fichiers),
            appliquees=tuple(appliquees),
            detail=masquer(str(exc), env),
        )
    deja = len(fichiers) - len(appliquees)
    statut = "appliquees" if appliquees else "a_jour"
    return ResultatMigrations(
        statut, total=len(fichiers), deja_inscrites=deja, appliquees=tuple(appliquees)
    )


# --------------------------------------------------------------------------- orchestration


@dataclass
class Rapport:
    reglages: list[ResultatReglage] = field(default_factory=list)
    migrations: ResultatMigrations | None = None

    @property
    def vert(self) -> bool:
        return all(r.vert for r in self.reglages) and (
            self.migrations is None or self.migrations.vert
        )

    def lignes(self) -> list[str]:
        sorties = [
            f"{'OK  ' if r.vert else 'NON '} {r.statut:<34} {r.plateforme} : {r.reglage}"
            + (f" — {r.detail}" if r.detail else "")
            for r in self.reglages
        ]
        if self.migrations is not None:
            m = self.migrations
            sorties.append(
                f"{'OK  ' if m.vert else 'NON '} {'migrations ' + m.statut:<34} "
                f"{m.total} fichier(s), {m.deja_inscrites} déjà inscrite(s), "
                f"{len(m.appliquees)} appliquée(s)" + (f" — {m.detail}" if m.detail else "")
            )
        sorties.append("VERDICT : " + ("VERT" if self.vert else "ROUGE (manques nommés ci-dessus)"))
        return sorties


def environnement_de_creation(env: Mapping[str, str]) -> dict[str, str]:
    """L'environnement du script. `SUPABASE_PROJECT_REF` (nom du produit de référence) sert de
    `PROJECT_REF` (nom du registre) quand ce dernier n'est pas posé."""
    complet = dict(env)
    if not complet.get("PROJECT_REF") and complet.get("SUPABASE_PROJECT_REF"):
        complet["PROJECT_REF"] = complet["SUPABASE_PROJECT_REF"]
    return complet


def jouer(
    registre: Sequence[Reglage],
    env: Mapping[str, str],
    runner: ProcessRunner,
    transport: TransportHttps,
    *,
    projet: Path,
    decisions: Mapping[str, Decision] | None = None,
    plateformes: Sequence[str] | None = None,
    simulation: bool = False,
    lire_seulement: bool = False,
) -> Rapport:
    """Joue le registre sur un projet. Ordre : les réglages d'abord (le TLS imposé redémarre la
    base : il ne doit pas couper une migration en cours), puis les migrations."""
    env = environnement_de_creation(env)
    choisies = {p.lower() for p in plateformes} if plateformes else None
    rapport = Rapport()
    for reglage in registre:
        if choisies is not None and reglage.plateforme.lower() not in choisies:
            rapport.reglages.append(
                ResultatReglage(
                    reglage.plateforme,
                    reglage.reglage,
                    reglage.classement,
                    "exclu",
                    "plateforme non retenue par l'appelant",
                )
            )
            continue
        rapport.reglages.append(
            jouer_reglage(
                reglage,
                env,
                runner,
                projet=projet,
                decision=(decisions or {}).get(reglage.reglage),
                simulation=simulation,
                lire_seulement=lire_seulement,
            )
        )
    if (choisies is None or "supabase" in choisies) and not lire_seulement:
        rapport.migrations = appliquer_migrations(projet, env, transport, simulation=simulation)
    return rapport


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: ProcessRunner | None = None,
    transport: TransportHttps | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    """CLI : `python -m conductor.reglages_surs [--projet DOSSIER] [--registre FICHIER]
    [--decisions FICHIER] [--plateformes A,B] [--simulation] [--lire-seulement]`.

    Code 0 : tout est vert. Code 1 : au moins un manque nommé (écart, variable absente, geste
    humain, condition non tenue). Code 2 : registre, décisions ou arguments inexploitables.
    """
    parseur = argparse.ArgumentParser(prog="conductor.reglages_surs", description=__doc__)
    parseur.add_argument("--projet", type=Path, default=Path.cwd())
    parseur.add_argument("--registre", type=Path, default=None)
    parseur.add_argument("--decisions", type=Path, default=None)
    parseur.add_argument("--plateformes", default=None, help="ex. Supabase,GitHub")
    parseur.add_argument("--simulation", action="store_true")
    parseur.add_argument("--lire-seulement", action="store_true")
    args = parseur.parse_args(sys.argv[1:] if argv is None else list(argv))
    try:
        registre = charger_registre(args.registre)
        decisions = charger_decisions(args.decisions)
    except ReglagesError as exc:
        print(f"refus : {exc}", file=sys.stderr)
        return 2
    rapport = jouer(
        registre,
        os.environ if env is None else env,
        runner or SubprocessProcessRunner(),
        transport or TransportUrllib(),
        projet=args.projet,
        decisions=decisions,
        plateformes=args.plateformes.split(",") if args.plateformes else None,
        simulation=args.simulation,
        lire_seulement=args.lire_seulement,
    )
    print("\n".join(rapport.lignes()))
    return 0 if rapport.vert else 1


if __name__ == "__main__":
    raise SystemExit(main())
