"""Gate anti-patterns IA (TF-0103.3) : imports fantômes, secrets en dur, routes sans auth."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.gates.ai_antipatterns_gate import (
    _dep_name,
    _import_names_for_dependency,
    check_hardcoded_secrets,
    check_missing_dependencies,
    check_routes_without_auth,
    main,
    manifest_import_names,
    run_ai_antipatterns_gate,
)

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
