"""Iraqi mobile number extraction and normalisation.

An Iraqi mobile number is ``7`` + 9 digits after the country code 964 (national
format ``07XX XXX XXXX``). The third digit of the national number is 3-9;
075 (Korek), 077 (Asiacell) and 078/079 (Zain) are by far the most common,
so numbers on other 07x prefixes are accepted but flagged for review.

Accepted spellings (after Arabic-Indic digits are converted):
``07701234567``, ``7701234567``, ``+9647701234567``, ``009647701234567``,
``9647701234567``, ``+964 07701234567`` (redundant trunk zero), with any mix
of spaces, dashes, dots and parentheses between digit groups.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import clean_text

COMMON_PREFIXES = frozenset({"75", "77", "78", "79"})

# A run of digits possibly broken by spaces / dashes / dots / parentheses.
_RUN = re.compile(r"\+?\(?\d[\d \-.()]*\d\)?|\+?\d")
_GROUP = re.compile(r"\+?\d+")


@dataclass(frozen=True)
class PhoneHit:
    number: str  # E.164, e.g. +9647701234567; "" for invalid hits
    raw: str
    start: int
    end: int
    problem: str | None = None  # None for valid numbers


def normalize_phone(raw: str) -> str | None:
    """Return the E.164 form (+9647XXXXXXXXX) of an Iraqi mobile number, or None."""
    raw = clean_text(raw).strip()
    plus = raw.startswith("+")
    d = re.sub(r"\D", "", raw)
    if d.startswith("00964"):
        d = d[5:]
    elif d.startswith("964") and len(d) >= 12:
        d = d[3:]
    elif plus:
        return None  # another country code
    if d.startswith("0"):
        d = d[1:]
    if len(d) == 10 and d[0] == "7" and d[1] in "3456789":
        return "+964" + d
    return None


def is_common_prefix(e164: str) -> bool:
    return e164[4:6] in COMMON_PREFIXES


def _looks_like_phone_attempt(digits: str, plus: bool) -> str | None:
    """Classify a digit string that failed validation. None = not a phone."""
    n = len(digits)
    if plus and not digits.startswith("964"):
        return "non_iraqi" if n >= 8 else None
    if digits.startswith("00") and not digits.startswith("00964") and n >= 10:
        return "non_iraqi"
    if digits.startswith(("964", "00964")) and n >= 9:
        return "wrong_length"
    if digits.startswith("07") and 9 <= n <= 13:
        return "wrong_length"
    if digits.startswith("7") and 9 <= n <= 11:
        return "wrong_length"
    if digits.startswith("0") and 9 <= n <= 11:
        return "not_mobile"  # landline (e.g. Baghdad 01...) or garbage
    return None


def extract_phones(text: str) -> list[PhoneHit]:
    """Find every phone-like number in ``text`` (already ``clean_text``-ed).

    Valid hits have ``problem is None``. Invalid ones (wrong length, foreign,
    landline) are returned too so the caller can warn instead of silently
    dropping a number the customer clearly meant as their phone.
    """
    hits: list[PhoneHit] = []
    for run in _RUN.finditer(text):
        groups = [(g.group(), run.start() + g.start(), run.start() + g.end())
                  for g in _GROUP.finditer(run.group())]
        consumed = [False] * len(groups)
        i = 0
        while i < len(groups):
            found = None
            digits = ""
            for j in range(i, len(groups)):
                digits += groups[j][0].lstrip("+")
                if len(digits) > 15:
                    break
                candidate = ("+" if groups[i][0].startswith("+") else "") + digits
                number = normalize_phone(candidate)
                if number:
                    found = (j, number)
                    break
            if found:
                j, number = found
                start, end = groups[i][1], groups[j][2]
                hits.append(PhoneHit(number, text[start:end], start, end))
                for k in range(i, j + 1):
                    consumed[k] = True
                i = j + 1
            else:
                i += 1
        # Report leftover digit groups that look like a botched phone number.
        k = 0
        while k < len(groups):
            if consumed[k]:
                k += 1
                continue
            m = k
            while m + 1 < len(groups) and not consumed[m + 1]:
                m += 1
            plus = groups[k][0].startswith("+")
            digits = "".join(g[0].lstrip("+") for g in groups[k:m + 1])
            problem = _looks_like_phone_attempt(digits, plus)
            if problem:
                start, end = groups[k][1], groups[m][2]
                hits.append(PhoneHit("", text[start:end], start, end, problem))
            k = m + 1
    hits.sort(key=lambda h: h.start)
    return hits
