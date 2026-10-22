"""Text normalisation.

Two layers, kept deliberately separate:

* ``clean_text`` produces the *display* text: invisible formatting characters
  removed, Arabic-Indic / Persian digits turned into ASCII, odd spaces turned
  into plain spaces.  Letters are left exactly as the customer typed them, so
  names and addresses come back in their original spelling.
* ``fold`` produces a *matching key* for one token: harakat/tatweel removed,
  letter variants (hamza forms, ta marbuta, Kurdish/Persian letters) unified and
  Latin case-folded.  It is never shown to anyone.
"""

import re
import unicodedata

# Arabic-Indic (U+0660-0669) and Extended Arabic-Indic / Persian (U+06F0-06F9).
# Only these are converted: Python's \d also matches Devanagari, NKo,
# mathematical digits and more, which have no business in an Iraqi phone.
_DIGITS = {}
for _i in range(10):
    _DIGITS[0x0660 + _i] = str(_i)
    _DIGITS[0x06F0 + _i] = str(_i)

# Unicode "format" characters that copy/paste from Instagram, WhatsApp and
# iOS contacts injects: bidi marks, embeddings, isolates, zero-width chars, BOM.
_INVISIBLE = {
    cp: None
    for cp in (
        list(range(0x200B, 0x2010))  # ZWSP, ZWNJ, ZWJ, LRM, RLM
        + list(range(0x202A, 0x202F))  # LRE RLE PDF LRO RLO
        + list(range(0x2066, 0x206A))  # LRI RLI FSI PDI
        + [0x061C, 0xFEFF, 0x00AD, 0x2060, 0x0640]  # ... and tatweel
    )
}

_SPACES = re.compile(r"[ \t   -   　]+")

_TABLE = dict(_DIGITS)
_TABLE.update(_INVISIBLE)
_TABLE[ord("\r")] = "\n"


def _nfkc_arabic_presentation(text):
    """Expand Arabic presentation forms (e.g. U+FEFB 'ﻻ') to base letters."""
    if not any("ﭐ" <= ch <= "﷿" or "ﹰ" <= ch <= "﻾" for ch in text):
        return text
    out = []
    for ch in text:
        if "ﭐ" <= ch <= "﷿" or "ﹰ" <= ch <= "﻾":
            out.append(unicodedata.normalize("NFKC", ch))
        else:
            out.append(ch)
    return "".join(out)


def _drop_emoji(text):
    if text.isascii():
        return text
    return "".join(
        " " if unicodedata.category(ch) in ("So", "Sk", "Cs", "Co") or ch in "\ufe0f\ufe0e\u20e3" else ch
        for ch in text
    )


def clean_text(text):
    """Display-safe text: invisible chars and emoji removed, digits ASCII.

    Newlines are kept (they separate fields in most DMs); runs of other
    whitespace become one space and every line is stripped.  Letters are
    untouched, so returned names/addresses keep the customer's spelling.
    """
    text = _drop_emoji(_nfkc_arabic_presentation(text).translate(_TABLE))
    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(lines)


# --- matching keys ---------------------------------------------------------

_HARAKAT = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")

_LETTERS = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
        # Kurdish (Sorani) / Persian keyboard letters
        "ک": "ك",
        "ی": "ي",
        "ێ": "ي",
        "ې": "ي",
        "ە": "ه",
        "ھ": "ه",
        "ۆ": "و",
        "ۇ": "و",
        "ڕ": "ر",
        "ڵ": "ل",
        "ڤ": "ف",
        "گ": "ك",
        "پ": "ب",
        "چ": "ج",
        "ژ": "ز",
    }
)

# Characters stripped from the edges of a token before matching.
_EDGE_PUNCT = " \t.,،؛;:!?؟'\"()[]{}<>«»/\\|-_=+*~`^…•·"


def fold(token):
    """Matching key for a single token (or a short phrase)."""
    token = _HARAKAT.sub("", token)
    token = token.translate(_LETTERS).casefold()
    token = token.strip(_EDGE_PUNCT)
    # كربلاء -> كربلا, سامراء -> سامرا : a trailing hamza is very often dropped
    if token.endswith("ء"):
        token = token[:-1]
    return token


def tokens(text):
    """Split display text on whitespace."""
    return text.split()


def fold_tokens(text):
    return [fold(t) for t in text.split()]


_ARABIC_LETTER = re.compile("[ء-يٮ-ۓەۺ-ۿ]")
_LATIN_LETTER = re.compile("[A-Za-z]")


def has_letters(text):
    return bool(_ARABIC_LETTER.search(text) or _LATIN_LETTER.search(text))


def is_latin_letter(ch):
    return bool(ch) and ("a" <= ch.lower() <= "z")
