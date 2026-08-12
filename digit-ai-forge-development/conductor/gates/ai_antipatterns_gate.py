"""Gate anti-patterns IA (TF-0103, sous-item 3) — trois défauts fréquents du code généré.

Contrôle STATIQUE (AST + regex, aucune exécution), même posture heuristique que
``demo_markers_gate`` : coïncidence de motif, pas un compilateur. Trois classes de défaut,
observées dans le code produit par des agents autonomes :

1. **Imports fantômes** — un module importé qui n'est ni la bibliothèque standard, ni un
   paquet local, ni déclaré dans le manifeste de dépendances (``pyproject.toml``) : l'agent a
   halluciné une dépendance, ou a oublié de la déclarer — le code casse à l'installation
   propre (``uv sync`` sans le paquet préinstallé par accident dans l'environnement de dev).
2. **Secrets en dur** — une valeur secrète (clé API connue, ou littéral affecté à une variable
   au nom évocateur) écrite en clair dans le source au lieu d'être lue depuis l'environnement.
3. **Routes sans autorisation** — une route HTTP (FastAPI ``@app.get``/``@router.post``…) sans
   dépendance d'authentification visible ni marqueur explicite de route publique : l'agent a
   ajouté un endpoint sans se poser la question de qui peut l'appeler.

Hors périmètre volontaire (mêmes exclusions que ``demo_markers_gate``) : ``tests/``,
``migrations/``, ``vendor/`` (dépendance tierce épinglée, jamais modifiée) et ``.venv/``.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

from conductor.contracts import GateVerdict

_EXCLUDED_PARTS = ("test", "tests", "migrations", "vendor", ".venv")

# --- 1. Imports fantômes -----------------------------------------------------

# Paquets dont le nom de distribution PyPI diffère du nom du module importé (heuristique
# extensible — non exhaustive, comme tout contrôle de coïncidence de chaîne de ce gate).
_IMPORT_NAME_ALIASES: dict[str, str] = {
    "pyyaml": "yaml",
    "pillow": "pil",
    "beautifulsoup4": "bs4",
    "python-dotenv": "dotenv",
    "python-jose": "jose",
    "python-multipart": "multipart",
    "scikit-learn": "sklearn",
    "psycopg2-binary": "psycopg2",
    "opencv-python": "cv2",
    "pyjwt": "jwt",
}

_DEP_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _dep_name(spec: str) -> str | None:
    """Extrait le nom de paquet d'une spec PEP 508 (ignore extras/marqueurs/version)."""
    spec = spec.strip()
    if not spec or spec.startswith("#") or "://" in spec or spec.startswith("git+"):
        return None
    m = _DEP_NAME_RE.match(spec)
    return m.group(1) if m else None


def _import_names_for_dependency(dist_name: str) -> set[str]:
    lowered = dist_name.lower()
    if lowered.startswith("types-") or lowered.endswith("-stubs"):
        return set()  # stub de typage : jamais importé à l'exécution
    if lowered in _IMPORT_NAME_ALIASES:
        return {_IMPORT_NAME_ALIASES[lowered]}
    return {lowered.replace("-", "_")}


def manifest_import_names(pyproject_path: Path) -> set[str]:
    """Noms de modules couverts par le manifeste : ``[project.dependencies]``,
    ``[dependency-groups]`` (PEP 735) et ``[project.optional-dependencies]``."""
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    specs: list[str] = list(project.get("dependencies", []))
    for group_deps in data.get("dependency-groups", {}).values():
        specs += [d for d in group_deps if isinstance(d, str)]  # ignore {include-group: ...}
    for extra_deps in project.get("optional-dependencies", {}).values():
        specs += list(extra_deps)
    names: set[str] = set()
    for spec in specs:
        dep_name = _dep_name(spec)
        if dep_name:
            names |= _import_names_for_dependency(dep_name)
    return names


def _imported_top_level_modules(tree: ast.Module) -> set[str]:
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # import relatif (`from . import x`) : toujours local
                continue
            if node.module:
                mods.add(node.module.split(".")[0])
    return mods


def check_missing_dependencies(
    source_dir: Path, pyproject_path: Path, *, local_packages: set[str] | None = None
) -> list[dict[str, str]]:
    """Imports ni stdlib, ni manifeste, ni paquet local → import fantôme."""
    allowed = set(sys.stdlib_module_names) | {"__future__"} | manifest_import_names(
        pyproject_path
    )
    allowed |= local_packages if local_packages is not None else {source_dir.name}
    findings: list[dict[str, str]] = []
    for path in sorted(source_dir.rglob("*.py")):
        if not path.is_file() or _is_excluded(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
        except SyntaxError:
            continue  # hors périmètre : ruff/mypy couvrent la validité syntaxique
        for mod in sorted(_imported_top_level_modules(tree) - allowed):
            findings.append(
                {
                    "file": str(path),
                    "kind": "import-fantome",
                    "issue": f"import '{mod}' absent du manifeste de dépendances",
                }
            )
    return findings


# --- 2. Secrets en dur --------------------------------------------------------

# Préfixes de clés connues (AWS, GitHub, Google, Slack, Stripe, clé privée PEM).
_KNOWN_SECRET_PATTERN = re.compile(
    r"AKIA[0-9A-Z]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{36}"
    r"|github_pat_[A-Za-z0-9_]{22,}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|sk_(live|test)_[A-Za-z0-9]{16,}"
    r"|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"
)

# Affectation littérale à une variable au nom évocateur d'un secret.
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(secret\w*|password\w*|passwd|api[_-]?key\w*|access[_-]?token\w*|private[_-]?key)"
    r"\s*[:=]\s*[\"']([^\"']{8,})[\"']"
)

# Valeurs manifestement des placeholders — pas un vrai secret.
_PLACEHOLDER = re.compile(
    r"(?i)^(changeme|change[_-]?me|xxx+|todo|example|placeholder|your[_-]|<.*>|\{\{.*\}\}|\$\{.*\}|\.\.\.|fixme|dummy|fake|test[_-]?)"
)


def check_hardcoded_secrets(source_dir: Path) -> list[dict[str, str]]:
    """Clé connue en clair, ou littéral non-placeholder affecté à une variable sensible."""
    findings: list[dict[str, str]] = []
    for path in sorted(source_dir.rglob("*.py")):
        if not path.is_file() or _is_excluded(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _KNOWN_SECRET_PATTERN.search(text):
            findings.append(
                {"file": str(path), "kind": "secret-en-dur", "issue": "clé connue en clair"}
            )
            continue
        for match in _SECRET_ASSIGNMENT.finditer(text):
            value = match.group(2)
            if _PLACEHOLDER.match(value) or value.startswith(("os.", "settings.")):
                continue
            findings.append(
                {
                    "file": str(path),
                    "kind": "secret-en-dur",
                    "issue": f"valeur en dur affectée à '{match.group(1)}'",
                }
            )
    return findings


# --- 3. Routes sans autorisation ---------------------------------------------

_ROUTE_DECORATOR = re.compile(
    r"@\w+\.(get|post|put|delete|patch|options|head)\(", re.IGNORECASE
)
_AUTH_MARKER = re.compile(
    r"Depends\(|Security\(|current_user|require_auth|get_current_user", re.IGNORECASE
)
_PUBLIC_OPT_OUT = re.compile(r"route[_-]publique[_-]ok|public[_-]route[_-]ok", re.IGNORECASE)
_ROUTE_WINDOW = 400  # caractères après le décorateur couvrant sa signature de fonction


def check_routes_without_auth(source_dir: Path) -> list[dict[str, str]]:
    """Route HTTP sans `Depends(...)`/`Security(...)` d'auth ni marqueur public explicite."""
    findings: list[dict[str, str]] = []
    for path in sorted(source_dir.rglob("*.py")):
        if not path.is_file() or _is_excluded(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _ROUTE_DECORATOR.finditer(text):
            window = text[match.start() : match.start() + _ROUTE_WINDOW]
            if _AUTH_MARKER.search(window) or _PUBLIC_OPT_OUT.search(window):
                continue
            findings.append(
                {
                    "file": str(path),
                    "kind": "route-sans-auth",
                    "issue": f"route '{match.group(0)}' sans dépendance d'auth ni marqueur public",
                }
            )
    return findings


# --- Agrégation ---------------------------------------------------------------


def _is_excluded(path: Path) -> bool:
    return any(part.lower() in _EXCLUDED_PARTS for part in path.parts)


def run_ai_antipatterns_gate(
    source_dir: Path, pyproject_path: Path | None = None, *, local_packages: set[str] | None = None
) -> GateVerdict:
    """P-06 : arborescence source absente → SKIP tracé, jamais un échec implicite."""
    if not source_dir.exists():
        return GateVerdict(
            gate="ai-antipatterns",
            passed=True,
            findings=[{"skipped": f"arborescence source absente : {source_dir}"}],
        )
    findings: list[dict[str, str]] = []
    if pyproject_path is not None and pyproject_path.exists():
        findings += check_missing_dependencies(
            source_dir, pyproject_path, local_packages=local_packages
        )
    else:
        findings.append(
            {"skipped": "pyproject.toml introuvable — imports fantômes non contrôlés"}
        )
    findings += check_hardcoded_secrets(source_dir)
    findings += check_routes_without_auth(source_dir)
    blocking = [f for f in findings if "skipped" not in f]
    return GateVerdict(
        gate="ai-antipatterns", passed=not blocking, findings=findings, log_ref=str(source_dir)
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.ai_antipatterns_gate <source_dir> [pyproject]``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in (1, 2):
        print(
            "usage: python -m conductor.gates.ai_antipatterns_gate <source_dir> [pyproject.toml]",
            file=sys.stderr,
        )
        return 2
    source_dir = Path(args[0])
    pyproject_path = Path(args[1]) if len(args) == 2 else source_dir.parent / "pyproject.toml"
    verdict = run_ai_antipatterns_gate(source_dir, pyproject_path)
    if verdict.passed:
        print("ai-antipatterns gate: PASS")
        return 0
    blocking = [f for f in verdict.findings if "skipped" not in f]
    print(f"ai-antipatterns gate: FAIL ({len(blocking)} défaut(s))", file=sys.stderr)
    for f in blocking:
        print(f"  - [{f['kind']}] {f['file']} : {f['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
