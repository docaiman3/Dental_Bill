"""Helpers for correcting legacy text corruption in imported billing data."""

from __future__ import annotations

REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("ā", "ä"),
    ("ū", "ü"),
    ("ō", "ö"),
    ("Ā", "Ä"),
    ("Ū", "Ü"),
    ("Ō", "Ö"),
)


def normalize_umlauts(text: str | None) -> str | None:
    """Map legacy macron substitutions back to German umlauts."""
    if text is None:
        return None

    normalized = text
    for bad, good in REPLACEMENTS:
        normalized = normalized.replace(bad, good)
    return normalized
