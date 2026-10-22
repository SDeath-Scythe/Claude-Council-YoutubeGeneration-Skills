"""Iraqi mobile number extraction.

Iraqi mobiles have a 10-digit national number starting with 7 (07XX XXX XXXX
domestically, +964 7XX XXX XXXX internationally). Customers write them with
spaces, dashes, dots, a +964 / 00964 / 964 prefix, a stray 0 after the country
code, or Arabic-Indic digits (already converted by ``clean_text``).

Digit groups separated only by spacing punctuation are joined and tried as a
number, so "0770 123 4567" and "+964 (0) 770-123-4567" both work, while house
numbers like "دار 12" next to a phone do not get glued onto it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Second digit of the national number for the mobile operators:
# 75 Korek, 77 Asiacell, 78/79 Zain.
KNOWN_OPERATOR_PREFIXES = ("75", "77", "78", "79")

# A digit group must not be glued to Latin letters ("jame3", "ra8mi" in
# Arabizi use digits as letters). Arabic letters glued to digits are fine
# ("رقمي07701234567").
_GROUP = re.compile(r"(?<![A-Za-z])\d+(?![A-Za-z])")
_GAP = re.compile(r"[ \-.()+/]{0,4}")
_MAX_DIGITS = 15


@dataclass(frozen=True)
class PhoneMatch:
    start: int
    end: int
    e164: str
    raw: str
    known_operator: bool


@dataclass(frozen=True)
class BadNumber:
    start: int
    end: int
    raw: str


def normalize_iraqi_mobile(digits: str) -> str | None:
    """Return +9647XXXXXXXXX for a valid Iraqi mobile digit string, else None."""
    d = digits
    if d.startswith("00964"):
        d = d[5:]
    elif d.startswith("964"):
        d = d[3:]
    if d.startswith("0"):
        d = d[1:]
    if len(d) == 10 and d[0] == "7":
        return "+964" + d
    return None


def find_phones(text: str) -> tuple[list[PhoneMatch], list[BadNumber]]:
    groups = list(_GROUP.finditer(text))
    joinable = [
        i + 1 < len(groups) and _GAP.fullmatch(text, groups[i].end(), groups[i + 1].start()) is not None
        for i in range(len(groups))
    ]

    phones: list[PhoneMatch] = []
    used: set[int] = set()
    i = 0
    while i < len(groups):
        digits = ""
        found = None
        j = i
        while j < len(groups):
            digits += groups[j].group()
            if len(digits) > _MAX_DIGITS:
                break
            e164 = normalize_iraqi_mobile(digits)
            if e164:
                found = (j, e164)
                break
            if not joinable[j]:
                break
            j += 1
        if found:
            j, e164 = found
            start, end = groups[i].start(), groups[j].end()
            if start > 0 and text[start - 1] == "+":
                start -= 1
            phones.append(PhoneMatch(start, end, e164, text[start:end], e164[4:6] in KNOWN_OPERATOR_PREFIXES))
            used.update(range(i, j + 1))
            i = j + 1
        else:
            i += 1

    # Long digit runs that are not valid mobiles: probably a mistyped phone.
    bad: list[BadNumber] = []
    i = 0
    while i < len(groups):
        if i in used:
            i += 1
            continue
        j = i
        while joinable[j] and j + 1 not in used and j + 1 < len(groups):
            j += 1
        digits = "".join(g.group() for g in groups[i : j + 1])
        if len(digits) >= 8:
            start, end = groups[i].start(), groups[j].end()
            if start > 0 and text[start - 1] == "+":
                start -= 1
            bad.append(BadNumber(start, end, text[start:end]))
        i = j + 1
    return phones, bad
