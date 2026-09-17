"""Gate « parité runtime » (TF-1042) : oracle exécutable de la douzième discipline.

Recette DOUBLE SENS, au sens strict du lot : un projet PARITAIRE (CI et image sur la même
version, manifeste de test couvrant le runtime, import rejoué dans l'image) passe ; le MÊME
projet avec sa chaîne CI en 3.12 et son image en 3.11 (le défaut mesuré chez Produit-11 le
11/09/2026) est refusé. Un projet sans Dockerfile n'est pas conteneurisé : SANS_OBJET, jamais
un échec fabriqué faute de matière à juger.
"""

from __future__ import annotations

from pathlib import Path

from conductor.gates.runtime_parity_gate import main, run_runtime_parity_gate

_DOCKERFILE_PARITAIRE = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -c "import flask"
CMD ["python", "app.py"]
"""

_DOCKERFILE_SANS_IMPORT = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
"""

_WORKFLOW_GH_311 = """name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-dev.txt
      - run: pytest
"""

_WORKFLOW_GH_312 = """name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-dev.txt
      - run: pytest
"""

# TF-1042 : le défaut fondateur porte sur QUATRE tâches UsePythonVersion Azure Pipelines.
_AZURE_312_QUATRE_TACHES = """trigger:
- main
pool:
  vmImage: ubuntu-latest
steps:
- task: UsePythonVersion@0
  displayName: 'Python API'
  inputs:
    versionSpec: '3.12'
- task: UsePythonVersion@0
  displayName: 'Python worker'
  inputs:
    versionSpec: '3.12'
- task: UsePythonVersion@0
  displayName: 'Python lint'
  inputs:
    versionSpec: '3.12'
- task: UsePythonVersion@0
  displayName: 'Python integration'
  inputs:
    versionSpec: '3.12'
- script: pip install -r requirements-dev.txt
- script: pytest
"""

_RUNTIME_REQS = "flask==2.3.0\n"
_TEST_REQS_COMPLET = "flask==2.3.0\npytest==8.0.0\n"
_TEST_REQS_INCOMPLET = "pytest==8.0.0\n"


def _projet(
    tmp_path: Path,
    *,
    dockerfile: str | None = _DOCKERFILE_PARITAIRE,
    workflow: str | None = _WORKFLOW_GH_311,
    azure: str | None = None,
    runtime_reqs: str | None = _RUNTIME_REQS,
    test_reqs: str | None = _TEST_REQS_COMPLET,
    test_reqs_name: str = "requirements-dev.txt",
) -> Path:
    """Un projet instancié minimal : Dockerfile + chaîne CI + manifestes runtime/test."""
    racine = tmp_path / "projet"
    racine.mkdir()
    if dockerfile is not None:
        (racine / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    if workflow is not None:
        wf_dir = racine / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(workflow, encoding="utf-8")
    if azure is not None:
        (racine / "azure-pipelines.yml").write_text(azure, encoding="utf-8")
    if runtime_reqs is not None:
        (racine / "requirements.txt").write_text(runtime_reqs, encoding="utf-8")
    if test_reqs is not None:
        (racine / test_reqs_name).write_text(test_reqs, encoding="utf-8")
    return racine


# --- Recette double sens (interprète) ------------------------------------------


def test_sens_vert_projet_paritaire_passe(tmp_path: Path) -> None:
    """Fixture VERTE : CI et image sur la même version, manifeste couvert, import rejoué."""
    racine = _projet(tmp_path)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is True
    assert verdict.findings == []


def test_sens_rouge_disparite_interpreteur_azure_est_refusee(tmp_path: Path) -> None:
    """Fixture ROUGE : le défaut fondateur — CI en 3.12 (Azure, quatre tâches), image en 3.11."""
    racine = _projet(tmp_path, workflow=None, azure=_AZURE_312_QUATRE_TACHES)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is False
    disparites = [f for f in verdict.findings if f["kind"] == "interpreteur-disparite"]
    # quatre tâches UsePythonVersion déclarées, quatre constats localisés — jamais un total
    # anonyme (c'est le nombre réel mesuré chez Produit-11, TF-1042).
    assert len(disparites) == 4
    assert all(f["issue"].startswith("CI déclare Python 3.12") for f in disparites)
    assert len({f["ligne"] for f in disparites}) == 4


def test_sens_rouge_disparite_interpreteur_github_actions_est_refusee(tmp_path: Path) -> None:
    """Même défaut, déclaré côté GitHub Actions plutôt qu'Azure Pipelines."""
    racine = _projet(tmp_path, workflow=_WORKFLOW_GH_312)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is False
    disparites = [f for f in verdict.findings if f["kind"] == "interpreteur-disparite"]
    assert len(disparites) == 1
    assert "3.12" in disparites[0]["issue"] and "3.11" in disparites[0]["issue"]


def test_double_sens_par_le_cli_sur_le_meme_projet(tmp_path: Path) -> None:
    """Le double sens joué comme la recette du gabarit le joue : exit 1, correctif, exit 0."""
    racine = _projet(tmp_path, workflow=_WORKFLOW_GH_312)
    assert main([str(racine)]) == 1
    (racine / ".github" / "workflows" / "ci.yml").write_text(_WORKFLOW_GH_311, encoding="utf-8")
    assert main([str(racine)]) == 0


# --- Recette double sens (manifeste de test) ------------------------------------


def test_manifeste_test_incomplet_est_un_constat(tmp_path: Path) -> None:
    """Fixture ROUGE : le paquet runtime 'flask' n'est jamais installé par la porte de tests."""
    racine = _projet(tmp_path, test_reqs=_TEST_REQS_INCOMPLET)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is False
    constats = [f for f in verdict.findings if f["kind"] == "manifeste-test-incomplet"]
    assert len(constats) == 1
    assert "flask" in constats[0]["issue"]


def test_manifeste_test_absent_est_un_constat(tmp_path: Path) -> None:
    """Fixture ROUGE : aucun manifeste de test connu — le runtime n'est jamais exercé."""
    racine = _projet(tmp_path, test_reqs=None)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is False
    assert [f["kind"] for f in verdict.findings if "kind" in f] == ["manifeste-test-absent"]


# --- Recette double sens (test d'import) -----------------------------------------


def test_import_absent_est_un_constat(tmp_path: Path) -> None:
    """Fixture ROUGE : l'image finale ne rejoue aucun import Python."""
    racine = _projet(tmp_path, dockerfile=_DOCKERFILE_SANS_IMPORT)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is False
    assert [f["kind"] for f in verdict.findings if "kind" in f] == ["test-import-absent"]


# --- Do-no-harm : ce que le gate refuse de juger, il le DIT ----------------------


def test_projet_sans_dockerfile_est_sans_objet(tmp_path: Path) -> None:
    """P-06 : pas de Dockerfile → non conteneurisé, SKIP tracé (SANS_OBJET), jamais un échec."""
    racine = _projet(tmp_path, dockerfile=None)
    verdict = run_runtime_parity_gate(racine)
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_arborescence_absente_est_skip_trace(tmp_path: Path) -> None:
    verdict = run_runtime_parity_gate(tmp_path / "absent")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_image_de_base_non_officielle_hors_perimetre(tmp_path: Path) -> None:
    """Une image dérivée sans 'FROM python:' littéral : hors périmètre v0 pour le sous-contrôle
    1 — les sous-contrôles 2 et 3 restent indépendants et jugent ce qu'ils voient par ailleurs."""
    dockerfile = 'FROM mon-registre/python-durci:latest\nRUN python -c "import flask"\nCMD []\n'
    racine = _projet(tmp_path, dockerfile=dockerfile, runtime_reqs=None, test_reqs=None)
    verdict = run_runtime_parity_gate(racine)
    disparites = [f for f in verdict.findings if f.get("kind") == "interpreteur-disparite"]
    assert disparites == []
    assert verdict.passed is True


def test_aucune_version_ci_declaree_est_skip_trace(tmp_path: Path) -> None:
    """Chaîne CI sans version Python déclarée : rien à comparer, SKIP tracé sur ce sous-contrôle."""
    racine = _projet(
        tmp_path,
        workflow="name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: pytest\n",
    )
    verdict = run_runtime_parity_gate(racine)
    disparites = [f for f in verdict.findings if f.get("kind") == "interpreteur-disparite"]
    assert disparites == []


def test_dockerfile_sans_reference_pip_r_hors_perimetre(tmp_path: Path) -> None:
    """Dépendances installées autrement qu'un `-r <fichier>.txt` littéral : hors périmètre v0."""
    dockerfile = (
        "FROM python:3.11-slim\nRUN pip install flask\nRUN python -c \"import flask\"\nCMD []\n"
    )
    racine = _projet(tmp_path, dockerfile=dockerfile, runtime_reqs=None, test_reqs=None)
    verdict = run_runtime_parity_gate(racine)
    manifeste = [f for f in verdict.findings if f.get("kind", "").startswith("manifeste-test")]
    assert manifeste == []


def test_cli_usage_rend_2(tmp_path: Path) -> None:
    assert main([]) == 2
    assert main([str(tmp_path), "de trop"]) == 2
