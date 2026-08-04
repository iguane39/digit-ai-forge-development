"""Petits utilitaires texte pour les adapters du harness."""

from __future__ import annotations


def clip(text: str, limit: int) -> str:
    """Tronque `text` à `limit` caractères, en signalant la troncature par une ellipsis."""
    if len(text) <= limit:
        return text
    return text[:limit] + "…"
