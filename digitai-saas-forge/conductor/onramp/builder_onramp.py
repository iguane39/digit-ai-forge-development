"""BuilderOnramp — bretelle brownfield « branche B » (B-standard).

Pour une stack non-FastAPI (1ᵉʳ profil : node-ts), résout le TargetProfile de la stack,
normalise vers le contrat (DESIGN.md), capture la baseline via le code_check du profil, et
DÉCLARE la dégradation (profil synthétisé, catalogue de briques vide, harness à fournir).
Ne migre pas le code vers FastAPI : on hisse au standard DANS la stack d'origine.
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.gates.code_gate import CommandRunner
from conductor.gates.design_gate import DesignLinter
from conductor.onramp.analyzer import Analyzer
from conductor.onramp.base import Substrate
from conductor.onramp.defaults import DEFAULT_DESIGN_MD
from conductor.onramp.detect import detect_stack, has_ci
from conductor.onramp.no_onramp import baseline_notes, capture_baseline
from conductor.profiles import TargetProfile, profile_for_stack


class BuilderOnramp:
    """Branche B : hisse une stack non-FastAPI au contrat cible (profil synthétisé/injecté).

    Profil résolu par la cascade générique (``resolve_profile``) et **injecté** par
    ``select_onramp`` pour une stack quelconque (P-14). Sans injection, comportement historique :
    résolution par marqueur curé (node-ts)."""

    def __init__(
        self,
        *,
        profile: TargetProfile | None = None,
        confidence: str = "inferred",
        code_runner: CommandRunner | None = None,
        design_linter: DesignLinter | None = None,
        analyzer: Analyzer | None = None,
    ) -> None:
        self._profile = profile
        self._confidence = confidence
        self._code_runner = code_runner
        self._design_linter = design_linter
        self._analyzer: Analyzer | None = analyzer

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        repo = dest
        if self._profile is not None:
            profile, confidence = self._profile, self._confidence
        else:  # historique : résolution par marqueur curé (node-ts)
            stack = detect_stack(repo)
            resolved = profile_for_stack(stack)
            if resolved is None or stack == "fastapi":
                raise ValueError(
                    f"BuilderOnramp : stack '{stack}' non gérée par un profil dédié dans {repo} "
                    "(FastAPI relève de NoOnramp/AdapterOnramp ; passer un profil résolu pour une "
                    "stack quelconque)."
                )
            profile, confidence = resolved, "curated"

        notes: list[str] = [
            f"Profil '{profile.name}' synthétisé (confiance : {confidence}) : contrat hissé dans "
            "la stack d'origine (B-standard).",
            "Catalogue de briques vide pour cette stack (à enrichir).",
        ]

        design_md = repo / profile.design_md_path
        if profile.has_ui and not design_md.exists():
            design_md.parent.mkdir(parents=True, exist_ok=True)
            design_md.write_text(DEFAULT_DESIGN_MD, encoding="utf-8")
            notes.append("DESIGN.md créé par normalisation (à compléter).")
        if not has_ci(repo):
            notes.append("Harness CI absent : gate code à fournir pour cette stack.")

        # lazy : évite un cycle d'import (harness.analyzer → onramp.analyzer ← onramp.__init__).
        from conductor.harness.resolve import resolve_analyzer

        analyzer: Analyzer = self._analyzer or resolve_analyzer()
        arch_map = analyzer.analyze(repo)
        baseline = capture_baseline(
            repo, profile, code_runner=self._code_runner, design_linter=self._design_linter
        )
        notes.extend(baseline_notes(baseline))
        return Substrate(
            repo_path=repo,
            profile=profile,
            design_md_path=design_md,
            baseline=baseline,
            arch_map=arch_map,
            declared_degradation=notes,
            profile_confidence=confidence,
        )
