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
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

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


# --- Gate -----------------------------------------------------------------------


def run_runtime_parity_gate(project_dir: Path) -> GateVerdict:
    """P-06 : arborescence absente ou sans Dockerfile → SKIP tracé (SANS_OBJET), jamais un
    échec implicite — un projet non conteneurisé n'a pas d'image servie à comparer."""
    if not project_dir.exists():
        return GateVerdict(
            gate="runtime-parity",
            passed=True,
            findings=[{"skipped": f"arborescence projet absente : {project_dir}"}],
        )
    dockerfile_path = project_dir / "Dockerfile"
    if not dockerfile_path.exists():
        return GateVerdict(
            gate="runtime-parity",
            passed=True,
            findings=[
                {
                    "skipped": "aucun Dockerfile à la racine du projet — non conteneurisé, "
                    "hors périmètre (SANS_OBJET)"
                }
            ],
            log_ref=str(project_dir),
        )
    dockerfile_text = dockerfile_path.read_text(encoding="utf-8", errors="ignore")
    findings = (
        check_parite_interpreteur(project_dir, dockerfile_text)
        + check_manifeste_inclut_runtime(project_dir, dockerfile_text)
        + check_test_import(dockerfile_text, dockerfile_path=dockerfile_path)
    )
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
