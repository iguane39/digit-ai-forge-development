"""Gate anti-patterns IA (TF-0103.3) : imports fantômes, secrets en dur, routes sans auth."""

from __future__ import annotations

from pathlib import Path

from conductor.gates.ai_antipatterns_gate import (
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
    assert findings and findings[0]["issue"] == "clé connue en clair"


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
    assert len(findings) == 1
    assert findings[0]["kind"] == "route-sans-auth"


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
    assert any("skipped" in f for f in verdict.findings)


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


def test_cli_main_pass_et_fail(tmp_path: Path) -> None:
    pyproject = _write_pyproject(tmp_path)
    src = tmp_path / "app"
    src.mkdir()
    (src / "main.py").write_text("import requests\n", encoding="utf-8")
    assert main([str(src), str(pyproject)]) == 1
    (src / "main.py").write_text("import os\n", encoding="utf-8")
    assert main([str(src), str(pyproject)]) == 0
