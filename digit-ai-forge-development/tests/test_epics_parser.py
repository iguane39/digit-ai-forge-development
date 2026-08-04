"""Parser epics.md → list[Story] : métadonnées seules, tolérant, fallback []."""

from __future__ import annotations

from conductor.harness.epics_parser import parse_epics

_SAMPLE = """# Epic 6 : Authentification

## Story 6.1 : Connexion SSO
**GH Issue:** #142
### Acceptance Criteria
- L'utilisateur se connecte via le fournisseur SSO
- Un échec affiche un message clair

## Story 6.2 : Déconnexion
### Critères d'acceptation
- La session est invalidée côté serveur
"""


def test_parse_two_stories_with_acceptance() -> None:
    stories = parse_epics(_SAMPLE)
    assert [s.id for s in stories] == ["6.1", "6.2"]
    assert stories[0].title == "Connexion SSO"
    assert stories[0].gh_issue == 142
    assert "fournisseur SSO" in stories[0].acceptance[0]
    assert len(stories[0].acceptance) == 2
    assert stories[1].acceptance == ["La session est invalidée côté serveur"]


def test_story_without_acceptance_section() -> None:
    text = "# Epic 1\n## Story 1.1 : Sans critères\n"
    stories = parse_epics(text)
    assert stories[0].id == "1.1"
    assert stories[0].acceptance == []


def test_epic_id_not_taken_for_story() -> None:
    # "Epic 6" (sans point) ne doit pas devenir une story.
    assert parse_epics("# Epic 6 : Titre\n") == []


def test_empty_or_prose_yields_empty() -> None:
    assert parse_epics("") == []
    assert parse_epics("Juste de la prose sans story numérotée.\n") == []


def test_epic_label_attached_to_story() -> None:
    stories = parse_epics(_SAMPLE)
    assert "Authentification" in stories[0].epic


from pathlib import Path  # noqa: E402

from conductor.harness.bmad_planner import ClaudeCliBmadPlanner  # noqa: E402
from conductor.onramp.base import Substrate  # noqa: E402
from conductor.profiles import FASTAPI_SAAS  # noqa: E402


class _WritingCli:
    """Fake CliRunner : écrit un epics.md échantillon dans planning-artifacts au déclenchement."""

    def __init__(self, body: str) -> None:
        self._body = body

    def run(self, prompt: str, cwd: Path) -> str:
        planning = cwd / "_bmad-output" / "planning-artifacts"
        planning.mkdir(parents=True, exist_ok=True)
        (planning / "epics.md").write_text(self._body, encoding="utf-8")
        return "ok"


def _substrate(tmp: Path) -> Substrate:
    return Substrate(repo_path=tmp, profile=FASTAPI_SAAS, design_md_path=tmp / "DESIGN.md")


def test_planner_populates_stories(tmp_path: Path) -> None:
    plan = ClaudeCliBmadPlanner(cli=_WritingCli(_SAMPLE)).plan(_substrate(tmp_path))
    assert [s.id for s in plan.stories] == ["6.1", "6.2"]
    assert plan.hitl1_approved is False


def test_planner_unparseable_epics_yields_empty_stories(tmp_path: Path) -> None:
    plan = ClaudeCliBmadPlanner(cli=_WritingCli("prose sans story")).plan(_substrate(tmp_path))
    assert plan.stories == []  # fallback : juge pass-through, pas de régression
