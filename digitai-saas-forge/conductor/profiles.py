"""TargetProfile — le contrat d'une stack (gate code, applicabilité design, briques).

Le profil `fastapi-saas` réifie le comportement actuel de la forge (cf. spec brownfield).
`enforceable` décrit la part du contrat applicable — base de la dégradation déclarée (B).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from conductor.catalog import CATALOG, BrickSpec


class TargetProfile(BaseModel):
    name: str
    code_check: str | None  # commande du gate code ; None → gate code non applicable
    has_ui: bool  # le gate design s'applique-t-il ?
    design_md_path: str = "design/DESIGN.md"  # convention RELATIVE (≠ chemin concret du Substrate)
    conventions: str = ""
    brick_catalog: dict[str, BrickSpec] = Field(default_factory=dict)
    # P-11 : rôle → répertoire relatif (ex. backend/frontend) et rôle → gestionnaire de paquets.
    roles: dict[str, str] = Field(default_factory=dict)
    pkg_managers: dict[str, str] = Field(default_factory=dict)
    # P-09 : commandes dérivées du repo (None → repli sur `code_check` / non applicable).
    test_cmd: list[str] | None = None
    build_cmd: list[str] | None = None
    lint_cmd: list[str] | None = None

    @property
    def enforceable(self) -> dict[str, bool]:
        """Part du contrat réellement applicable (gates) pour cette stack."""
        return {"code": self.code_check is not None, "design": self.has_ui}


# Profil canonique = la forge actuelle (FastAPI + React, ruff/mypy/pytest, double gate).
FASTAPI_SAAS = TargetProfile(
    name="fastapi-saas",
    code_check="uv run pytest",
    has_ui=True,
    design_md_path="design/DESIGN.md",
    conventions="ruff + mypy strict; FastAPI + React; scaffold-first; double gate",
    brick_catalog=CATALOG,
    roles={"backend": "backend", "frontend": "frontend"},
    pkg_managers={"backend": "uv", "frontend": "npm"},
)

# Profil non-FastAPI (1ᵉʳ profil BB). B-standard : on hisse au contrat dans la stack d'origine.
NODE_TS = TargetProfile(
    name="node-ts",
    code_check="npm test",
    has_ui=True,
    design_md_path="design/DESIGN.md",
    conventions="Node/TypeScript ; npm test ; UI présente",
    brick_catalog={},
    roles={"app": "."},
    pkg_managers={"app": "npm"},
)

_PROFILES: dict[str, TargetProfile] = {"fastapi": FASTAPI_SAAS, "node-ts": NODE_TS}


def profile_for_stack(stack: str) -> TargetProfile | None:
    """Mappe une stack détectée à son TargetProfile (None si non supportée)."""
    return _PROFILES.get(stack)


_JS_LOCKFILES: dict[str, str] = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lockb": "bun",
    "package-lock.json": "npm",
}


def _js_manager(repo: Path) -> str:
    """Gestionnaire JS déduit du lockfile présent (défaut npm)."""
    for lock, mgr in _JS_LOCKFILES.items():
        if (repo / lock).exists():
            return mgr
    return "npm"


def _make_targets(makefile: Path) -> set[str]:
    """Cibles déclarées dans un Makefile (lignes `cible:`)."""
    targets: set[str] = set()
    for line in makefile.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


def derive_profile(repo: Path, base: TargetProfile) -> TargetProfile:
    """P-09 — dérive test/build/lint des marqueurs RÉELS du repo (package.json scripts, Makefile).

    Précédence : `package.json` > `Makefile` ; sinon repli sur `base` (aucune commande inventée).
    """
    updates: dict[str, list[str]] = {}
    pkg = repo / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            scripts = {}
        pm = _js_manager(repo)
        for field, script in (("test_cmd", "test"), ("build_cmd", "build"), ("lint_cmd", "lint")):
            if isinstance(scripts, dict) and script in scripts:
                updates[field] = [pm, "run", script]
    makefile = repo / "Makefile"
    if makefile.exists():
        targets = _make_targets(makefile)
        for field, target in (("test_cmd", "test"), ("build_cmd", "build"), ("lint_cmd", "lint")):
            if field not in updates and target in targets:  # package.json prioritaire
                updates[field] = ["make", target]
    return base.model_copy(update=updates) if updates else base
