"""Gate anti-patterns IA (TF-0103.3) : imports fantômes, secrets en dur, routes sans auth,
outil de qualité déclaré et jamais câblé (TF-1041)."""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pytest

from conductor.gates.ai_antipatterns_gate import (
    _chain_text,
    _dep_name,
    _find_repo_root,
    _import_names_for_dependency,
    _package_json_quality_scripts,
    _pre_commit_hook_ids,
    _pyproject_linters,
    _workflow_files,
    check_archiving_step_continue_on_error,
    check_declared_tools_not_wired,
    check_event_wait_after_action,
    check_hardcoded_secrets,
    check_missing_dependencies,
    check_routes_without_auth,
    main,
    manifest_import_names,
    run_ai_antipatterns_gate,
)
from tests._locale_ascii import evaluer_sous_locale_ascii

_PYPROJECT = """
[project]
name = "demo"
dependencies = ["pydantic>=2.7", "pyyaml>=6.0", "types-pyyaml>=6.0"]

[dependency-groups]
dev = ["pytest>=8.2", {include-group = "lint"}]
"""


def _write_pyproject(tmp_path: Path) -> Path:
    p = tmp_path / "pyproject.toml"
    p.write_text(_PYPROJECT, encoding="utf-8")
    return p


# --- manifest_import_names ----------------------------------------------------


def test_manifest_import_names_resout_alias_et_ignore_stubs(tmp_path: Path) -> None:
    pyproject = _write_pyproject(tmp_path)
    names = manifest_import_names(pyproject)
    assert "pydantic" in names
    assert "yaml" in names  # alias pyyaml -> yaml
    assert "pyyaml" not in names  # jamais le nom de distribution brut
    assert "types_pyyaml" not in names and "types-pyyaml" not in names  # stub : pas d'import


# --- _dep_name (TF-0120 : lacune mutation — specs URL/git+ jamais testées) ------


def test_dep_name_ignore_vide_et_commentaire() -> None:
    """Fixture rouge : chaîne vide/blanche ou commentaire → aucun nom (pas une dépendance)."""
    assert _dep_name("") is None
    assert _dep_name("   ") is None
    assert _dep_name("# un commentaire") is None


def test_dep_name_ignore_specs_url_et_git() -> None:
    """Fixture rouge réelle : une spec par URL (nommée ou non, avec ou sans préfixe `git+`)
    ne doit jamais être lue comme un nom de paquet — sinon un fragment d'URL (« https »,
    « git ») polluerait silencieusement le jeu de noms d'imports autorisés."""
    assert _dep_name("https://example.com/foo.whl") is None
    assert _dep_name("pkg @ https://example.com/pkg.whl") is None
    assert _dep_name("git+git@github.com:user/repo.git") is None


def test_dep_name_extrait_le_nom_normal() -> None:
    """Fixture verte : une spec PEP 508 standard extrait bien le nom, marqueurs ignorés."""
    assert _dep_name("  requests>=2.31  ") == "requests"


# --- _import_names_for_dependency (TF-0120 : suffixe -stubs et normalisation tiret) --


def test_import_names_for_dependency_stub_sans_prefixe_types() -> None:
    """Fixture rouge réelle : un paquet de stubs qui ne commence pas par 'types-' (suffixe
    '-stubs' seul, ex. distributions tierces) est aussi un stub — aucun import réel."""
    assert _import_names_for_dependency("foo-stubs") == set()


def test_import_names_for_dependency_normalise_le_tiret() -> None:
    """Fixture rouge réelle : le tiret du nom de distribution devient un underscore dans le
    nom de module importé (convention PyPI)."""
    assert _import_names_for_dependency("my-package") == {"my_package"}


_PYPROJECT_TROIS_SOURCES = """
[project]
name = "demo"
dependencies = ["pydantic>=2.7"]

[project.optional-dependencies]
extra = ["httpx>=0.27"]

[dependency-groups]
dev = ["pytest>=8.2", {include-group = "lint"}]
"""


def test_manifest_import_names_couvre_les_trois_sources(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-0120) : `dependencies` + `dependency-groups` +
    `optional-dependencies` doivent TOUTES contribuer au jeu de noms — une régression sur
    l'une des trois clés (mauvaise clé, mauvais défaut, `=` au lieu de `+=`) fait disparaître
    silencieusement une partie de la couverture sans qu'aucun test existant ne s'en aperçoive
    (le fixture historique ne testait que `dependencies`)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(_PYPROJECT_TROIS_SOURCES, encoding="utf-8")
    names = manifest_import_names(pyproject)
    assert "pydantic" in names  # [project.dependencies]
    assert "httpx" in names  # [project.optional-dependencies]
    assert "pytest" in names  # [dependency-groups]


def test_manifest_import_names_sans_table_project(tmp_path: Path) -> None:
    """Fixture rouge réelle : un pyproject.toml sans table [project] (TOML valide, cas
    dégénéré) ne doit pas planter — `data.get("project", {})` doit produire un dict vide,
    jamais None (sinon `.get()` sur None lève)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[build-system]\nrequires = ["hatchling"]\n', encoding="utf-8")
    assert manifest_import_names(pyproject) == set()


def test_manifest_import_names_sans_cle_dependencies(tmp_path: Path) -> None:
    """Fixture rouge réelle : un pyproject qui ne déclare aucune dépendance directe
    (seulement des dependency-groups, cas plausible pour un paquet d'outillage) ne doit pas
    planter sur le défaut de `project.get("dependencies", ...)`."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\n\n[dependency-groups]\ndev = ["pytest>=8.2"]\n',
        encoding="utf-8",
    )
    assert manifest_import_names(pyproject) == {"pytest"}


# --- 1. imports fantômes -------------------------------------------------------


def test_import_declare_passe(tmp_path: Path) -> None:
    """Fixture verte : stdlib + dépendance déclarée → aucun finding."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text(
        "from __future__ import annotations\nimport os\nimport pydantic\n", encoding="utf-8"
    )
    assert check_missing_dependencies(src, pyproject) == []


def test_import_fantome_echoue(tmp_path: Path) -> None:
    """Fixture rouge : import ni stdlib ni manifeste ni local → import fantôme."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import requests\n", encoding="utf-8")
    findings = check_missing_dependencies(src, pyproject)
    assert len(findings) == 1
    assert findings[0]["kind"] == "import-fantome"
    assert "requests" in findings[0]["issue"]


def test_import_local_hors_manifeste_passe(tmp_path: Path) -> None:
    """Un import du paquet local (source_dir lui-même) n'est pas un import fantôme."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import app.utils\n", encoding="utf-8")
    assert check_missing_dependencies(src, pyproject) == []


def test_missing_dependencies_exclusion_ne_bloque_pas_la_suite(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-0120) : un fichier sous un répertoire exclu (`tests/`) ne
    produit aucun finding, ET son exclusion ne doit pas interrompre l'analyse du reste de
    l'arborescence (rglob trie `tests/` avant `zz_main.py`)."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    excluded_dir = src / "tests"
    excluded_dir.mkdir()
    (excluded_dir / "a_helper.py").write_text("import requests\n", encoding="utf-8")
    (src / "zz_main.py").write_text("import requests\n", encoding="utf-8")
    findings = check_missing_dependencies(src, pyproject)
    assert findings == [
        {
            "file": str(src / "zz_main.py"),
            "kind": "import-fantome",
            "issue": "import 'requests' absent du manifeste de dépendances",
        }
    ]


def test_missing_dependencies_erreur_syntaxe_ne_bloque_pas_la_suite(tmp_path: Path) -> None:
    """Fixture rouge réelle : un fichier syntaxiquement invalide (hors périmètre — ruff/mypy
    le couvrent) ne doit pas arrêter l'analyse des fichiers suivants."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "a_broken.py").write_text("def broken(:\n", encoding="utf-8")
    (src / "zz_main.py").write_text("import requests\n", encoding="utf-8")
    findings = check_missing_dependencies(src, pyproject)
    assert len(findings) == 1
    assert findings[0]["file"] == str(src / "zz_main.py")


def test_missing_dependencies_import_relatif_ignore_puis_suite_analysee(tmp_path: Path) -> None:
    """Fixture rouge réelle : un import relatif ignoré (`from . import x`) ne doit pas
    arrêter l'analyse des imports suivants du même fichier."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("from . import helper\nimport requests\n", encoding="utf-8")
    findings = check_missing_dependencies(src, pyproject)
    assert len(findings) == 1
    assert "requests" in findings[0]["issue"]


def test_missing_dependencies_import_from_point_capture_le_module_racine(
    tmp_path: Path,
) -> None:
    """Fixture rouge réelle : `from requests.auth import X` doit être rattaché au module
    racine `requests`, pas au chemin complet `requests.auth` — sinon un import fantôme sur un
    sous-module ne serait jamais détecté sous son vrai nom de paquet."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text(
        "from requests.auth import HTTPBasicAuth\n", encoding="utf-8"
    )
    findings = check_missing_dependencies(src, pyproject)
    assert len(findings) == 1
    assert findings[0]["issue"] == "import 'requests' absent du manifeste de dépendances"


def test_missing_dependencies_ignore_octets_invalides(tmp_path: Path) -> None:
    """Fixture rouge réelle : `errors="ignore"` doit avaler un octet non-UTF-8 égaré dans un
    fichier source plutôt que de faire planter tout le scan sur un seul fichier corrompu."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_bytes(b"import requests  # \xff\xfe\n")
    findings = check_missing_dependencies(src, pyproject)
    assert len(findings) == 1
    assert findings[0]["issue"] == "import 'requests' absent du manifeste de dépendances"


# --- 2. secrets en dur ----------------------------------------------------------


def test_secret_via_environ_passe(tmp_path: Path) -> None:
    """Fixture verte : la valeur vient de l'environnement, aucun littéral en dur."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_text('API_KEY = os.environ["API_KEY"]\n', encoding="utf-8")
    assert check_hardcoded_secrets(src) == []


def test_secret_placeholder_passe(tmp_path: Path) -> None:
    """Un placeholder documenté (changeme, exemple…) n'est pas un vrai secret."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_text('SECRET_KEY = "changeme-in-prod"\n', encoding="utf-8")
    assert check_hardcoded_secrets(src) == []


def test_secret_en_dur_echoue(tmp_path: Path) -> None:
    """Fixture rouge : littéral non-placeholder affecté à une variable sensible."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_text('PASSWORD = "hunter2plus9"\n', encoding="utf-8")
    findings = check_hardcoded_secrets(src)
    assert len(findings) == 1
    assert findings[0]["kind"] == "secret-en-dur"


def test_cle_connue_en_dur_echoue(tmp_path: Path) -> None:
    """Fixture rouge : clé au format connu (AWS) en clair dans le source."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_text(
        'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n', encoding="utf-8"
    )
    findings = check_hardcoded_secrets(src)
    assert findings == [
        {"file": str(src / "config.py"), "kind": "secret-en-dur", "issue": "clé connue en clair"}
    ]


def test_hardcoded_secrets_exclusion_ne_bloque_pas_la_suite(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-0120) : un fichier sous un répertoire exclu (`tests/`) ne
    produit aucun finding, ET son exclusion ne doit pas interrompre l'analyse du reste de
    l'arborescence (rglob trie `tests/` avant `zz_main.py`)."""
    src = tmp_path / "app"
    src.mkdir()
    excluded_dir = src / "tests"
    excluded_dir.mkdir()
    (excluded_dir / "a_helper.py").write_text('PASSWORD = "hunter2plus9"\n', encoding="utf-8")
    (src / "zz_main.py").write_text('PASSWORD = "hunter2plus9"\n', encoding="utf-8")
    findings = check_hardcoded_secrets(src)
    assert findings == [
        {
            "file": str(src / "zz_main.py"),
            "kind": "secret-en-dur",
            "issue": "valeur en dur affectée à 'PASSWORD'",
        }
    ]


def test_hardcoded_secrets_cle_connue_puis_fichier_suivant_analyse(tmp_path: Path) -> None:
    """Fixture rouge réelle : après avoir trouvé une clé connue dans un fichier, le scan
    doit continuer avec les fichiers suivants (pas les arrêter)."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "a_known.py").write_text('AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n', encoding="utf-8")
    (src / "zz_other.py").write_text('PASSWORD = "hunter2plus9"\n', encoding="utf-8")
    findings = check_hardcoded_secrets(src)
    files_found = {f["file"] for f in findings}
    assert files_found == {str(src / "a_known.py"), str(src / "zz_other.py")}


def test_hardcoded_secrets_valeur_prefixee_os_ou_settings_passe(tmp_path: Path) -> None:
    """Fixture verte : une valeur qui référence dynamiquement `os.`/`settings.` n'est pas un
    vrai secret en dur — les deux préfixes doivent être reconnus, pas seulement l'un des deux."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_text(
        'API_KEY = "os.getenv-fallback-marker"\n'
        'SECRET_TOKEN = "settings.SECRET_TOKEN_REF"\n',
        encoding="utf-8",
    )
    assert check_hardcoded_secrets(src) == []


def test_hardcoded_secrets_placeholder_ignore_puis_secret_reel_detecte(tmp_path: Path) -> None:
    """Fixture rouge réelle : sauter un placeholder (`continue`) ne doit pas arrêter
    l'analyse du reste du même fichier — le vrai secret qui suit doit être détecté."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_text(
        'SECRET_KEY = "changeme-in-prod"\nPASSWORD = "hunter2plus9"\n', encoding="utf-8"
    )
    findings = check_hardcoded_secrets(src)
    assert len(findings) == 1
    assert findings[0]["issue"] == "valeur en dur affectée à 'PASSWORD'"


def test_hardcoded_secrets_ignore_octets_invalides(tmp_path: Path) -> None:
    """Fixture rouge réelle : `errors="ignore"` doit avaler un octet non-UTF-8 égaré plutôt
    que de faire planter le scan sur un fichier corrompu."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "config.py").write_bytes(b'PASSWORD = "hunter2plus9"  # \xff\xfe\n')
    findings = check_hardcoded_secrets(src)
    assert len(findings) == 1
    assert findings[0]["issue"] == "valeur en dur affectée à 'PASSWORD'"


# --- 3. routes sans autorisation -------------------------------------------------


def test_route_avec_depends_auth_passe(tmp_path: Path) -> None:
    """Fixture verte : la route dépend d'un provider d'authentification."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "routes.py").write_text(
        "@app.get('/me')\n"
        "def me(user = Depends(get_current_user)):\n"
        "    return user\n",
        encoding="utf-8",
    )
    assert check_routes_without_auth(src) == []


def test_route_publique_marquee_passe(tmp_path: Path) -> None:
    """Fixture verte : route délibérément publique, marquée explicitement."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "routes.py").write_text(
        "@app.get('/health')  # route-publique-ok\n"
        "def health():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    assert check_routes_without_auth(src) == []


def test_route_sans_auth_echoue(tmp_path: Path) -> None:
    """Fixture rouge : route mutante sans dépendance d'auth ni marqueur public."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "routes.py").write_text(
        "@app.delete('/admin/users/{id}')\ndef delete_user(id: int):\n    ...\n",
        encoding="utf-8",
    )
    findings = check_routes_without_auth(src)
    assert findings == [
        {
            "file": str(src / "routes.py"),
            "kind": "route-sans-auth",
            "issue": "route '@app.delete(' sans dépendance d'auth ni marqueur public",
        }
    ]


def test_routes_exclusion_ne_bloque_pas_la_suite(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-0120) : un fichier sous un répertoire exclu (`tests/`) ne
    produit aucun finding, ET son exclusion ne doit pas interrompre l'analyse du reste de
    l'arborescence (rglob trie `tests/` avant `zz_routes.py`)."""
    src = tmp_path / "app"
    src.mkdir()
    excluded_dir = src / "tests"
    excluded_dir.mkdir()
    (excluded_dir / "a_helper.py").write_text(
        "@app.delete('/x')\ndef x(): ...\n", encoding="utf-8"
    )
    (src / "zz_routes.py").write_text(
        "@app.delete('/admin/users/{id}')\ndef delete_user(id: int):\n    ...\n",
        encoding="utf-8",
    )
    findings = check_routes_without_auth(src)
    assert findings == [
        {
            "file": str(src / "zz_routes.py"),
            "kind": "route-sans-auth",
            "issue": "route '@app.delete(' sans dépendance d'auth ni marqueur public",
        }
    ]


def test_routes_avec_auth_puis_route_suivante_sans_auth_detectee(tmp_path: Path) -> None:
    """Fixture rouge réelle : sauter une route déjà protégée (`continue`) ne doit pas
    arrêter l'analyse des routes suivantes dans le même fichier."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "routes.py").write_text(
        "@app.get('/me')\n"
        "def me(user = Depends(get_current_user)):\n"
        "    return user\n"
        "@app.delete('/admin/users/{id}')\n"
        "def delete_user(id: int):\n"
        "    ...\n",
        encoding="utf-8",
    )
    findings = check_routes_without_auth(src)
    assert len(findings) == 1
    assert findings[0]["issue"] == "route '@app.delete(' sans dépendance d'auth ni marqueur public"


def test_routes_ignore_octets_invalides(tmp_path: Path) -> None:
    """Fixture rouge réelle : `errors="ignore"` doit avaler un octet non-UTF-8 égaré plutôt
    que de faire planter le scan sur un fichier corrompu."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "routes.py").write_bytes(
        b"@app.delete('/admin')  # \xff\xfe\ndef delete_it(): ...\n"
    )
    findings = check_routes_without_auth(src)
    assert len(findings) == 1


# --- 5. Étape d'archivage sous continueOnError (TF-1112) ------------------------


def test_archivage_azure_sous_continue_on_error_echoue(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-1112, mesure Produit-11) : PublishBuildArtifacts protégé par
    continueOnError: true — l'étape reste verte quel que soit le sort du chemin publié."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "azure-pipelines.yml").write_text(
        "steps:\n"
        "  - script: npx playwright test\n"
        "  - task: PublishBuildArtifacts@1\n"
        "    continueOnError: true\n"
        "    inputs:\n"
        "      pathToPublish: frontend/tests/e2e/resultats.json\n"
        "      artifactName: resultats\n",
        encoding="utf-8",
    )
    findings = check_archiving_step_continue_on_error(tmp_path)
    assert findings == [
        {
            "file": str(tmp_path / "azure-pipelines.yml"),
            "kind": "archivage-non-verifiable",
            "issue": "étape d'archivage sous continueOnError/continue-on-error: true — un "
            "chemin jamais produit reste vert, l'échec qu'elle devait archiver ne laisse "
            "aucune trace",
        }
    ]


def test_archivage_azure_sans_continue_on_error_passe(tmp_path: Path) -> None:
    """Fixture verte : même étape d'archivage, sans neutralisation — un échec de publication
    reste un échec de pipeline."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "azure-pipelines.yml").write_text(
        "steps:\n"
        "  - task: PublishBuildArtifacts@1\n"
        "    inputs:\n"
        "      pathToPublish: frontend/tests/e2e/resultats.json\n"
        "      artifactName: resultats\n",
        encoding="utf-8",
    )
    assert check_archiving_step_continue_on_error(tmp_path) == []


def test_archivage_github_actions_sous_continue_on_error_echoue(tmp_path: Path) -> None:
    """Fixture rouge : même défaut, dialecte GitHub Actions (upload-artifact /
    continue-on-error)."""
    (tmp_path / ".git").mkdir()
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - uses: actions/upload-artifact@v4\n"
        "        continue-on-error: true\n"
        "        with:\n"
        "          path: resultats.json\n",
        encoding="utf-8",
    )
    findings = check_archiving_step_continue_on_error(tmp_path)
    assert len(findings) == 1
    assert findings[0]["file"] == str(workflows / "ci.yml")
    assert findings[0]["kind"] == "archivage-non-verifiable"


def test_archivage_hors_fenetre_ne_declenche_pas(tmp_path: Path) -> None:
    """Fixture verte réelle : l'étape d'archivage elle-même n'est PAS neutralisée ; un
    ``continueOnError: true`` porté par une étape SANS rapport, bien plus loin dans le
    fichier, ne doit pas lui être imputé à tort — la fenêtre est bornée autour du
    déclencheur d'archivage, pas du fichier entier."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "azure-pipelines.yml").write_text(
        "steps:\n"
        "  - task: PublishBuildArtifacts@1\n"
        "    inputs:\n"
        "      pathToPublish: resultats.json\n"
        + ("\n" * 600)
        + "  - script: npm run lint\n"
        "    continueOnError: true\n",
        encoding="utf-8",
    )
    assert check_archiving_step_continue_on_error(tmp_path) == []


def test_run_gate_integre_le_controle_archivage(tmp_path: Path) -> None:
    """Intégration : ``run_ai_antipatterns_gate`` remonte le 5e contrôle (TF-1112) même sans
    pyproject.toml — le défaut est indépendant du langage du produit."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "azure-pipelines.yml").write_text(
        "steps:\n"
        "  - task: PublishBuildArtifacts@1\n"
        "    continueOnError: true\n"
        "    inputs:\n"
        "      pathToPublish: resultats.json\n",
        encoding="utf-8",
    )
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("x = 1\n", encoding="utf-8")
    verdict = run_ai_antipatterns_gate(src, tmp_path / "absent.toml")
    assert verdict.passed is False
    kinds = {f["kind"] for f in verdict.findings if "skipped" not in f}
    assert "archivage-non-verifiable" in kinds


def _racine_git(depart: Path) -> Path | None:
    """Premier dossier, en remontant depuis ``depart``, qui porte ``.git`` (TF-2052)."""
    return next((d for d in (depart, *depart.parents) if (d / ".git").exists()), None)


def test_racine_git_se_trouve_a_plusieurs_niveaux(tmp_path: Path) -> None:
    """TF-2052, double sens : l'ancien contrôle (``.git`` à la racine ou au parent seulement)
    échoue depuis ``mutants/`` — trois niveaux sous le ``.git`` ; la remontée le trouve."""
    (tmp_path / "depot" / ".git").mkdir(parents=True)
    profond = tmp_path / "depot" / "produit" / "mutants"
    profond.mkdir(parents=True)
    ancien = (profond / ".git").exists() or (profond.parent / ".git").exists()
    assert ancien is False  # fixture rouge : ce que le test d'origine ne voyait pas
    assert _racine_git(profond) == tmp_path / "depot"  # remède joué : trouvé
    assert _racine_git(tmp_path / "depot") == tmp_path / "depot"  # le .git lui-même, niveau 0


def test_archivage_sans_faux_positif_sur_ce_depot(tmp_path: Path) -> None:
    """Preuve d'absence de faux positif EXIGÉE par le contrat de campagne : rejouée ici sur le
    dépôt réel (``.github/workflows/double-gate.yml``), qui n'archive rien sous
    continueOnError — la règle neuve ne doit rien y trouver."""
    repo_root = Path(__file__).resolve().parents[1]
    # TF-2052 : sous mutmut, les tests jouent depuis ``mutants/`` (un cran plus bas que le
    # produit) — on remonte donc jusqu'au ``.git`` au lieu de ne regarder que deux niveaux, et
    # on saute hors d'un dépôt (archive sans ``.git``) : la preuve porte sur le dépôt réel.
    if _racine_git(repo_root) is None:
        pytest.skip("hors d'un dépôt git : aucune chaîne CI réelle à juger")
    findings = check_archiving_step_continue_on_error(repo_root)
    assert findings == []


# --- 6. Attente d'événement posée après l'action (TF-1111) ----------------------


def test_waitfor_apres_click_echoue(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-1111, mesure Produit-11) : ``waitForResponse`` posé APRÈS
    ``click`` — reproduction fidèle de ``09-import-en-masse.spec.ts``."""
    e2e = tmp_path / "frontend" / "tests" / "e2e"
    e2e.mkdir(parents=True)
    (e2e / "09-import-en-masse.spec.ts").write_text(
        "test('import invalide', async ({ page }) => {\n"
        "  await page.click('#importer');\n"
        "  await page.waitForResponse(r => r.url().includes('/import'));\n"
        "});\n",
        encoding="utf-8",
    )
    findings = check_event_wait_after_action(tmp_path)
    assert len(findings) == 1
    assert findings[0]["file"] == str(e2e / "09-import-en-masse.spec.ts")
    assert findings[0]["kind"] == "attente-posee-apres-action"
    assert "waitForResponse" in findings[0]["issue"]


def test_waitfor_avant_click_passe(tmp_path: Path) -> None:
    """Fixture verte : la promesse d'attente est capturée AVANT l'action, puis attendue —
    même fichier corrigé, aucun ``await page.waitFor*`` ne suit textuellement une action."""
    e2e = tmp_path / "frontend" / "tests" / "e2e"
    e2e.mkdir(parents=True)
    (e2e / "09-import-en-masse.spec.ts").write_text(
        "test('import invalide', async ({ page }) => {\n"
        "  const reponse = page.waitForResponse(r => r.url().includes('/import'));\n"
        "  await page.click('#importer');\n"
        "  await reponse;\n"
        "});\n",
        encoding="utf-8",
    )
    assert check_event_wait_after_action(tmp_path) == []


def test_waitfor_sans_rapport_avec_l_action_passe(tmp_path: Path) -> None:
    """Fixture verte réelle : un ``waitFor*`` isolé, sans action précédente, n'est jamais un
    faux positif — la règle exige la SUCCESSION action puis attente, pas la seule présence."""
    e2e = tmp_path / "frontend" / "tests" / "e2e"
    e2e.mkdir(parents=True)
    (e2e / "attente-seule.spec.ts").write_text(
        "test('chargement', async ({ page }) => {\n"
        "  await page.goto('/');\n"
        "  await page.waitForSelector('#pret');\n"
        "});\n",
        encoding="utf-8",
    )
    assert check_event_wait_after_action(tmp_path) == []


def test_run_gate_integre_le_controle_attente(tmp_path: Path) -> None:
    """Intégration : ``run_ai_antipatterns_gate`` remonte le 6e contrôle (TF-1111)."""
    src = tmp_path / "app"
    e2e = src / "tests" / "e2e"
    e2e.mkdir(parents=True)
    (e2e / "x.spec.ts").write_text(
        "await page.click('#go');\nawait page.waitForNavigation();\n", encoding="utf-8"
    )
    (src / "main.py").write_text("x = 1\n", encoding="utf-8")
    verdict = run_ai_antipatterns_gate(src, tmp_path / "absent.toml")
    assert verdict.passed is False
    kinds = {f["kind"] for f in verdict.findings if "skipped" not in f}
    assert "attente-posee-apres-action" in kinds


def test_attente_sans_faux_positif_sur_ce_depot() -> None:
    """Preuve d'absence de faux positif EXIGÉE par le contrat de campagne : ce dépôt ne porte
    aucune spécification Playwright — SKIP net, jamais un faux positif par construction."""
    repo_root = Path(__file__).resolve().parents[1]
    assert list(repo_root.rglob("*.spec.ts")) == []
    assert check_event_wait_after_action(repo_root) == []


# --- Agrégation / P-06 / CLI -----------------------------------------------------


def test_arborescence_absente_est_skip_trace(tmp_path: Path) -> None:
    verdict = run_ai_antipatterns_gate(tmp_path / "absent")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_pyproject_absent_est_skip_trace_sur_import(tmp_path: Path) -> None:
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import os\n", encoding="utf-8")
    verdict = run_ai_antipatterns_gate(src, tmp_path / "absent.toml")
    assert verdict.passed is True
    assert verdict.findings == [
        {"skipped": "pyproject.toml introuvable — imports fantômes non contrôlés"}
    ]


def test_run_gate_transmet_local_packages(tmp_path: Path) -> None:
    """Fixture rouge réelle (TF-0120) : `local_packages` doit être transmis tel quel à
    `check_missing_dependencies` — le perdre silencieusement (remplacé par None) ferait
    retomber sur le nom du dossier source et casserait l'autorisation explicite d'un paquet
    local nommé différemment."""
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "somesrc"
    src.mkdir()
    (src / "main.py").write_text("import mon_paquet_local\n", encoding="utf-8")
    verdict = run_ai_antipatterns_gate(src, pyproject, local_packages={"mon_paquet_local"})
    assert verdict.passed is True


def test_run_gate_log_ref_pointe_le_dossier_source(tmp_path: Path) -> None:
    """Fixture rouge réelle : `log_ref` doit référencer le dossier réellement analysé."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import os\n", encoding="utf-8")
    verdict = run_ai_antipatterns_gate(src, tmp_path / "absent.toml")
    assert verdict.log_ref == str(src)


def test_gate_agrege_les_trois_controles_et_echoue(tmp_path: Path) -> None:
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text(
        "import requests\n"
        'PASSWORD = "hunter2plus9"\n'
        "@app.get('/admin')\ndef admin():\n    ...\n",
        encoding="utf-8",
    )
    verdict = run_ai_antipatterns_gate(src, pyproject)
    kinds = {f["kind"] for f in verdict.findings}
    assert verdict.passed is False
    assert kinds == {"import-fantome", "secret-en-dur", "route-sans-auth"}


# --- 4. Outil de qualité déclaré, jamais câblé (TF-1041) ----------------------


def _write_chain(repo_root: Path, content: str) -> None:
    workflows = repo_root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(content, encoding="utf-8")


def test_find_repo_root_remonte_jusqu_au_marqueur_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "produit"
    nested.mkdir()
    assert _find_repo_root(nested) == tmp_path


def test_find_repo_root_sans_marqueur_rend_le_depart(tmp_path: Path) -> None:
    """Fixture rouge : aucun ``.git`` sur le chemin → le point de départ est rendu tel quel
    (do-no-harm), jamais une remontée jusqu'à la racine du disque."""
    isolated = tmp_path / "sans-git"
    isolated.mkdir()
    assert _find_repo_root(isolated) == isolated


def test_package_json_quality_scripts_filtre_lint_et_typecheck(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint .", "build": "tsc -b", "test": "vitest"}}),
        encoding="utf-8",
    )
    scripts = _package_json_quality_scripts(tmp_path)
    assert scripts == {"lint": "eslint ."}


def test_package_json_absent_rend_dict_vide(tmp_path: Path) -> None:
    assert _package_json_quality_scripts(tmp_path) == {}


def test_pyproject_linters_detecte_les_tables_declarees(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text("[tool.ruff]\nline-length = 100\n[tool.mypy]\nstrict = true\n", encoding="utf-8")
    assert _pyproject_linters(p) == ["ruff", "mypy"]


def test_pyproject_linters_sans_table_tool_rend_liste_vide(tmp_path: Path) -> None:
    p = _write_pyproject(tmp_path)
    assert _pyproject_linters(p) == []


def test_pre_commit_hook_ids_lit_les_id(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: local\n    hooks:\n      - id: ruff\n      - id: eslint\n",
        encoding="utf-8",
    )
    assert _pre_commit_hook_ids(tmp_path) == ["ruff", "eslint"]


def test_declared_tool_absent_de_la_chaine_echoue(tmp_path: Path) -> None:
    """Fixture rouge (TF-1041, mesure Produit-11) : un script de qualité déclaré et absent du
    fichier de chaîne est signalé — la déclaration seule ne prouve rien."""
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint ."}}), encoding="utf-8"
    )
    _write_chain(tmp_path, "jobs:\n  build:\n    steps:\n      - run: npm run build\n")
    pyproject = _write_pyproject(tmp_path)
    findings = check_declared_tools_not_wired(pyproject, repo_root=tmp_path)
    assert findings == [
        {
            "kind": "outil-non-cable",
            "issue": "script package.json 'lint' (eslint .) absent de la chaîne CI",
        }
    ]


def test_declared_tool_cable_dans_la_chaine_passe(tmp_path: Path) -> None:
    """Fixture verte : le même script, cette fois appelé par la chaîne, ne remonte rien."""
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint ."}}), encoding="utf-8"
    )
    _write_chain(tmp_path, "jobs:\n  code:\n    steps:\n      - run: npm run lint\n")
    pyproject = _write_pyproject(tmp_path)
    assert check_declared_tools_not_wired(pyproject, repo_root=tmp_path) == []


def test_declared_tool_neutralise_dans_la_chaine_echoue(tmp_path: Path) -> None:
    """Fixture rouge : le linter est cité mais sa ligne est neutralisée (``|| true``) — cité
    n'est pas câblé."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    _write_chain(tmp_path, "jobs:\n  code:\n    steps:\n      - run: uv run ruff check . || true\n")
    findings = check_declared_tools_not_wired(pyproject, repo_root=tmp_path)
    assert findings == [
        {
            "kind": "outil-non-cable",
            "issue": "linter pyproject.toml '[tool.ruff]' absent de la chaîne CI",
        }
    ]


def test_declared_pyproject_linter_cable_passe(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    _write_chain(tmp_path, "jobs:\n  code:\n    steps:\n      - run: uv run ruff check .\n")
    assert check_declared_tools_not_wired(pyproject, repo_root=tmp_path) == []


def test_declared_pre_commit_hook_absent_echoue(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: local\n    hooks:\n      - id: eslint\n", encoding="utf-8"
    )
    _write_chain(tmp_path, "jobs:\n  code:\n    steps:\n      - run: npm run build\n")
    pyproject = _write_pyproject(tmp_path)
    findings = check_declared_tools_not_wired(pyproject, repo_root=tmp_path)
    assert findings == [
        {
            "kind": "outil-non-cable",
            "issue": "hook .pre-commit-config.yaml 'eslint' absent de la chaîne CI",
        }
    ]


def test_declared_tools_sans_chaine_ni_declaration_ne_remonte_rien(tmp_path: Path) -> None:
    pyproject = _write_pyproject(tmp_path)
    assert check_declared_tools_not_wired(pyproject, repo_root=tmp_path) == []


def test_run_gate_integre_le_controle_socle(tmp_path: Path) -> None:
    """Intégration : ``run_ai_antipatterns_gate`` remonte bien le 4e contrôle (TF-1041) et le
    dépôt reste PASS quand tout est câblé."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("x = 1\n", encoding="utf-8")
    _write_chain(tmp_path, "jobs:\n  code:\n    steps:\n      - run: uv run ruff check .\n")
    verdict = run_ai_antipatterns_gate(src, pyproject)
    assert verdict.passed is True


def test_cli_main_pass_et_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import requests\n", encoding="utf-8")
    assert main([str(src), str(pyproject)]) == 1
    err = capsys.readouterr().err
    assert err == (
        "ai-antipatterns gate: FAIL (1 défaut(s))\n"
        f"  - [import-fantome] {src / 'main.py'} : "
        "import 'requests' absent du manifeste de dépendances\n"
    )
    (src / "main.py").write_text("import os\n", encoding="utf-8")
    assert main([str(src), str(pyproject)]) == 0
    assert capsys.readouterr().out == "ai-antipatterns gate: PASS\n"


def test_cli_nombre_arguments_invalide(capsys: pytest.CaptureFixture[str]) -> None:
    """Fixture rouge réelle (TF-0120) : ni 0 ni 3+ arguments n'est un usage valide — message
    d'usage exact sur stderr, code de sortie 2 (jamais un autre code)."""
    assert main([]) == 2
    err = capsys.readouterr().err
    assert err == (
        "usage: python -m conductor.gates.ai_antipatterns_gate <source_dir> "
        "[pyproject.toml]\n"
    )
    assert main(["a", "b", "c"]) == 2


def test_cli_un_seul_argument_utilise_le_pyproject_par_defaut(tmp_path: Path) -> None:
    """Fixture rouge réelle : sans second argument, le pyproject par défaut
    (`<source_dir>/../pyproject.toml`) déclarant la dépendance importée suffit à faire
    passer le gate sans le nommer explicitement."""
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import pydantic\n", encoding="utf-8")
    assert main([str(src)]) == 0


def test_cli_pyproject_par_defaut_utilise_le_bon_nom_de_fichier(tmp_path: Path) -> None:
    """Fixture rouge réelle : le nom du fichier par défaut est EXACTEMENT `pyproject.toml`
    — un dérivé qui ne trouve jamais le fichier réel ferait passer le contrôle des imports
    fantômes en SKIP silencieux plutôt qu'en échec attendu (le pyproject par défaut existe
    mais ne déclare pas `requests`)."""
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import requests\n", encoding="utf-8")
    assert main([str(src)]) == 1


def test_cli_argument_explicite_prime_sur_le_defaut(tmp_path: Path) -> None:
    """Fixture rouge réelle : quand un pyproject est nommé explicitement (2e argument), il
    doit être utilisé À LA PLACE du défaut — même si le défaut existe et déclare autre chose."""
    default_pyproject = tmp_path / "proj" / "pyproject.toml"
    default_pyproject.parent.mkdir()
    default_pyproject.write_text('[project]\nname = "x"\ndependencies = []\n', encoding="utf-8")
    src = tmp_path / "proj" / "app"
    src.mkdir()
    (src / "main.py").write_text("import pydantic\n", encoding="utf-8")
    explicit_pyproject = tmp_path / "explicit.toml"
    explicit_pyproject.write_text(_PYPROJECT, encoding="utf-8")
    assert main([str(src), str(explicit_pyproject)]) == 0  # pydantic déclaré côté explicite


def test_cli_argv_none_utilise_sys_argv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fixture rouge réelle : en usage réel (`python -m ...`), `argv=None` doit lire
    `sys.argv[1:]` (le nom du programme est en position 0) — jamais un autre décalage. Le
    défaut est déclaratif (un import fantôme) pour qu'un mauvais décalage — qui ferait
    dériver `source_dir` vers le pyproject lui-même, un simple fichier sans `.py` à
    scanner — bascule silencieusement le verdict en PASS au lieu du FAIL attendu."""
    pyproject = _write_pyproject(tmp_path)  # ne déclare pas 'requests'
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import requests\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["ai_antipatterns_gate", str(src), str(pyproject)])
    assert main() == 1


def test_cli_les_findings_skip_ne_comptent_pas_comme_defauts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fixture rouge réelle : un pyproject absent (finding `skipped`) ne doit ni compter
    dans le nombre de défauts affiché, ni apparaître dans le détail — seuls les vrais
    défauts (ici un secret en dur, détecté indépendamment du manifeste) sont listés."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text('PASSWORD = "hunter2plus9"\n', encoding="utf-8")
    assert main([str(src)]) == 1
    err = capsys.readouterr().err
    assert err == (
        "ai-antipatterns gate: FAIL (1 défaut(s))\n"
        f"  - [secret-en-dur] {src / 'main.py'} : valeur en dur affectée à 'PASSWORD'\n"
    )


# --- TF-2068 : survivants du rejeu mutmut du 03/11/2026 -------------------------------
#
# Chaque test ci-dessous tue un mutant vivant ; la correspondance est dans
# docs/mutation-equivalents.md. Les fixtures rouges sont les entrées que la suite ne
# fournissait pas : locale non UTF-8, octets invalides, dialectes de chaîne CI, motifs hors
# fenêtre.


def _json(chemin: Path) -> str:
    return json.dumps(str(chemin))


# Lecture en UTF-8 indépendante de la locale : le fils tourne en locale ASCII et les octets
# multi-octets y sont avalés (errors="ignore") ou refusés (strict) si ``encoding`` saute. Chaque
# test appelle aussi la fonction DANS le processus du test : mutmut ne relie un test à une
# fonction que par les appels qu'il observe dans son propre processus, et le fils lui est
# invisible. Le résultat du fils doit égaler celui du processus du test.


def test_manifest_lu_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text(
        '# dépendances déclarées\n[project]\nname = "demo"\ndependencies = ["pydantic>=2.7"]\n',
        encoding="utf-8",
    )
    local = sorted(manifest_import_names(p))
    assert local == ["pydantic"]
    assert evaluer_sous_locale_ascii(f"sorted(g.manifest_import_names(Path({_json(p)})))") == local


def test_imports_fantomes_lus_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import requésts\n", encoding="utf-8")
    pyproject = _write_pyproject(tmp_path)
    local = [f["issue"] for f in check_missing_dependencies(src, pyproject)]
    assert local == ["import 'requésts' absent du manifeste de dépendances"]
    assert evaluer_sous_locale_ascii(
        "[f['issue'] for f in "
        f"g.check_missing_dependencies(Path({_json(src)}), Path({_json(pyproject)}))]"
    ) == local


def test_secrets_lus_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text('secret_é = "motdepasse01"\n', encoding="utf-8")
    local = [f["issue"] for f in check_hardcoded_secrets(src)]
    assert local == ["valeur en dur affectée à 'secret_é'"]
    assert evaluer_sous_locale_ascii(
        f"[f['issue'] for f in g.check_hardcoded_secrets(Path({_json(src)}))]"
    ) == local


def test_routes_lues_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text('@appé.get("/x")\ndef f():\n    return 1\n', encoding="utf-8")
    local = [f["issue"] for f in check_routes_without_auth(src)]
    assert local == ["route '@appé.get(' sans dépendance d'auth ni marqueur public"]
    assert evaluer_sous_locale_ascii(
        f"[f['issue'] for f in g.check_routes_without_auth(Path({_json(src)}))]"
    ) == local


def test_package_json_lu_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint --format=é"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    local = _package_json_quality_scripts(tmp_path)
    assert local == {"lint": "eslint --format=é"}
    assert (
        evaluer_sous_locale_ascii(f"g._package_json_quality_scripts(Path({_json(tmp_path)}))")
        == local
    )


def test_pyproject_linters_lu_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text("# lecture à froid\n[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    local = _pyproject_linters(p)
    assert local == ["ruff"]
    assert evaluer_sous_locale_ascii(f"g._pyproject_linters(Path({_json(p)}))") == local


def test_pre_commit_lu_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: local\n    hooks:\n      - id: lintér\n", encoding="utf-8"
    )
    local = _pre_commit_hook_ids(tmp_path)
    assert local == ["lintér"]
    assert evaluer_sous_locale_ascii(f"g._pre_commit_hook_ids(Path({_json(tmp_path)}))") == local


def test_chaine_ci_lue_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: déploiement\n", encoding="utf-8")
    local = _chain_text(tmp_path)
    assert local == "name: déploiement\n"
    assert evaluer_sous_locale_ascii(f"g._chain_text(Path({_json(tmp_path)}))") == local


def test_archivage_lu_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    """Le motif ``continueOnError`` est à plus de 400 caractères de l'étape : hors fenêtre, donc
    aucun constat. Si la locale avale les 450 ``é`` du commentaire, le motif entre dans la
    fenêtre et un constat apparaît."""
    (tmp_path / "azure-pipelines.yml").write_text(
        "steps:\n"
        "  - task: PublishBuildArtifacts@1\n"
        "    inputs:\n"
        "      pathToPublish: resultats.json\n"
        f"    # {'é' * 450}\n"
        "    continueOnError: true\n",
        encoding="utf-8",
    )
    local = len(check_archiving_step_continue_on_error(tmp_path))
    assert local == 0
    assert (
        evaluer_sous_locale_ascii(
            f"len(g.check_archiving_step_continue_on_error(Path({_json(tmp_path)})))"
        )
        == local
    )


def test_attente_lue_en_utf8_quelle_que_soit_la_locale(tmp_path: Path) -> None:
    """Même ressort que l'archivage, pour la fenêtre de 200 caractères après l'action."""
    (tmp_path / "x.spec.ts").write_text(
        f"await page.click('#go');\n// {'é' * 250}\nawait page.waitForResponse(r => r);\n",
        encoding="utf-8",
    )
    local = len(check_event_wait_after_action(tmp_path))
    assert local == 0
    assert (
        evaluer_sous_locale_ascii(f"len(g.check_event_wait_after_action(Path({_json(tmp_path)})))")
        == local
    )


# Octets invalides : errors="ignore" les avale, un mode strict ou un nom de gestionnaire altéré
# lève dès le premier octet invalide.


def test_pre_commit_ignore_octets_invalides(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_bytes(
        b"repos:\n  - repo: local\n    hooks:\n      - id: ruff\n\xff\xfe\n      - id: eslint\n"
    )
    assert _pre_commit_hook_ids(tmp_path) == ["ruff", "eslint"]


def test_chaine_ci_ignore_octets_invalides(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_bytes(b"run: ruff\xff\xfe\n")
    assert _chain_text(tmp_path) == "run: ruff\n"


def test_archivage_ignore_octets_invalides(tmp_path: Path) -> None:
    (tmp_path / "azure-pipelines.yml").write_bytes(
        b"# \xff\xfe\n"
        b"steps:\n"
        b"  - task: PublishBuildArtifacts@1\n"
        b"    continueOnError: true\n"
    )
    assert len(check_archiving_step_continue_on_error(tmp_path)) == 1


def test_attente_ignore_octets_invalides(tmp_path: Path) -> None:
    (tmp_path / "x.spec.ts").write_bytes(
        b"// \xff\xfe\nawait page.click('#go');\nawait page.waitForNavigation();\n"
    )
    assert len(check_event_wait_after_action(tmp_path)) == 1


# Autres entrées jamais fournies.


def test_find_repo_root_est_plafonne_a_cinq_niveaux(tmp_path: Path) -> None:
    """Le ``.git`` à 4 niveaux au-dessus du départ est le dernier inspecté (5 dossiers : le
    départ et ses 4 parents) ; à 5 niveaux il est hors plafond et le départ est rendu tel quel."""
    (tmp_path / ".git").mkdir()
    quatre = tmp_path / "a" / "b" / "c" / "d"
    quatre.mkdir(parents=True)
    cinq = quatre / "e"
    cinq.mkdir()
    assert _find_repo_root(quatre) == tmp_path
    assert _find_repo_root(cinq) == cinq


def test_chain_text_sans_dossier_workflows_rend_la_chaine_vide(tmp_path: Path) -> None:
    assert _chain_text(tmp_path) == ""


def test_chain_text_joint_yml_et_yaml_par_un_saut_de_ligne(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("a: 1", encoding="utf-8")
    (workflows / "deploy.yaml").write_text("b: 2", encoding="utf-8")
    assert _chain_text(tmp_path) == "a: 1\nb: 2"


def test_workflow_files_liste_les_trois_emplacements_dans_l_ordre(tmp_path: Path) -> None:
    """Fixture verte à double sens : un fichier par emplacement et par extension, liste exacte.
    Un emplacement ou une extension oubliés, un ordre écrasé ou une soustraction à la place de
    l'addition font diverger la liste."""
    workflows = tmp_path / ".github" / "workflows"
    pipelines = tmp_path / "pipelines"
    workflows.mkdir(parents=True)
    pipelines.mkdir()
    attendus = [
        workflows / "a.yml",
        workflows / "b.yaml",
        pipelines / "p.yml",
        pipelines / "q.yaml",
        tmp_path / "azure-pipelines.yml",
        tmp_path / "azure-pipelines-ci.yaml",
    ]
    for fichier in attendus:
        fichier.write_text("x: 1\n", encoding="utf-8")
    assert _workflow_files(tmp_path) == attendus


def test_declared_tool_cite_sans_le_mot_run_est_cable(tmp_path: Path) -> None:
    """``pnpm lint`` câble le script ``lint`` sans écrire ``run lint`` : l'une OU l'autre
    citation suffit."""
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint ."}}), encoding="utf-8"
    )
    _write_chain(tmp_path, "jobs:\n  code:\n    steps:\n      - run: pnpm lint\n")
    pyproject = _write_pyproject(tmp_path)
    assert check_declared_tools_not_wired(pyproject, repo_root=tmp_path) == []


def test_pre_commit_hook_ids_retire_les_guillemets_et_seulement_eux(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: local\n    hooks:\n"
        "      - id: 'ruff'\n"
        '      - id: "mypy"\n'
        "      - id: XeslintX\n",
        encoding="utf-8",
    )
    assert _pre_commit_hook_ids(tmp_path) == ["ruff", "mypy", "XeslintX"]


def test_missing_dependencies_nomme_le_fichier_dans_les_avertissements_de_syntaxe(
    tmp_path: Path,
) -> None:
    """``filename=`` d'``ast.parse`` n'est pas muet : l'avertissement du compilateur sur une
    séquence d'échappement invalide nomme le fichier fautif ; sans lui, ``<unknown>``."""
    src = tmp_path / "app"
    src.mkdir()
    fautif = src / "ancien.py"
    fautif.write_text('PATRON = "\\d+"\n', encoding="utf-8")
    with warnings.catch_warnings(record=True) as alertes:
        warnings.simplefilter("always")
        check_missing_dependencies(src, _write_pyproject(tmp_path))
    assert [a.filename for a in alertes if "escape" in str(a.message)] == [str(fautif)]


def test_missing_dependencies_autorise_future_meme_hors_liste_stdlib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``__future__`` est autorisé explicitement, sans dépendre de la liste de l'interpréteur :
    avec une liste qui l'omet, ``from __future__ import annotations`` ne fait pas un import
    fantôme."""
    monkeypatch.setattr(sys, "stdlib_module_names", frozenset({"os"}))
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text(
        "from __future__ import annotations\nimport os\n", encoding="utf-8"
    )
    assert check_missing_dependencies(src, _write_pyproject(tmp_path)) == []


def test_attente_exclut_node_modules_vendor_venv_et_les_dossiers_homonymes(
    tmp_path: Path,
) -> None:
    """Les spécifications de ``node_modules``/``vendor``/``.venv`` ne sont pas jugées, un
    dossier nommé ``*.spec.ts`` n'est pas un fichier, et l'exclusion ne coupe pas la suite :
    la spécification fautive, triée après les exclues, est bien rendue."""
    motif = "await page.click('#go');\nawait page.waitForNavigation();\n"
    for exclu in ("node_modules/pkg", "Vendor", ".venv/lib"):
        dossier = tmp_path / exclu
        dossier.mkdir(parents=True)
        (dossier / "x.spec.ts").write_text(motif, encoding="utf-8")
    (tmp_path / "carton.spec.ts").mkdir()
    reel = tmp_path / "tests" / "e2e"
    reel.mkdir(parents=True)
    (reel / "z.spec.ts").write_text(motif, encoding="utf-8")
    findings = check_event_wait_after_action(tmp_path)
    assert [f["file"] for f in findings] == [str(reel / "z.spec.ts")]


def test_attente_message_complet(tmp_path: Path) -> None:
    (tmp_path / "x.spec.ts").write_text(
        "await page.click('#go');\nawait page.waitForResponse(r => r);\n", encoding="utf-8"
    )
    findings = check_event_wait_after_action(tmp_path)
    assert [f["issue"] for f in findings] == [
        "« await page.waitForResponse( » posé APRÈS l'action qui le déclenche — "
        "l'attente se déclare avant l'action, jamais après"
    ]


def test_cli_constat_sans_fichier_est_attribue_a_la_chaine_ci(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Un constat d'outil non câblé n'a pas de fichier : la ligne imprimée le dit mot pour mot."""
    (tmp_path / ".git").mkdir()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("x = 1\n", encoding="utf-8")
    assert main([str(src), str(pyproject)]) == 1
    assert capsys.readouterr().err == (
        "ai-antipatterns gate: FAIL (1 défaut(s))\n"
        "  - [outil-non-cable] (chaîne CI) : "
        "linter pyproject.toml '[tool.ruff]' absent de la chaîne CI\n"
    )
