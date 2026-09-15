"""Gate anti-patterns IA (TF-0103, sous-item 3) — six défauts fréquents du code généré.

Contrôle STATIQUE (AST + regex, aucune exécution), même posture heuristique que
``demo_markers_gate`` : coïncidence de motif, pas un compilateur. Six classes de défaut,
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
4. **Outil de qualité déclaré et jamais câblé** (TF-1041) — un script de qualité de
   ``package.json`` (lint/typecheck), un linter configuré dans ``pyproject.toml`` ([tool.ruff],
   [tool.mypy]…) ou un hook de ``.pre-commit-config.yaml`` qui n'apparaît dans AUCUN fichier de
   chaîne CI (``.github/workflows/*.yml``), ou y apparaît neutralisé (``|| true``,
   ``continue-on-error: true``) : un outil déclaré et jamais appelé est un outil qui n'existe
   pas — la déclaration rassure d'autant plus qu'elle est longuement commentée (mesure du
   11/09/2026, Produit-11).
5. **Étape d'archivage de preuves sous ``continueOnError``** (TF-1112, mesure Produit-11 du
   14/09/2026) — une étape ``PublishBuildArtifacts@`` (Azure Pipelines) ou
   ``actions/upload-artifact@`` (GitHub Actions) protégée par ``continueOnError: true`` /
   ``continue-on-error: true`` : le chemin qu'elle publie peut ne jamais avoir existé, l'étape
   reste verte quand même, et le premier échec réel qu'elle devait archiver (traces, captures,
   contexte de page) ne laisse aucune trace. Mesure fondatrice : ``resultats.json`` n'a JAMAIS
   existé sur aucun run — l'étape échouait à chaque exécution et ``continueOnError`` la rendait
   verte depuis sa naissance. Prolongement du §4 : archiver sous garde d'échec neutralisée
   n'archive rien, exactement comme un outil câblé sous garde neutralisée n'est pas câblé.
6. **Attente d'événement posée APRÈS l'action qu'elle observe** (TF-1111, mesure Produit-11 du
   11/09/2026) — dans une spécification Playwright (``*.spec.ts``), un ``await page.waitFor*(``
   qui suit textuellement, dans le même bloc, un ``await`` d'action (``click``/``fill``/
   ``press``/``setInputFiles``) mesure la vitesse de la machine, pas le produit : l'aller-retour
   peut s'achever avant que l'abonnement à l'événement ne soit en place, d'où une attente jamais
   satisfaite alors que le produit a déjà répondu correctement. Mesure fondatrice :
   ``page.waitForResponse(...)`` posé après ``click()`` a rendu 92/93 sur l'agent d'intégration
   continue, deux fois, pour un écart reproduit ZÉRO fois en local (six exécutions vertes) — la
   capture d'écran archivée par le run en échec montrait le motif serveur déjà attendu à l'écran.
   Contrôle STATIQUE, PROPRE à ce défaut : contrairement aux contrôles 1-5, il DESCEND dans
   ``tests/`` au lieu de l'exclure — c'est là, et seulement là, que ce motif vit.

Hors périmètre volontaire des contrôles 1-5 (mêmes exclusions que ``demo_markers_gate``) :
``tests/``, ``migrations/``, ``vendor/`` (dépendance tierce épinglée, jamais modifiée) et
``.venv/``.
"""

from __future__ import annotations

import ast
import json
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


# --- 4. Outil de qualité déclaré, jamais câblé (TF-1041) ----------------------

_QUALITY_SCRIPT_NAME = re.compile(r"lint|typecheck|type-check|tsc", re.IGNORECASE)
_NEUTRALIZED = re.compile(r"\|\|\s*true|continue-on-error:\s*true", re.IGNORECASE)
_KNOWN_PYPROJECT_LINTERS = ("ruff", "mypy", "flake8", "black", "pylint")


def _find_repo_root(start: Path, *, max_levels: int = 5) -> Path:
    """Remonte depuis ``start`` jusqu'à un dossier portant ``.git`` (racine du dépôt), plafonné
    à ``max_levels`` — un dépôt de forge peut loger son produit un cran sous la racine git
    (chaîne CI en ``.github/`` un niveau au-dessus du ``pyproject.toml`` audité)."""
    current = start.resolve()
    for _ in range(max_levels):
        if (current / ".git").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return start


def _package_json_quality_scripts(repo_root: Path) -> dict[str, str]:
    """Scripts de qualité déclarés par ``package.json`` (racine) : lint/typecheck/tsc."""
    pkg = repo_root / "package.json"
    if not pkg.exists():
        return {}
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}
    return {
        name: str(cmd)
        for name, cmd in scripts.items()
        if isinstance(name, str) and _QUALITY_SCRIPT_NAME.search(name)
    }


def _pyproject_linters(pyproject_path: Path) -> list[str]:
    """Linters configurés dans le ``pyproject.toml`` audité : présence d'une table
    ``[tool.<linter>]`` parmi les linters Python usuels — la présence de la table vaut
    déclaration, indépendamment de son contenu."""
    if not pyproject_path.exists():
        return []
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return []
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return []
    return [name for name in _KNOWN_PYPROJECT_LINTERS if name in tool]


def _pre_commit_hook_ids(repo_root: Path) -> list[str]:
    """Identifiants des hooks déclarés par ``.pre-commit-config.yaml`` (racine) — lecture ligne
    à ligne, sans dépendance YAML tierce (même posture que le reste du gate)."""
    cfg = repo_root / ".pre-commit-config.yaml"
    if not cfg.exists():
        return []
    ids: list[str] = []
    for line in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*-?\s*id:\s*(\S+)", line)
        if m:
            ids.append(m.group(1).strip("'\""))
    return ids


def _chain_text(repo_root: Path) -> str:
    """Contenu concaténé des fichiers de chaîne CI connus (``.github/workflows/*.yml|yaml``)."""
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.exists():
        return ""
    files = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    return "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in files)


def _cited_and_wired(token: str, chain_text: str) -> bool:
    """Le jeton apparaît dans la chaîne ET sa ligne n'est pas neutralisée (``|| true``,
    ``continue-on-error: true``)."""
    if token not in chain_text:
        return False
    return any(
        token in line and not _NEUTRALIZED.search(line) for line in chain_text.splitlines()
    )


def check_declared_tools_not_wired(
    pyproject_path: Path, *, repo_root: Path | None = None
) -> list[dict[str, str]]:
    """Un outil de qualité DÉCLARÉ (script package.json, linter pyproject.toml, hook
    pre-commit) et absent — ou neutralisé — de la chaîne CI est un outil qui n'existe pas."""
    root = repo_root if repo_root is not None else _find_repo_root(pyproject_path.parent)
    chain_text = _chain_text(root)
    findings: list[dict[str, str]] = []

    for name, cmd in _package_json_quality_scripts(root).items():
        if not (_cited_and_wired(f"run {name}", chain_text) or _cited_and_wired(name, chain_text)):
            findings.append(
                {
                    "kind": "outil-non-cable",
                    "issue": f"script package.json '{name}' ({cmd}) absent de la chaîne CI",
                }
            )
    for linter in _pyproject_linters(pyproject_path):
        if not _cited_and_wired(linter, chain_text):
            findings.append(
                {
                    "kind": "outil-non-cable",
                    "issue": f"linter pyproject.toml '[tool.{linter}]' absent de la chaîne CI",
                }
            )
    for hook_id in _pre_commit_hook_ids(root):
        if not _cited_and_wired(hook_id, chain_text):
            findings.append(
                {
                    "kind": "outil-non-cable",
                    "issue": f"hook .pre-commit-config.yaml '{hook_id}' absent de la chaîne CI",
                }
            )
    return findings


# --- 5. Étape d'archivage sous continueOnError (TF-1112) ----------------------

_ARCHIVE_STEP = re.compile(
    r"^[ \t]*-\s*(?:task\s*:\s*PublishBuildArtifacts@\d+|uses\s*:\s*actions/upload-artifact@)",
    re.IGNORECASE | re.MULTILINE,
)
_CONTINUE_ON_ERROR_TRUE = re.compile(
    r"continueOnError\s*:\s*true|continue-on-error\s*:\s*true", re.IGNORECASE
)
_ARCHIVE_WINDOW = 400  # caractères après le déclencheur d'étape couvrant sa configuration


def _workflow_files(repo_root: Path) -> list[Path]:
    """Fichiers de chaîne CI connus, les deux dialectes du parc (même emplacements
    qu'``oracle-ops`` O-8) : GitHub Actions (``.github/workflows/*.yml|yaml``) et Azure
    Pipelines (``azure-pipelines*.yml|yaml`` à la racine, ``pipelines/*.yml|yaml``)."""
    files: list[Path] = []
    workflows_dir = repo_root / ".github" / "workflows"
    if workflows_dir.exists():
        files += sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    pipelines_dir = repo_root / "pipelines"
    if pipelines_dir.exists():
        files += sorted(pipelines_dir.glob("*.yml")) + sorted(pipelines_dir.glob("*.yaml"))
    if repo_root.exists():
        for pattern in ("azure-pipelines*.yml", "azure-pipelines*.yaml"):
            files += sorted(repo_root.glob(pattern))
    return files


def check_archiving_step_continue_on_error(start_dir: Path) -> list[dict[str, str]]:
    """TF-1112 (mesure Produit-11, 14/09/2026) : une étape d'archivage de preuves protégée par
    ``continueOnError``/``continue-on-error: true`` ne peut jamais échouer, quel que soit le
    sort du chemin qu'elle publie — c'est le contrôle STATIQUE réclamé par la mesure (motif
    reconnaissable à la lecture), le prolongement de la vérification RUNTIME (l'étape produit
    réellement son artefact) qui reste, elle, hors périmètre d'un contrôle sans exécution."""
    root = _find_repo_root(start_dir)
    findings: list[dict[str, str]] = []
    for path in _workflow_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _ARCHIVE_STEP.finditer(text):
            window = text[match.start() : match.start() + _ARCHIVE_WINDOW]
            if _CONTINUE_ON_ERROR_TRUE.search(window):
                findings.append(
                    {
                        "file": str(path),
                        "kind": "archivage-non-verifiable",
                        "issue": "étape d'archivage sous continueOnError/continue-on-error: "
                        "true — un chemin jamais produit reste vert, l'échec qu'elle devait "
                        "archiver ne laisse aucune trace",
                    }
                )
    return findings


# --- 6. Attente d'événement posée après l'action (TF-1111) --------------------

_PLAYWRIGHT_ACTION_AWAIT = re.compile(
    r"await\s+page\.(?:click|fill|press|setInputFiles)\(", re.IGNORECASE
)
_PLAYWRIGHT_WAITFOR_AWAIT = re.compile(r"await\s+page\.waitFor\w*\(", re.IGNORECASE)
_EVENT_WAIT_WINDOW = 200  # caractères après l'action couvrant l'instruction suivante
_SPEC_EXCLUDED_PARTS = ("vendor", ".venv", "node_modules")


def check_event_wait_after_action(source_dir: Path) -> list[dict[str, str]]:
    """TF-1111 (mesure Produit-11, 11/09/2026) : contrairement aux contrôles 1-5, celui-ci
    DESCEND délibérément dans les spécifications Playwright (``*.spec.ts``) — c'est le seul
    endroit où ce motif vit, et l'exclusion générique de ``tests/`` le rendrait aveugle."""
    findings: list[dict[str, str]] = []
    for path in sorted(source_dir.rglob("*.spec.ts")):
        if not path.is_file() or any(
            part.lower() in _SPEC_EXCLUDED_PARTS for part in path.parts
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _PLAYWRIGHT_ACTION_AWAIT.finditer(text):
            window = text[match.end() : match.end() + _EVENT_WAIT_WINDOW]
            wf = _PLAYWRIGHT_WAITFOR_AWAIT.search(window)
            if wf:
                findings.append(
                    {
                        "file": str(path),
                        "kind": "attente-posee-apres-action",
                        "issue": f"« {wf.group(0)} » posé APRÈS l'action qui le déclenche — "
                        "l'attente se déclare avant l'action, jamais après",
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
        findings += check_declared_tools_not_wired(pyproject_path)
    else:
        findings.append(
            {"skipped": "pyproject.toml introuvable — imports fantômes non contrôlés"}
        )
    findings += check_hardcoded_secrets(source_dir)
    findings += check_routes_without_auth(source_dir)
    findings += check_archiving_step_continue_on_error(source_dir)
    findings += check_event_wait_after_action(source_dir)
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
        print(f"  - [{f['kind']}] {f.get('file', '(chaîne CI)')} : {f['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
