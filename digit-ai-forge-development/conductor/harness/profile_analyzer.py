"""④ Analyse LLM (opt-in) du profil — complète l'inférence heuristique quand elle est incomplète.

Derrière ``CONDUCTOR_USE_CLAUDE_ANALYZER=1`` (garde côté ``resolve_profile``). Réutilise le
harness ``claude_cli`` : on demande au CLI de proposer, pour l'arbre du repo, des commandes
test/build/lint par rôle + ``has_ui``. La sortie est **validée pydantic** puis **fusionnée** dans
le profil synthétisé (on ne remplit que les trous — jamais d'écrasement d'une commande sûre).
Sur toute erreur (CLI indispo, JSON invalide) → ``None`` : l'appelant retombe sur l'inférence ③.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ValidationError

from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.profiles import RoleCommands, TargetProfile, _primary_test

_PROMPT = (
    "Analyse l'arbre de ce dépôt et propose, en JSON STRICT, les commandes de test/build/lint "
    "par rôle et si une UI est présente. Format : un objet avec `has_ui` (bool) et `commands` "
    "(objet rôle -> objet avec `test`/`build`/`lint`). "
    "Rôles connus : {roles}. Réponds UNIQUEMENT le JSON, sans texte autour."
)


class _RoleAnalysis(BaseModel):
    test: str | None = None
    build: str | None = None
    lint: str | None = None


class _Analysis(BaseModel):
    has_ui: bool | None = None
    commands: dict[str, _RoleAnalysis] = {}


def analyze_profile_with_claude(
    repo: Path, *, base: TargetProfile, cli: CliRunner | None = None
) -> TargetProfile | None:
    """Complète ``base`` via le CLI Claude. Renvoie un TargetProfile enrichi, ou None si échec."""
    runner = cli or SubprocessClaudeCli()
    try:
        raw = runner.run(_PROMPT.format(roles=", ".join(sorted(base.roles)) or "app"), repo)
        analysis = _Analysis.model_validate_json(_json_slice(raw))
    except (RuntimeError, ValidationError, ValueError):
        return None

    merged: dict[str, RoleCommands] = dict(base.commands)
    for role, found in analysis.commands.items():
        current = merged.get(role, RoleCommands())
        merged[role] = RoleCommands(
            test=current.test or found.test,  # ne remplit que les trous
            build=current.build or found.build,
            lint=current.lint or found.lint,
        )
    has_ui = base.has_ui or bool(analysis.has_ui)
    return base.model_copy(
        update={"commands": merged, "code_check": _primary_test(merged), "has_ui": has_ui}
    )


def _json_slice(text: str) -> str:
    """Extrait le 1ᵉʳ objet JSON d'une réponse (tolère un éventuel texte autour)."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("réponse LLM sans objet JSON")
    return text[start : end + 1]
