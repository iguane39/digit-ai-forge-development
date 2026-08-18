"""ClaudeCliSpecReviewer — revue de conformité au spec par un sous-agent `claude`.

Confronte les critères d'acceptation d'une story au diff de sa PR. Renvoie un SpecVerdict
(under-build bloquant, over-build consultatif). En cas d'échec d'interprétation (erreur runner ou
JSON invalide), ne bloque pas — do-no-harm — mais rend un verdict **`indecis` MOTIVÉ** (TF-0375) :
un `passed=True` muet se lit « conforme », et c'est exactement ce qui a permis à cat-dev-03 de
rester « jamais démontré sur produit réel » sans que personne s'en aperçoive.
"""

from __future__ import annotations

import json
from pathlib import Path

from conductor.contracts import SpecVerdict, Story, StoryOutcome
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli

_PROMPT = (
    "Tu es un reviewer de CONFORMITÉ AU SPEC. Story : « {title} ». Critères d'acceptation :\n"
    "{criteria}\n"
    "Confronte le diff de la PR ({pr_url}) à ces critères. Réponds UNIQUEMENT par un objet JSON : "
    '{{"findings": [{{"kind": "under-build"|"over-build", "criterion": "...", '
    '"detail": "...", "severity": "faible|moyenne|élevée"}}]}}. '
    "under-build = critère non tenu ; over-build = comportement non demandé. Aucun texte hors JSON."
)


class ClaudeCliSpecReviewer:
    """Implémente SpecComplianceReviewer : revue réelle via le CLI `claude`."""

    def __init__(self, *, runner: CliRunner | None = None) -> None:
        self._runner: CliRunner = runner or SubprocessClaudeCli()

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> SpecVerdict:
        criteria = "\n".join(f"- {c}" for c in story.acceptance) or "- (aucun critère listé)"
        prompt = _PROMPT.format(title=story.title, criteria=criteria, pr_url=outcome.pr_url or "")
        try:
            raw = self._runner.run(prompt, cwd)
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("réponse non-objet")
            findings = data.get("findings", [])
            if not isinstance(findings, list):
                raise ValueError("findings non-liste")
        except (RuntimeError, ValueError, json.JSONDecodeError) as erreur:
            # TF-0375 — do-no-harm CONSERVÉ (on ne bloque pas sur un juge muet), silence SUPPRIMÉ.
            # Avant : `SpecVerdict(passed=True)`, indistinguable d'une story conforme. C'est ce
            # qui permet à un gate de « n'avoir jamais été démontré » sans que personne le voie.
            return SpecVerdict.indecis(
                f"le reviewer de conformité n a pas rendu de verdict exploitable "
                f"({type(erreur).__name__} : {erreur}) — la story n est PAS déclarée conforme, "
                f"elle est déclarée NON JUGÉE"
            )
        norm = [{str(k): str(v) for k, v in f.items()} for f in findings if isinstance(f, dict)]
        return SpecVerdict.from_findings(norm)
