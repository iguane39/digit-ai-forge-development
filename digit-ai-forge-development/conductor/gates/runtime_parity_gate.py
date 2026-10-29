"""Gate « parité runtime » (TF-1042, mesure Produit-11 du 11/09/2026) — la douzième discipline
devient oracle exécutable.

LE FAIT. La chaîne testait en Python 3.12 (quatre tâches ``UsePythonVersion`` d'un pipeline
Azure DevOps) pendant que l'image servie partait de ``python:3.11-slim`` — une dépendance ou une
syntaxe disponible en 3.12 et absente en 3.11 passait la porte de tests et échouait au démarrage
du conteneur, APRÈS la porte, au moment où le coût est maximal. Le socle ne demandait ni
l'égalité des versions, ni l'inclusion du manifeste de runtime dans celui de test, ni un test
d'import dans l'image finale. Second effet mesuré le même jour, tenu côté
``digit-ai-forge-ops`` (règle O-10 d'``oracle-ops.mjs`` : épinglage à l'empreinte du manifeste
SERVI) — ce gate-ci couvre le versant construction : la parité entre l'environnement qui TESTE
et l'image qui SERT.

Convention documentée dans ``../../docs/run-playbook.md`` § « Produit livrable — disciplines de
production ». Contrôle STATIQUE, même posture heuristique que ``static_cache_gate`` /
``porte_neutralisee_gate`` (coïncidence de chaîne, aucune exécution, aucun réseau) : trois
vérifications indépendantes, chacune SKIP tracée quand son objet est absent — jamais un échec
fabriqué faute de matière à juger (P-06).

1. **interpreteur-disparite** — la version Python déclarée par la chaîne CI
   (``python-version:`` d'``actions/setup-python``, ou ``versionSpec:`` d'une tâche
   ``UsePythonVersion`` Azure Pipelines) diffère de celle du DERNIER ``FROM python:...`` du
   Dockerfile (l'image réellement servie, en build multi-étapes).
2. **manifeste-test-incomplet** / **manifeste-test-absent** — le manifeste de dépendances de
   TEST (``requirements-dev.txt`` ou équivalent connu) n'inclut pas (⊇) le manifeste de RUNTIME
   référencé par le Dockerfile (``-r <fichier>.txt`` d'une commande ``pip install``) : un paquet
   présent dans l'image et absent des tests n'est jamais exercé par la porte.
3. **test-import-absent** — l'image finale ne rejoue, à aucune étape ``RUN`` du Dockerfile,
   d'import Python (``python -c "import ..."`` ou équivalent) qui prouverait que les modules
   installés s'importent réellement dans l'environnement servi.

Périmètre v0, borné comme ``O-10`` d'oracle-ops : ``Dockerfile`` à la racine du projet (pas de
recherche récursive multi-Dockerfile), manifeste runtime au format ``requirements.txt`` (pip)
référencé par un ``-r`` littéral, image de base ``python:...`` officielle (une image dérivée sans
ce nom littéral est hors périmètre de la vérification 1, SKIP tracée).

4. **Compatibilité d'un Worker Cloudflare** (TF-1998, étude du pilot du 28/10/2026, ligne C6) —
   un Worker n'a pas d'image : son runtime est la version de ``workerd`` que fixe sa
   ``compatibility_date``, avec ses ``compatibility_flags``. La configuration Wrangler
   (``wrangler.json``, ``wrangler.jsonc`` ou ``wrangler.toml`` à la racine) dit ce qui SERT ; la
   configuration Vitest des Workers (``cloudflareTest()`` de ``@cloudflare/vitest-plugin``, ou
   l'ancien ``@cloudflare/vitest-pool-workers``) et le harnais ``createTestHarness`` disent ce qui
   TESTE. Faits lus le 29/10/2026 sur developers.cloudflare.com : ``compatibility_date`` est
   requise au déploiement et héritable par environnement (page « Configuration - Wrangler ») ;
   sans date, un test Vitest prend « the latest locally available date », et les options
   ``miniflare`` du test priment sur la configuration Wrangler (« Vitest integration »,
   « Configuration ») ; le harnais charge la racine par défaut (« Configure the test harness »).
   Cinq constats : **compat-date-absente**, **compat-test-date-implicite**,
   **compat-date-disparite**, **compat-flags-disparite**, **compat-env-disparite**. Sans
   configuration Wrangler, ce sous-contrôle ne s'ouvre pas : un projet conteneurisé garde le
   verdict d'avant TF-1998. Périmètre v0 : configurations à la racine, valeurs littérales (une
   date posée par une variable est tracée, jamais devinée), environnement tenu pour testé quand
   un ``createTestHarness`` d'un fichier de test le sélectionne par ``env`` littéral.
   L'option ``environment`` de ``cloudflareTest`` ne compte pas : la page lue ne lui prête que
   « bindings and variables », la date testée reste celle de la racine du ``configPath``.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from conductor.contracts import GateVerdict

# --- 1. Parité d'interpréteur -------------------------------------------------

_FROM_PYTHON = re.compile(r"^FROM\s+python:(?P<version>\d+\.\d+)", re.IGNORECASE | re.MULTILINE)
_GH_PYTHON_VERSION = re.compile(r"python-version:\s*[\"']?(?P<version>\d+\.\d+)", re.IGNORECASE)
_AZURE_TASK = re.compile(r"UsePythonVersion", re.IGNORECASE)
_AZURE_VERSION_SPEC = re.compile(r"versionSpec:\s*[\"']?(?P<version>\d+\.\d+)", re.IGNORECASE)


def _version_image(dockerfile_text: str) -> str | None:
    """La DERNIÈRE étape ``FROM python:...`` — celle qui compose l'image finale servie."""
    matches = list(_FROM_PYTHON.finditer(dockerfile_text))
    return matches[-1].group("version") if matches else None


def _versions_ci(project_dir: Path) -> list[dict[str, str]]:
    """Chaque version Python déclarée par la chaîne CI — GitHub Actions ou Azure Pipelines."""
    fichiers: list[Path] = []
    gh_dir = project_dir / ".github" / "workflows"
    if gh_dir.exists():
        fichiers += sorted(gh_dir.glob("*.yml")) + sorted(gh_dir.glob("*.yaml"))
    fichiers += sorted(project_dir.glob("azure-pipelines*.yml"))
    azure_dir = project_dir / ".azure-pipelines"
    if azure_dir.exists():
        fichiers += sorted(azure_dir.glob("*.yml")) + sorted(azure_dir.glob("*.yaml"))

    declarations: list[dict[str, str]] = []
    for fichier in fichiers:
        lignes = fichier.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, ligne in enumerate(lignes):
            m = _GH_PYTHON_VERSION.search(ligne)
            if m:
                declarations.append(
                    {"version": m.group("version"), "file": str(fichier), "ligne": str(i + 1)}
                )
                continue
            if _AZURE_TASK.search(ligne):
                fenetre = "\n".join(lignes[i : i + 6])
                m2 = _AZURE_VERSION_SPEC.search(fenetre)
                if m2:
                    declarations.append(
                        {"version": m2.group("version"), "file": str(fichier), "ligne": str(i + 1)}
                    )
    return declarations


def check_parite_interpreteur(project_dir: Path, dockerfile_text: str) -> list[dict[str, str]]:
    """Un constat par déclaration CI qui diffère de l'image — chaque occurrence nommée,
    jamais un total anonyme (une chaîne peut porter plusieurs tâches, TF-1042 en comptait
    quatre)."""
    version_image = _version_image(dockerfile_text)
    if version_image is None:
        return [
            {
                "skipped": "aucun 'FROM python:...' littéral dans le Dockerfile — "
                "image de base non officielle, hors périmètre v0"
            }
        ]
    declarations = _versions_ci(project_dir)
    if not declarations:
        return [
            {
                "skipped": "aucune version d'interpréteur déclarée par la chaîne CI "
                "(setup-python / UsePythonVersion) — rien à comparer"
            }
        ]
    findings: list[dict[str, str]] = []
    for d in declarations:
        if d["version"] == version_image:
            continue
        findings.append(
            {
                "kind": "interpreteur-disparite",
                "file": d["file"],
                "ligne": d["ligne"],
                "issue": f"CI déclare Python {d['version']}, l'image servie part de "
                f"python:{version_image} — une dépendance ou une syntaxe disponible dans l'un "
                "et absente de l'autre passe la porte de tests puis échoue au démarrage du "
                "conteneur, après la porte, au moment où le coût est maximal",
            }
        )
    return findings


# --- 2. Manifeste de test ⊇ manifeste de runtime ------------------------------

_RUNTIME_MANIFEST_REF = re.compile(r"-r\s+(?P<path>[^\s&|;]+\.txt)", re.IGNORECASE)
_TEST_MANIFEST_CANDIDATS = (
    "requirements-dev.txt",
    "requirements-test.txt",
    "requirements_test.txt",
    "dev-requirements.txt",
    "test-requirements.txt",
    "requirements/dev.txt",
    "requirements/test.txt",
)
_NOM_PAQUET = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def _paquets(manifest_text: str) -> set[str]:
    paquets: set[str] = set()
    for ligne_brute in manifest_text.splitlines():
        ligne = ligne_brute.strip()
        if not ligne or ligne.startswith("#") or ligne.startswith("-"):
            continue  # commentaire, -r/-e/--index-url... : rien à épingler
        m = _NOM_PAQUET.match(ligne)
        if m:
            paquets.add(m.group(1).lower().replace("_", "-"))
    return paquets


def check_manifeste_inclut_runtime(
    project_dir: Path, dockerfile_text: str
) -> list[dict[str, str]]:
    ref = _RUNTIME_MANIFEST_REF.search(dockerfile_text)
    if ref is None:
        return [
            {
                "skipped": "aucune commande 'pip install -r <fichier>.txt' dans le Dockerfile "
                "— hors périmètre v0 (pip/requirements.txt)"
            }
        ]
    chemin_declare = ref.group("path")
    runtime_path = project_dir / chemin_declare
    if not runtime_path.exists():
        return [
            {
                "skipped": f"manifeste runtime référencé introuvable sur disque : "
                f"{chemin_declare}"
            }
        ]
    runtime_paquets = _paquets(runtime_path.read_text(encoding="utf-8", errors="ignore"))
    if not runtime_paquets:
        return [
            {
                "skipped": f"manifeste runtime {chemin_declare} sans paquet épinglé — "
                "rien à couvrir"
            }
        ]
    test_path = next(
        (project_dir / c for c in _TEST_MANIFEST_CANDIDATS if (project_dir / c).exists()), None
    )
    if test_path is None:
        return [
            {
                "kind": "manifeste-test-absent",
                "file": str(runtime_path),
                "issue": f"{len(runtime_paquets)} paquet(s) runtime déclaré(s) "
                f"({chemin_declare}) et aucun manifeste de test connu à la racine — la porte "
                "de tests n'installe jamais ces paquets",
            }
        ]
    test_paquets = _paquets(test_path.read_text(encoding="utf-8", errors="ignore"))
    manquants = sorted(runtime_paquets - test_paquets)
    return [
        {
            "kind": "manifeste-test-incomplet",
            "file": str(test_path),
            "issue": f"paquet runtime '{p}' ({chemin_declare}) absent de {test_path.name} — "
            "jamais exercé par la porte de tests",
        }
        for p in manquants
    ]


# --- 3. Test d'import dans l'image finale -------------------------------------

_IMPORT_TEST = re.compile(
    r"^RUN\s+.*python[0-9.]*\s+(-c\s+[\"'].*\bimport\b|.*\b(smoke|import[_-]?test|test[_-]?import)\b)",
    re.IGNORECASE | re.MULTILINE,
)


def check_test_import(dockerfile_text: str, *, dockerfile_path: Path) -> list[dict[str, str]]:
    if _IMPORT_TEST.search(dockerfile_text):
        return []
    return [
        {
            "kind": "test-import-absent",
            "file": str(dockerfile_path),
            "issue": "aucune étape RUN de l'image finale ne rejoue d'import Python "
            '(`python -c "import ..."` ou équivalent) — rien ne prouve que les modules '
            "installés s'importent réellement dans l'image servie",
        }
    ]


# --- 4. Compatibilité d'un Worker (TF-1998) -------------------------------------

# Ordre de lecture retenu ici ; la documentation lue le 29/10/2026 ne dit pas lequel Wrangler
# préfère quand plusieurs coexistent : le cas est tracé, jamais tranché en silence.
_WRANGLER_CANDIDATS = ("wrangler.json", "wrangler.jsonc", "wrangler.toml")
_VITEST_CANDIDATS = tuple(
    f"vitest.config.{ext}" for ext in ("ts", "mts", "cts", "js", "mjs", "cjs")
)
_INTEGRATION_WORKERS = re.compile(r"@cloudflare/vitest-(?:plugin|pool-workers)")
_BLOC_WRANGLER = re.compile(r"\bwrangler\s*:\s*\{([^{}]*)\}")
_CONFIG_PATH = re.compile(r"\bconfigPath\s*:\s*[\"'`]([^\"'`]+)[\"'`]")
_DATE_TEST = re.compile(r"\bcompatibilityDate\s*:\s*[\"'`](\d{4}-\d{2}-\d{2})[\"'`]")
_DRAPEAUX_TEST = re.compile(r"\bcompatibilityFlags\s*:\s*\[([^\]]*)\]")
_CHAINE = re.compile(r"[\"'`]([^\"'`]+)[\"'`]")
_HARNAIS = re.compile(r"\bcreateTestHarness\s*\(")
_ENV_HARNAIS = re.compile(r"\benv\s*:\s*[\"'`]([^\"'`]+)[\"'`]")
_FICHIER_TEST = re.compile(r"\.(?:test|spec)\.[cm]?[jt]sx?$")
_EXCLUS = {"node_modules", ".wrangler", "dist", ".git", ".venv"}

Compat = tuple[str | None, frozenset[str] | None]


def _jsonc_vers_json(texte: str) -> str:
    """Retire les commentaires (``//``, ``/* */``) puis les virgules finales, HORS des chaînes :
    une URL ``https://…`` dans une valeur reste intacte (format JSONC de ``wrangler.jsonc``)."""
    sans_commentaires: list[str] = []
    i, n, dans_chaine = 0, len(texte), False
    while i < n:
        c = texte[i]
        if dans_chaine:
            sans_commentaires.append(c)
            if c == "\\" and i + 1 < n:
                sans_commentaires.append(texte[i + 1])
                i += 2
                continue
            dans_chaine = c != '"'
            i += 1
            continue
        if c == '"':
            dans_chaine = True
        elif texte.startswith("//", i):
            fin = texte.find("\n", i)
            i = n if fin == -1 else fin
            continue
        elif texte.startswith("/*", i):
            fin = texte.find("*/", i + 2)
            i = n if fin == -1 else fin + 2
            continue
        sans_commentaires.append(c)
        i += 1
    source = "".join(sans_commentaires)
    sortie: list[str] = []
    dans_chaine = False
    for j, c in enumerate(source):
        if dans_chaine:
            sortie.append(c)
            if c == '"' and source[j - 1] != "\\":
                dans_chaine = False
            continue
        if c == '"':
            dans_chaine = True
        elif c == ",":
            suite = source[j + 1 :].lstrip()
            if suite[:1] in ("}", "]"):
                continue
        sortie.append(c)
    return "".join(sortie)


def _config_wrangler(project_dir: Path) -> list[Path]:
    return [project_dir / nom for nom in _WRANGLER_CANDIDATS if (project_dir / nom).is_file()]


def _lire_wrangler(chemin: Path) -> dict[str, Any] | str:
    """La configuration lue, ou le motif pour lequel elle ne l'est pas (jamais une exception)."""
    texte = chemin.read_text(encoding="utf-8", errors="ignore")
    try:
        if chemin.suffix == ".toml":
            donnees: Any = tomllib.loads(texte)
        else:
            donnees = json.loads(_jsonc_vers_json(texte))
    except (tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        return f"configuration Wrangler illisible ({chemin.name}) : {exc}"
    if not isinstance(donnees, dict):
        return f"configuration Wrangler sans objet racine ({chemin.name})"
    return donnees


def _compat(section: Mapping[str, Any]) -> Compat:
    date = section.get("compatibility_date")
    drapeaux = section.get("compatibility_flags")
    lus: frozenset[str] | None = None
    if isinstance(drapeaux, list):
        lus = frozenset(d for d in drapeaux if isinstance(d, str))
    return (date if isinstance(date, str) else None, lus)


def _environnements(conf: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    envs = conf.get("env")
    if not isinstance(envs, dict):
        return {}
    return {str(nom): section for nom, section in envs.items() if isinstance(section, dict)}


def _lister(drapeaux: frozenset[str] | None) -> str:
    return "[" + ", ".join(sorted(drapeaux or ())) + "]"


def _environnements_testes(project_dir: Path) -> set[str]:
    """Environnements qu'un ``createTestHarness`` des fichiers de test sélectionne par ``env``."""
    choisis: set[str] = set()
    for chemin in sorted(project_dir.rglob("*")):
        if _EXCLUS.intersection(chemin.relative_to(project_dir).parts):
            continue
        if not chemin.is_file() or not _FICHIER_TEST.search(chemin.name):
            continue
        texte = chemin.read_text(encoding="utf-8", errors="ignore")
        if _HARNAIS.search(texte):
            choisis.update(_ENV_HARNAIS.findall(texte))
    return choisis


def _check_configuration_de_test(
    project_dir: Path, vitest: Path, servi: Path, racine: Compat
) -> list[dict[str, str]]:
    """R2 à R4 : ce que la configuration Vitest des Workers fait tourner, comparé au servi."""
    texte = vitest.read_text(encoding="utf-8", errors="ignore")
    if not _INTEGRATION_WORKERS.search(texte):
        return [
            {
                "skipped": f"{vitest.name} sans intégration Workers (@cloudflare/vitest-plugin) — "
                "ces tests ne tournent pas dans le runtime Workers, la parité n'a rien à "
                "comparer (leur couverture relève du pan workers de forge-tests)"
            }
        ]
    bloc = _BLOC_WRANGLER.search(texte)
    config_path = _CONFIG_PATH.search(bloc.group(1)) if bloc else None
    date_test = _DATE_TEST.search(texte)
    drapeaux_test = _DRAPEAUX_TEST.search(texte)
    traces: list[dict[str, str]] = []
    if date_test is None and "compatibilityDate" in texte:
        traces.append(
            {"skipped": f"{vitest.name} : compatibilityDate non littéral — hors périmètre v0"}
        )
    if date_test is None and config_path is None and "compatibilityDate" not in texte:
        return [
            {
                "kind": "compat-test-date-implicite",
                "file": str(vitest),
                "issue": "la configuration de test ne nomme ni wrangler.configPath ni "
                "compatibilityDate : les tests prennent « the latest locally available date » "
                f"pendant que {servi.name} sert la date {racine[0] or 'absente'} — pointer la "
                f"configuration servie (wrangler: {{ configPath: \"./{servi.name}\" }})",
            }
        ]
    # `wrangler.configPath` charge « main, compatibility settings and bindings » de la RACINE du
    # fichier ; `environment` n'y prend que « bindings and variables » (page Configuration) :
    # la date testée est donc celle de la racine, quel que soit l'environnement choisi.
    servi_compat = racine
    teste = servi_compat
    if config_path is not None:
        cible = (project_dir / config_path.group(1)).resolve()
        if cible != servi.resolve():
            lue = _lire_wrangler(cible) if cible.is_file() else f"{config_path.group(1)} absente"
            if isinstance(lue, str):
                return [*traces, {"skipped": f"configPath de {vitest.name} : {lue}"}]
            teste = _compat(lue)
    if date_test is not None:
        teste = (date_test.group(1), teste[1])
    if drapeaux_test is not None:
        teste = (teste[0], frozenset(_CHAINE.findall(drapeaux_test.group(1))))
    constats = list(traces)
    if teste[0] is not None and servi_compat[0] is not None and teste[0] != servi_compat[0]:
        constats.append(
            {
                "kind": "compat-date-disparite",
                "file": str(vitest),
                "issue": f"les tests tournent à la date {teste[0]}, {servi.name} sert la date "
                f"{servi_compat[0]} — un comportement du runtime ouvert entre les deux dates "
                "passe la porte de tests puis change en service ; aligner la date de test sur "
                "la date servie",
            }
        )
    if (teste[1] or frozenset()) != (servi_compat[1] or frozenset()):
        constats.append(
            {
                "kind": "compat-flags-disparite",
                "file": str(vitest),
                "issue": f"les tests tournent avec les drapeaux {_lister(teste[1])}, "
                f"{servi.name} sert {_lister(servi_compat[1])} — aligner les drapeaux de test "
                "sur les drapeaux servis",
            }
        )
    return constats


def check_parite_compatibilite(project_dir: Path) -> list[dict[str, str]]:
    """Sous-contrôle 4 : la date et les drapeaux de compatibilité servis sont ceux qui sont
    testés. Un constat par écart, localisé ; une trace pour ce qui n'est pas jugeable."""
    configs = _config_wrangler(project_dir)
    if not configs:
        return [{"skipped": "aucune configuration Wrangler à la racine — pas de Worker"}]
    servi = configs[0]
    findings: list[dict[str, str]] = []
    if len(configs) > 1:
        autres = ", ".join(c.name for c in configs[1:])
        findings.append(
            {
                "skipped": f"plusieurs configurations Wrangler à la racine : {servi.name} est "
                f"jugée, {autres} non — l'ordre de priorité de Wrangler n'est pas établi par "
                "la documentation lue le 29/10/2026"
            }
        )
    conf = _lire_wrangler(servi)
    if isinstance(conf, str):
        return [*findings, {"skipped": conf}]
    racine = _compat(conf)
    if racine[0] is None:
        findings.append(
            {
                "kind": "compat-date-absente",
                "file": str(servi),
                "issue": "aucune compatibility_date au niveau racine — Wrangler l'exige pour "
                "déployer, et un test sans date prend la plus récente du runtime local : la "
                "version servie n'est déclarée nulle part ; déclarer compatibility_date",
            }
        )
    envs = _environnements(conf)
    testes = _environnements_testes(project_dir)
    vitest = next((project_dir / n for n in _VITEST_CANDIDATS if (project_dir / n).is_file()), None)
    for nom, section in sorted(envs.items()):
        date, drapeaux = _compat(section)
        ecarts: list[str] = []
        if date is not None and date != racine[0]:
            ecarts.append(f"la date {date} (racine : {racine[0] or 'absente'})")
        if drapeaux is not None and drapeaux != (racine[1] or frozenset()):
            ecarts.append(f"les drapeaux {_lister(drapeaux)} (racine : {_lister(racine[1])})")
        if ecarts and nom not in testes:
            findings.append(
                {
                    "kind": "compat-env-disparite",
                    "file": str(servi),
                    "issue": f"l'environnement '{nom}' sert {' et '.join(ecarts)} ; les tests "
                    f"chargent la racine et aucune configuration de test ne sélectionne '{nom}' "
                    "— retirer la surcharge (l'environnement hérite alors de la racine), ou "
                    f"sélectionner '{nom}' dans un test (env de createTestHarness)",
                }
            )
    if vitest is None:
        findings.append(
            {
                "skipped": "aucune configuration Vitest à la racine — la parité de la "
                "configuration de test n'est pas jugée (la couverture des tests relève du pan "
                "workers de forge-tests)"
            }
        )
    else:
        findings += _check_configuration_de_test(project_dir, vitest, servi, racine)
    return findings


# --- Gate -----------------------------------------------------------------------


def run_runtime_parity_gate(project_dir: Path) -> GateVerdict:
    """P-06 : arborescence absente, ou ni Dockerfile ni configuration Wrangler → SKIP tracé
    (SANS_OBJET), jamais un échec implicite — rien de servi à comparer à ce qui est testé."""
    if not project_dir.exists():
        return GateVerdict(
            gate="runtime-parity",
            passed=True,
            findings=[{"skipped": f"arborescence projet absente : {project_dir}"}],
        )
    dockerfile_path = project_dir / "Dockerfile"
    worker = bool(_config_wrangler(project_dir))
    if not dockerfile_path.exists() and not worker:
        return GateVerdict(
            gate="runtime-parity",
            passed=True,
            findings=[
                {
                    "skipped": "aucun Dockerfile ni configuration Wrangler à la racine du projet "
                    "— non conteneurisé et sans Worker, hors périmètre (SANS_OBJET)"
                }
            ],
            log_ref=str(project_dir),
        )
    findings: list[dict[str, str]] = []
    if dockerfile_path.exists():
        dockerfile_text = dockerfile_path.read_text(encoding="utf-8", errors="ignore")
        findings += (
            check_parite_interpreteur(project_dir, dockerfile_text)
            + check_manifeste_inclut_runtime(project_dir, dockerfile_text)
            + check_test_import(dockerfile_text, dockerfile_path=dockerfile_path)
        )
    else:
        findings.append(
            {"skipped": "aucun Dockerfile à la racine du projet — sous-contrôles 1 à 3 SANS_OBJET"}
        )
    if worker:
        findings += check_parite_compatibilite(project_dir)
    blocking = [f for f in findings if "skipped" not in f]
    return GateVerdict(
        gate="runtime-parity", passed=not blocking, findings=findings, log_ref=str(project_dir)
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.runtime_parity_gate <project_dir>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m conductor.gates.runtime_parity_gate <project_dir>", file=sys.stderr)
        return 2
    verdict = run_runtime_parity_gate(Path(args[0]))
    if verdict.passed:
        print("runtime-parity gate: PASS")
        return 0
    blocking = [f for f in verdict.findings if "skipped" not in f]
    print(f"runtime-parity gate: FAIL ({len(blocking)} constat(s))", file=sys.stderr)
    for f in blocking:
        loc = f.get("ligne")
        localisation = f"{f['file']}:{loc}" if loc else f["file"]
        print(f"  - [{f['kind']}] {localisation} : {f['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
