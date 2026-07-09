"""TargetProfile — le contrat d'une stack (gate code, applicabilité design, briques).

Le profil `fastapi-saas` réifie le comportement actuel de la forge (cf. spec brownfield).
`enforceable` décrit la part du contrat applicable — base de la dégradation déclarée (B).
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from conductor.capabilities import Capabilities, detect_capabilities
from conductor.catalog import CATALOG, BrickSpec

# Rôles « backend » préférés comme commande primaire (pour la baseline / le gate simple).
_PRIMARY_ROLE_ORDER = ["backend", "api", "server", "app"]

Confidence = Literal["curated", "manifest", "inferred", "analyzed"]


class RoleCommands(BaseModel):
    """Commandes d'un rôle (P-16) ; clé absente = non applicable → gate skip tracé (P-06)."""

    test: str | None = None
    build: str | None = None
    lint: str | None = None


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
    # P-16 : commandes PAR RÔLE (monorepos multi-stack). Vide → moteur lit `code_check` (curés).
    commands: dict[str, RoleCommands] = Field(default_factory=dict)
    # P-09 : commandes dérivées du repo (None → repli sur `code_check` / non applicable).
    test_cmd: list[str] | None = None
    build_cmd: list[str] | None = None
    lint_cmd: list[str] | None = None

    @property
    def enforceable(self) -> dict[str, bool]:
        """Part du contrat réellement applicable (gates) pour cette stack."""
        code = self.code_check is not None or any(
            rc.test is not None for rc in self.commands.values()
        )
        return {"code": code, "design": self.has_ui}

    @staticmethod
    def from_manifest(path: Path) -> TargetProfile:
        """Parse un manifeste opposable `.forge/profile.toml` (P-18) → TargetProfile.

        Validation : `name` requis ; au moins un rôle ; commandes en chaîne (découpées `shlex`
        côté gate, jamais `shell=True`) ; chemins relatifs."""
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Manifeste {path} : champ `name` requis (chaîne non vide).")
        roles = {str(k): str(v) for k, v in (data.get("roles") or {}).items()}
        if not roles:
            raise ValueError(f"Manifeste {path} : au moins un rôle requis dans [roles].")
        pkg_managers = {str(k): str(v) for k, v in (data.get("pkg_managers") or {}).items()}
        commands: dict[str, RoleCommands] = {}
        for role, spec in (data.get("commands") or {}).items():
            if isinstance(spec, dict):
                commands[str(role)] = RoleCommands(
                    test=spec.get("test"), build=spec.get("build"), lint=spec.get("lint")
                )
        design_md_path = str(data.get("design_md_path") or "design/DESIGN.md")
        return TargetProfile(
            name=name,
            code_check=_primary_test(commands),
            has_ui=bool(data.get("has_ui", False)),
            design_md_path=design_md_path,
            conventions="Profil déclaré via manifeste .forge/profile.toml (opposable, P-18).",
            brick_catalog={},
            roles=roles,
            pkg_managers=pkg_managers,
            commands=commands,
        )


@dataclass(frozen=True)
class ProfileResolution:
    """Profil résolu + niveau de confiance journalisé/affiché au HITL-0 (P-14/P-17)."""

    profile: TargetProfile
    confidence: Confidence


def _primary_test(commands: dict[str, RoleCommands]) -> str | None:
    """Commande de test primaire (rôle backend préféré) pour la baseline / le gate simple."""
    for role in _PRIMARY_ROLE_ORDER:
        rc = commands.get(role)
        if rc and rc.test:
            return rc.test
    for rc in commands.values():
        if rc.test:
            return rc.test
    return None


def synthesize_profile(repo: Path, caps: Capabilities) -> TargetProfile:
    """Fabrique un TargetProfile à partir des capacités détectées (③ inférence, P-14).

    `code_check` = commande de test primaire (ou None → gate code skip tracé, P-06). Catalogue de
    briques vide (dégradation déclarée : le harness vient du repo, pas de scaffold riche)."""
    roles = {name: cap.directory for name, cap in caps.roles.items()}
    pkg_managers = {name: cap.pkg_manager for name, cap in caps.roles.items()}
    commands = {
        name: RoleCommands(test=cap.test, build=cap.build, lint=cap.lint)
        for name, cap in caps.roles.items()
    }
    ecosystems = sorted({cap.ecosystem for cap in caps.roles.values()})
    return TargetProfile(
        name="-".join(ecosystems) + "-generic" if ecosystems else "generic",
        code_check=_primary_test(commands),
        has_ui=caps.has_ui,
        design_md_path="design/DESIGN.md",
        conventions=f"Profil générique synthétisé (rôles: {', '.join(sorted(roles))}).",
        brick_catalog={},
        roles=roles,
        pkg_managers=pkg_managers,
        commands=commands,
    )


def resolve_profile(repo: Path) -> ProfileResolution:
    """Cascade P-14 : ① manifeste → ② curé → ③ inférence → (④ analyse LLM opt-in). 1er qui répond.

    Lève seulement si le repo n'expose AUCUN signal (P-15) — message actionnable."""
    manifest = repo / ".forge" / "profile.toml"
    if manifest.exists():
        return ProfileResolution(TargetProfile.from_manifest(manifest), "manifest")

    # ② curé : réutilise le registre existant si un marqueur curé est reconnu.
    from conductor.onramp.detect import detect_stack

    stack = detect_stack(repo)
    curated = profile_for_stack(stack)
    if curated is not None:
        return ProfileResolution(curated, "curated")

    caps = detect_capabilities(repo)
    if not caps.has_signal:
        raise ValueError(
            f"Aucun signal de stack exploitable dans {repo} (ni manifeste, ni gestionnaire "
            "de paquets, ni commande détectable). Fournis un manifeste opposable "
            "`.forge/profile.toml` (name + [roles] + [commands.<rôle>]) décrivant la stack."
        )
    profile = synthesize_profile(repo, caps)

    # ④ analyse LLM (opt-in) si l'heuristique laisse des rôles sans commande de test.
    if os.environ.get("CONDUCTOR_USE_CLAUDE_ANALYZER") == "1" and _is_incomplete(profile):
        from conductor.harness.profile_analyzer import analyze_profile_with_claude

        analyzed = analyze_profile_with_claude(repo, base=profile)
        if analyzed is not None:
            return ProfileResolution(analyzed, "analyzed")
    return ProfileResolution(profile, "inferred")


def _is_incomplete(profile: TargetProfile) -> bool:
    """Heuristique jugée incomplète si un rôle n'a pas de commande de test."""
    return any(rc.test is None for rc in profile.commands.values()) or not profile.commands


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
