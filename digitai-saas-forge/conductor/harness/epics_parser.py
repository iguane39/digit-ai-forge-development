"""Parser tolérant de epics.md → list[Story] (métadonnées seules).

Machine à états ligne par ligne. N'extrait QUE des métadonnées plates (id, epic, title,
acceptance, gh_issue) — ne reconstruit PAS le graphe de dépendances (BAD le fait, décision 01).
Fonction pure, déterministe, sans réseau. Fallback : aucune story → [].
"""

from __future__ import annotations

import re

from conductor.contracts import Story

_EPIC_RE = re.compile(r"^#+\s*(?:epic|épique)\s*(\d+)\b[:\-\s]*(.*)$", re.IGNORECASE)
_STORY_RE = re.compile(
    r"^#+\s*(?:story|récit|user story)?\s*(\d+\.\d+)\b[:\-\s]*(.*)$", re.IGNORECASE
)
_GH_RE = re.compile(r"\*\*\s*GH Issue\s*:\s*\*\*\s*#?\s*(\d+)", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_HEADING_RE = re.compile(r"^\s*(?:#+|\*\*)")
_ACCEPTANCE_RE = re.compile(r"acceptance|critères?\s+d['’]acceptation", re.IGNORECASE)


def parse_epics(text: str) -> list[Story]:
    """Extrait les stories (sections de epics.md). Renvoie [] si aucune story `X.Y`."""
    stories: list[Story] = []
    current: dict[str, object] | None = None
    epic_label = ""
    in_acceptance = False

    def _flush() -> None:
        if current is not None:
            acceptance = current["acceptance"]
            assert isinstance(acceptance, list)
            gh_issue = current["gh_issue"]
            assert gh_issue is None or isinstance(gh_issue, int)
            stories.append(
                Story(
                    id=str(current["id"]),
                    epic=str(current["epic"]),
                    title=str(current["title"]),
                    acceptance=acceptance,
                    gh_issue=gh_issue,
                )
            )

    for raw in text.splitlines():
        line = raw.rstrip()
        story_m = _STORY_RE.match(line)
        if story_m:
            _flush()
            current = {
                "id": story_m.group(1),
                "title": story_m.group(2).strip(),
                "epic": epic_label,
                "acceptance": [],
                "gh_issue": None,
            }
            in_acceptance = False
            continue
        epic_m = _EPIC_RE.match(line)
        if epic_m:
            _flush()
            current = None
            epic_label = epic_m.group(2).strip() or f"epic-{epic_m.group(1)}"
            in_acceptance = False
            continue
        if current is None:
            continue
        gh_m = _GH_RE.search(line)
        if gh_m:
            current["gh_issue"] = int(gh_m.group(1))
            continue
        if _HEADING_RE.match(line):
            in_acceptance = bool(_ACCEPTANCE_RE.search(line))
            continue
        if in_acceptance:
            bullet_m = _BULLET_RE.match(line)
            if bullet_m:
                acceptance = current["acceptance"]
                assert isinstance(acceptance, list)
                acceptance.append(bullet_m.group(1))

    _flush()
    return stories
