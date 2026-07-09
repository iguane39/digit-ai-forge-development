"""Détection de capacités — faits durs (déterministes) d'un repo, à la racine et par rôle.

Base de la résolution de profil générique (P-14/P-15) : au lieu d'énumérer une techno de plus,
on scanne les **marqueurs réels** (gestionnaires de paquets, scripts, orchestrateurs, UI) par
sous-répertoire de rôle, puis ``synthesize_profile`` (profiles.py) en fabrique un ``TargetProfile``.

Aucune dépendance réseau, aucun import d'``onramp`` (évite le cycle detect↔profiles).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Répertoires de rôle candidats (racine incluse via ".") — monorepos multi-stack (P-16).
_ROLE_DIRS = ["backend", "frontend", "api", "web", "app", "server", "client", "."]
# Rôles dont le nom implique une UI (le gate design s'applique).
_UI_DIRS = {"frontend", "web", "client", "ui"}
# Dépendances trahissant un front (package.json).
_UI_DEPS = ("react", "vue", "svelte", "@angular", "next", "vite", "solid-js")

# Marqueur de manifeste → écosystème (l'ordre fixe la priorité si plusieurs coexistent).
_MANIFESTS: list[tuple[str, str]] = [
    ("pyproject.toml", "python"),
    ("requirements.txt", "python"),
    ("Pipfile", "python"),
    ("package.json", "node"),
    ("go.mod", "go"),
    ("Cargo.toml", "rust"),
    ("pom.xml", "java-maven"),
    ("build.gradle", "java-gradle"),
    ("composer.json", "php"),
    ("Gemfile", "ruby"),
]
_JS_LOCKFILES: dict[str, str] = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lockb": "bun",
    "package-lock.json": "npm",
}
# Commandes conventionnelles par écosystème (inférence — validée au HITL-0, jamais un défaut
# silencieux du gate : P-06 reste vrai côté moteur).
_ECO_CMDS: dict[str, tuple[str | None, str | None, str | None]] = {
    # (test, build, lint)
    "python": ("pytest", None, None),
    "go": ("go test ./...", "go build ./...", None),
    "rust": ("cargo test", "cargo build", None),
    "java-maven": ("mvn test", "mvn package", None),
    "java-gradle": ("gradle test", "gradle build", None),
    "php": ("composer test", None, None),
    "ruby": ("bundle exec rake test", None, None),
}


@dataclass(frozen=True)
class RoleCapability:
    """Fait détecté pour un rôle : où, quel écosystème, quelles commandes, UI ou non."""

    directory: str
    ecosystem: str
    pkg_manager: str
    is_ui: bool
    test: str | None
    build: str | None
    lint: str | None


@dataclass(frozen=True)
class Capabilities:
    """Ensemble des rôles détectés dans un repo (vide = aucun signal exploitable)."""

    roles: dict[str, RoleCapability] = field(default_factory=dict)

    @property
    def has_signal(self) -> bool:
        return bool(self.roles)

    @property
    def has_ui(self) -> bool:
        return any(r.is_ui for r in self.roles.values())


def _read_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _pkg_scripts(d: Path) -> set[str]:
    scripts = _read_json(d / "package.json").get("scripts")
    return set(scripts) if isinstance(scripts, dict) else set()


def _pkg_deps(d: Path) -> set[str]:
    data = _read_json(d / "package.json")
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            deps.update(section)
    return deps


def _js_manager(d: Path) -> str:
    for lock, mgr in _JS_LOCKFILES.items():
        if (d / lock).exists():
            return mgr
    return "npm"


def _python_manager(d: Path) -> str:
    if (d / "poetry.lock").exists():
        return "poetry"
    if (d / "Pipfile").exists():
        return "pipenv"
    if (d / "pyproject.toml").exists():
        return "uv"  # convention de la forge
    return "pip"


def _make_test_target(d: Path) -> bool:
    """Le repo expose-t-il une cible `test:` dans un Makefile (signal de commande) ?"""
    mk = d / "Makefile"
    if not mk.exists():
        return False
    for line in mk.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("test:"):
            return True
    return False


def _first_ecosystem(d: Path) -> str | None:
    for marker, eco in _MANIFESTS:
        if (d / marker).exists():
            return eco
    return None


def _role_for_dir(d: Path) -> RoleCapability | None:
    """Fabrique une RoleCapability pour un répertoire, ou None s'il n'expose aucun signal."""
    eco = _first_ecosystem(d)
    if eco is None:
        if _make_test_target(d):  # pas de manifeste mais un orchestrateur avec `test:`
            return RoleCapability(d.name, "make", "make", (d / "index.html").exists(),
                                  "make test", None, None)
        return None
    is_ui = d.name in _UI_DIRS or (d / "index.html").exists()
    if eco == "node":
        pm = _js_manager(d)
        scripts = _pkg_scripts(d)
        deps = _pkg_deps(d)
        is_ui = is_ui or any(u in dep for dep in deps for u in _UI_DEPS)
        test = f"{pm} test"
        build = f"{pm} run build" if "build" in scripts else None
        lint = f"{pm} run lint" if "lint" in scripts else None
        return RoleCapability(d.name, "node", pm, is_ui, test, build, lint)
    if eco == "python":
        pm = _python_manager(d)
        tst, bld, lnt = _ECO_CMDS["python"]
        return RoleCapability(d.name, "python", pm, is_ui, tst, bld, lnt)
    pm = {"go": "go", "rust": "cargo", "java-maven": "mvn", "java-gradle": "gradle",
          "php": "composer", "ruby": "bundle"}.get(eco, eco)
    tst, bld, lnt = _ECO_CMDS.get(eco, (None, None, None))
    return RoleCapability(d.name, eco, pm, is_ui, tst, bld, lnt)


def detect_capabilities(repo: Path) -> Capabilities:
    """Scanne racine + répertoires de rôle et renvoie les capacités détectées (§4.3)."""
    roles: dict[str, RoleCapability] = {}
    for sub in _ROLE_DIRS:
        d = repo if sub == "." else repo / sub
        if not d.is_dir():
            continue
        cap = _role_for_dir(d)
        if cap is None:
            continue
        roles["app" if sub == "." else sub] = cap
    return Capabilities(roles=roles)
