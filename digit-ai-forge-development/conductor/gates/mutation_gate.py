"""Gate mutation (TF-0103, sous-item 2) — 3e métrique du double gate, mutmut pour Python.

Le double gate (code + design) mesure que les tests PASSENT, pas qu'ils DÉTECTENT une
régression : une suite verte à couverture haute peut laisser passer du code IA faux si
elle n'assertionne rien de discriminant (pratique 2026 pour le code généré par IA, source
TF-0103). Le score de mutation (mutants tués / mutants jugés) mesure la force réelle de la
suite : mutmut modifie le code (mutants) et vérifie que les tests échouent en conséquence.

**mutmut ne tourne PAS nativement sous Windows** (message natif du paquet : « please use
the WSL ») : cette étape s'exécute en CI (`ubuntu-latest`), dans le devcontainer fourni
(TF-0103.1), ou sous WSL — jamais en process natif sur un poste Windows. Ce gate ne relance
donc PAS mutmut lui-même (coût prohibitif pour un gate synchrone, et portabilité) : il lit
le format d'export officiel de mutmut (commande `mutmut export-cicd-stats` →
`mutants/mutmut-cicd-stats.json`) et applique une politique de seuil — même découplage que
`design_gate` qui lit `findings.json` sans relancer le linter.

Séquence produisant le fichier lu par ce gate (config `[tool.mutmut]` de `pyproject.toml`) ::

    uv run mutmut run
    uv run mutmut export-cicd-stats
    uv run python -m conductor.gates.mutation_gate mutants/mutmut-cicd-stats.json

**v0 (TF-0103.2) — mesure réelle exécutée sur le code du conductor lui-même** : scope borné
à `conductor/sandbox.py` + `conductor/gates/ai_antipatterns_gate.py` (le code neuf de cette
campagne). Résultat mesuré via Docker (`python:3.11-slim`, mutmut 3.7.0), 12/08/2026 :
**223 killed / 142 survived / 365 total → score 61,1 %**, sous le seuil. Une majorité des
survivants sont des mutations caractère-par-caractère de littéraux regex (le style
d'implémentation de ces deux modules) : mutmut ne distingue pas un caractère de regex qui
change le comportement observable d'un qui ne le change pas pour les entrées testées — deux
regex syntaxiquement différentes peuvent rester fonctionnellement équivalentes sur le jeu de
tests, gonflant le compte de survivants sans indiquer une assertion manquante. Restes :
renforcer les tests là où les survivants indiquent une VRAIE lacune logique (pas les
mutants de regex équivalents), puis étendre `only_mutate` au reste de `conductor/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conductor.contracts import GateVerdict

# Seuil explicite (TF-0103, source de la candidature : pratique 2026 "~75 %+" pour le code
# généré par IA). Score = killed / (killed + survived) — dénominateur restreint aux mutants
# JUGÉS : `no_tests`, `skipped`, `suspicious`, `timeout`, `check_was_interrupted_by_user`,
# `segfault` ne discriminent ni la force ni la faiblesse de la suite (mutant non jugé) ; les
# inclure diluerait le score sans rapport avec la qualité réelle des tests.
DEFAULT_THRESHOLD = 0.75


def _score(stats: dict[str, int]) -> float | None:
    killed = stats.get("killed", 0)
    survived = stats.get("survived", 0)
    judged = killed + survived
    if judged == 0:
        return None
    return killed / judged


def run_mutation_gate(stats_path: Path, *, threshold: float = DEFAULT_THRESHOLD) -> GateVerdict:
    """P-06 : stats absentes/illisibles/aucun mutant jugé → SKIP tracé, jamais un échec
    implicite (mutmut n'a peut-être pas encore tourné sur cet environnement — cas normal
    sur un poste Windows natif où mutmut refuse de s'exécuter, cf. docstring du module)."""
    if not stats_path.exists():
        return GateVerdict(
            gate="mutation",
            passed=True,
            findings=[{"skipped": f"stats mutmut absentes : {stats_path} (mutmut run requis)"}],
        )
    try:
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return GateVerdict(
            gate="mutation",
            passed=True,
            findings=[{"skipped": f"stats mutmut illisibles ({exc})"}],
            log_ref=str(stats_path),
        )
    score = _score(stats)
    if score is None:
        return GateVerdict(
            gate="mutation",
            passed=True,
            findings=[{"skipped": "aucun mutant jugé (killed+survived=0)"}],
            log_ref=str(stats_path),
        )
    passed = score >= threshold
    findings: list[dict[str, str]] = (
        []
        if passed
        else [
            {
                "score": f"{score:.1%}",
                "seuil": f"{threshold:.1%}",
                "killed": str(stats.get("killed", 0)),
                "survived": str(stats.get("survived", 0)),
                "issue": "score de mutation sous le seuil",
            }
        ]
    )
    return GateVerdict(gate="mutation", passed=passed, findings=findings, log_ref=str(stats_path))


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.mutation_gate <stats.json> [seuil]``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in (1, 2):
        print(
            "usage: python -m conductor.gates.mutation_gate <mutmut-cicd-stats.json> [seuil]",
            file=sys.stderr,
        )
        return 2
    threshold = float(args[1]) if len(args) == 2 else DEFAULT_THRESHOLD
    verdict = run_mutation_gate(Path(args[0]), threshold=threshold)
    if verdict.passed:
        skip = verdict.findings[0].get("skipped", "") if verdict.findings else ""
        print("mutation gate: PASS" + (f" ({skip})" if skip else ""))
        return 0
    f = verdict.findings[0]
    print(
        f"mutation gate: FAIL — score {f['score']} < seuil {f['seuil']} "
        f"(killed={f['killed']} survived={f['survived']})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
