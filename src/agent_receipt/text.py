"""Tiny text helpers. German umlauts fold so regexes stay ASCII."""

from __future__ import annotations

_FOLD = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
    }
)


def fold(text: str) -> str:
    return str(text or "").translate(_FOLD)
