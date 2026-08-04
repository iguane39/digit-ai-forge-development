"""clip : tronque proprement avec ellipsis (messages d'erreur lisibles)."""

from __future__ import annotations

from conductor.harness._text import clip


def test_clip_short_unchanged() -> None:
    assert clip("court", 100) == "court"


def test_clip_long_adds_ellipsis() -> None:
    out = clip("x" * 50, 10)
    assert out == "x" * 10 + "…"


def test_clip_exact_unchanged() -> None:
    assert clip("x" * 10, 10) == "x" * 10
