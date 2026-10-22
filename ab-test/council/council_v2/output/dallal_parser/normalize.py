"""Matching-only normalisation with an index map back to the original text (D2).

``fold(text)`` returns ``(norm, omap)`` where ``norm`` is a folded copy used for
all matching and ``omap[i]`` is the index in the original string of the
character that produced ``norm[i]``.  Ignorable characters (tashkeel, tatweel,
zero-width and bidi controls, variation selectors) are DROPPED, so stylised
spellings such as ``بـغـداد`` or ``البَصْرة`` match the gazetteer, and a bidi
mark inside a phone number does not break the number.  Emoji and other symbols
become spaces (word boundaries).  Output text (name, address) is always sliced
from the original string through ``omap``.
"""
import unicodedata

_DIGITS = {}
for _i in range(10):
    _DIGITS[chr(0x0660 + _i)] = str(_i)  # Arabic-Indic
    _DIGITS[chr(0x06F0 + _i)] = str(_i)  # Persian / Urdu

_FOLD = {
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    "ة": "ه", "ھ": "ه", "ہ": "ه", "ۀ": "ه", "ە": "ه",
    "ى": "ي", "ی": "ي", "ئ": "ي", "ێ": "ي", "ې": "ي",
    "ؤ": "و", "ۆ": "و", "ۇ": "و", "ۋ": "و",
    "گ": "ك", "ک": "ك", "ڪ": "ك",
    "چ": "ج", "پ": "ب", "ڤ": "ف", "ڵ": "ل", "ڕ": "ر",
}


def _is_ignorable(cp):
    return (0x064B <= cp <= 0x065F or cp == 0x0670 or cp == 0x0640
            or 0x06D6 <= cp <= 0x06ED
            or 0x200B <= cp <= 0x200F or 0x202A <= cp <= 0x202E
            or 0x2066 <= cp <= 0x2069 or cp in (0xFEFF, 0x00AD, 0x2060)
            or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF
            or 0x1F3FB <= cp <= 0x1F3FF)


_NEWLINES = {"\n", " ", " ", "\x0b", "\x0c", "\x85"}


def _fold_char(c):
    """Fold one (already NFKC'd) character; returns a str of length 0 or 1."""
    cp = ord(c)
    if _is_ignorable(cp):
        return ""
    if c in _DIGITS:
        return _DIGITS[c]
    if c in _FOLD:
        return _FOLD[c]
    if c in _NEWLINES:
        return "\n"
    if c.isspace():
        return " "
    if c.isascii():
        return c.lower()
    cat = unicodedata.category(c)
    if cat in ("So", "Sk", "Cs", "Co", "Cn", "Cc", "Cf"):
        return " "
    if cat.startswith("M"):  # stray combining marks
        return ""
    if c.isalpha() and 0x00C0 <= cp <= 0x024F:  # accented Latin -> base letter
        base = "".join(ch for ch in unicodedata.normalize("NFKD", c)
                       if not unicodedata.category(ch).startswith("M"))
        return (base[:1] or c).lower()
    low = c.lower()
    return low if len(low) == 1 else c


def fold(text):
    """Return (norm, omap) for ``text``."""
    out = []
    omap = []
    n = len(text)
    for idx, ch in enumerate(text):
        if ch == "\r":
            if idx + 1 < n and text[idx + 1] == "\n":
                continue
            out.append("\n")
            omap.append(idx)
            continue
        if ch in "'\u2019" and 0 < idx < n - 1 and text[idx - 1].isascii() and text[idx - 1].isalpha() \
                and text[idx + 1].isascii() and text[idx + 1].isalpha():
            continue  # I'm, don't: keep the Latin word whole
        nf = unicodedata.normalize("NFKC", ch) if ord(ch) > 0x7F else ch
        for c in nf:
            f = _fold_char(c)
            if f:
                out.append(f)
                omap.append(idx)
    return "".join(out), omap


def fold_simple(text):
    """Folded text only (for building lookup tables)."""
    return fold(text)[0]


def latin_skeleton(word):
    """Spelling-tolerant key for Latin words: karrada=karada, mansoor=mansour,
    basrah=basra, diwaniyah=diwaniya."""
    w = "".join(ch for ch in word.lower() if ch.isalpha())
    for a, b in (("oo", "u"), ("ou", "u"), ("ee", "i"), ("iy", "i"), ("ie", "i")):
        w = w.replace(a, b)
    res = []
    for ch in w:
        if not res or res[-1] != ch:
            res.append(ch)
    w = "".join(res)
    if len(w) > 3 and w.endswith("h") and w[-2] in "aeiou":
        w = w[:-1]
    return w


def is_arabic_letter(c):
    return "؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ" or "ࢠ" <= c <= "ࣿ"


def is_latin_letter(c):
    return c.isalpha() and c.isascii()


def squeeze(s):
    return " ".join(s.split())
