"""Text normalisation helpers.

Two levels of normalisation are used throughout the package:

* ``clean_text`` produces the *display* text: Unicode-compatibility folded,
  Arabic-Indic / Persian digits turned into ASCII digits, invisible
  formatting characters and emoji removed. Everything we return to the caller
  (name, address, landmark) is taken from this text, so the shop sees what the
  customer wrote, minus noise.
* ``norm_token`` / ``token_key`` produce *matching* keys: lower-cased, Arabic
  letter variants folded (أ إ آ -> ا, ة -> ه, ى -> ي, Kurdish/Persian letters
  -> Arabic), diacritics and tatweel removed, and the definite article ``ال``
  (or ``al-`` in Latin script) stripped. Keys are only ever compared, never
  shown.
"""

from __future__ import annotations

import re
import unicodedata

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)

_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿­︎️]")

# Harakat, Quranic marks, superscript alef and tatweel.
_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")

_LETTERS = str.maketrans(
    {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ة": "ه", "ى": "ي", "ئ": "ي", "ؤ": "و",
        # Kurdish (Sorani) / Persian letters folded to their Arabic look-alikes
        "ک": "ك", "ی": "ي", "ێ": "ي", "ە": "ه", "ھ": "ه", "ۆ": "و", "ۊ": "و",
        "ڕ": "ر", "ڵ": "ل", "گ": "ك", "ڤ": "ف", "پ": "ب", "چ": "ج", "ژ": "ز",
    }
)

# Word-initial hamza seat (very common in Kurdish: ئاسۆ) behaves like alef.
_INITIAL_YEH_HAMZA = re.compile(r"(?<!\w)ئ")

_EDGE_PUNCT = re.compile(r"^[^\w]+|[^\w]+$")

_LATIN_ARTICLE = re.compile(r"^(?:al|el)-")


def clean_text(text: str) -> str:
    """Return display text: NFKC, ASCII digits, no invisibles, no emoji."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DIGITS)
    text = _INVISIBLE.sub("", text)
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        # So = emoji/pictographs (📞 📍 ☎), Sk = modifiers, Co = private use
        if cat in ("So", "Sk", "Co", "Cs"):
            out.append(" ")
        elif ch == "\t":
            out.append(" ")
        else:
            out.append(ch)
    text = "".join(out)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def is_latin(s: str) -> bool:
    return bool(s) and all(ord(c) < 0x250 for c in s if c.isalpha())


def norm_token(token: str) -> str:
    """Normalise a single token for matching (keeps the definite article)."""
    t = _INITIAL_YEH_HAMZA.sub("ا", token)
    t = _DIACRITICS.sub("", t)
    t = t.translate(_LETTERS).lower()
    return _EDGE_PUNCT.sub("", t)


def strip_article(n: str) -> tuple[str, bool]:
    """Strip ``ال`` / ``al-`` from an already-normalised token.

    Returns ``(key, had_article)``. A bare ``al``/``el`` token (as in
    "al karrada") becomes the empty key, which matchers skip.
    """
    if n in ("al", "el"):
        return "", True
    if n.startswith("ال") and len(n) > 3:
        return n[2:], True
    m = _LATIN_ARTICLE.match(n)
    if m and len(n) > m.end() + 1:
        return n[m.end():], True
    return n, False


def token_key(token: str) -> str:
    return strip_article(norm_token(token))[0]


def prefix_variants(n: str) -> list[str]:
    """Normalised forms of ``n`` with attached Arabic proclitics removed.

    ``ببغداد`` -> ``بغداد``, ``بالبصره`` -> ``البصره``, ``للبصره`` -> ``البصره``,
    ``والكراده`` -> ``الكراده``. The unmodified token always comes first so that
    words that merely *start* with one of these letters (بابل, بغداد) still
    match exactly.
    """
    out = [n]
    if not n or is_latin(n):
        return out
    frontier = [n]
    for _ in range(2):
        nxt = []
        for t in frontier:
            if t.startswith("لل") and len(t) > 4:
                nxt.append("ال" + t[2:])
            if len(t) > 3 and t[0] in "وبلفك":
                nxt.append(t[1:])
        for t in nxt:
            if t not in out:
                out.append(t)
        frontier = nxt
    return out


_TOKEN_SPLIT = re.compile(r"\s+")
_COLON = re.compile(r"\s*[:：=]\s*")


def tokenize(segment: str) -> list[str]:
    """Split a segment into whitespace tokens, with ``:`` as its own token."""
    segment = _COLON.sub(" : ", segment)
    return [t for t in _TOKEN_SPLIT.split(segment.strip()) if t]


def has_digit(s: str) -> bool:
    return any(c.isdigit() for c in s)


def edit_distance_le1(a: str, b: str) -> bool:
    """True if Levenshtein(a, b) <= 1 (cheap special case)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = j = 0
    diff = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        diff += 1
        if diff > 1:
            return False
        if la == lb:
            i += 1
        j += 1
    return diff + (lb - j) + (la - i) <= 1
