"""Gate de non-régression (do-no-harm, brownfield).

Compare le statut courant des checks à la BASELINE capturée à l'onramp : un check qui était
vert et passe au rouge est une régression bloquante (→ 3 retries puis escalade, comme un gate).
Fonction pure, testable hors-ligne.
"""

from __future__ import annotations

from conductor.contracts import GateVerdict


def evaluate_regression(baseline: dict[str, bool], current: dict[str, bool]) -> GateVerdict:
    """Bloque si un check vert dans `baseline` n'est plus vert dans `current`."""
    regressions = [
        name for name, was_green in baseline.items() if was_green and not current.get(name, False)
    ]
    return GateVerdict(
        gate="regression",
        passed=not regressions,
        findings=[{"check": name, "issue": "vert→rouge"} for name in regressions],
    )
