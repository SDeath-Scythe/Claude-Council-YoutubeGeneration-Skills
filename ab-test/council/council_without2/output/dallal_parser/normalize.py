"""Text cleanup and matching keys.

Two representations of a message are used throughout the parser:

* ``clean`` text: what we return to callers (names, addresses). Digits are
  converted to ASCII, Arabic diacritics/tatweel, invisible marks and emoji are
  removed, but spelling (hamza forms, taa marbuta, ...) is preserved.
* ``key`` text: a matching form derived from ``clean`` by a strictly
  one-character-to-one-character mapping (letter variants folded, Latin
  lowercased). Because the mapping is 1:1, an index into ``key`` is also a
  valid index into ``clean``, so we can match on ``key`` and slice ``clean``.
"""

from __future__ import annotations

import re
import unicodedata

_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

# Harakat, Quranic marks, superscript alef, tatweel.
_REMOVE = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
# Zero-width / bidi control characters and emoji joiners / variation selectors.
_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿︎️­]")

# Folding used for the matching key only. Every value is a single character.
_KEY_MAP = {
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ة": "ه", "ە": "ه", "ھ": "ه",
    "ى": "ي", "ی": "ي", "ې": "ي", "ێ": "ي", "ئ": "ي",
    "ؤ": "و", "ۆ": "و",
    "ک": "ك", "گ": "ك",
    "ڤ": "ف", "پ": "ب", "چ": "ج", "ژ": "ز",
    "ڕ": "ر", "ڵ": "ل",
    "’": "'", "‘": "'", "`": "'",
}


def _symbol_to_space(ch: str) -> str:
    cat = unicodedata.category(ch)
    # So = emoji / pictographs (📞 📍 👤 ☎), Cs/Co = surrogates / private use.
    if cat in ("So", "Cs", "Co"):
        return " "
    return ch


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DIGITS)
    text = _INVISIBLE.sub("", text)
    text = _REMOVE.sub("", text)
    text = "".join(_symbol_to_space(c) for c in text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    return text


def _key_char(ch: str) -> str:
    mapped = _KEY_MAP.get(ch)
    if mapped is not None:
        return mapped
    low = ch.lower()
    return low if len(low) == 1 else ch


def make_key(clean: str) -> str:
    """Matching form of already-cleaned text (same length as the input)."""
    return "".join(_key_char(c) for c in clean)


def norm(phrase: str) -> str:
    """Normalize a vocabulary phrase the same way message text is keyed."""
    return make_key(clean_text(phrase)).strip()


_ARABIC = re.compile("[؀-ۿ]")


def has_arabic(text: str) -> bool:
    return bool(_ARABIC.search(text))
