"""Iraqi mobile number extraction and validation.

Design rule: never fabricate a number.  Digit groups are only joined across
characters people put *inside* a phone number (spaces, dashes, dots, slashes,
brackets) and never across letters or line breaks.  A group is never cut in
half, padded, or "corrected"; anything that does not canonicalise to exactly
ten digits starting with 7 is reported as invalid instead of returned.
"""

import re
from dataclasses import dataclass, field

# Operator prefixes (second and third digit of 07XX XXX XXXX):
#   75 Korek, 77 Asiacell, 78/79 Zain.  76 exists but is rare -> accepted
#   with a warning.  70-74 are not consumer mobile ranges -> rejected.
VALID_PREFIXES = ("75", "77", "78", "79")
UNCOMMON_PREFIXES = ("76",)

_GROUP = re.compile(r"[0-9]+")
_GAP_OK = re.compile(r"^[ \-./()]{1,3}$")
# Words that are usually followed by a house / alley / block number.
_ADDRESS_NUMBER_WORDS = {
    "دار", "زقاق", "زقاك", "محله", "محلة", "شارع", "عماره", "عمارة", "طابق",
    "شقه", "شقة", "بيت", "بلوك", "قطعه", "قطعة", "مجمع", "house", "street",
    "st", "block", "alley", "building", "apt", "no", "الدار", "الزقاق", "المحله",
    # quantity / size words: 'عدد 2 0770 ...' - the 2 is a quantity
    "عدد", "العدد", "قطعه", "قطع", "حبه", "حبات", "قياس", "القياس", "مقاس", "size", "x", "qty",
}

_MAX_GROUPS_PER_NUMBER = 8
_PREFIX_GROUPS = {"964", "00964", "00", "0964"}


@dataclass
class PhoneMatch:
    number: str  # +9647XXXXXXXXX
    start: int  # span in the line (covers all groups of the number)
    end: int
    uncommon_prefix: bool = False
    adjacent_digits: bool = False


@dataclass
class InvalidPhone:
    raw: str
    reason: str  # too_short | too_long | not_mobile | foreign | unknown_prefix
    start: int = 0
    end: int = 0


@dataclass
class LineResult:
    valid: list = field(default_factory=list)
    invalid: list = field(default_factory=list)
    spans: list = field(default_factory=list)  # every span consumed (valid + invalid)


def canonicalize(digits, had_plus=False):
    """Return (number|None, reason|None, uncommon_prefix: bool).

    ``digits`` is ASCII digits only.  Accepted shapes::

        07XXXXXXXXX  7XXXXXXXXX  9647XXXXXXXXX  96407XXXXXXXXX
        009647XXXXXXXXX  (+ is passed in as had_plus)
    """
    d = digits
    international = had_plus
    if d.startswith("00"):
        d = d[2:]
        international = True
    if d.startswith("964"):
        d = d[3:]
        if d.startswith("0"):  # '+964 0770 ...' - redundant trunk zero
            d = d[1:]
    elif international:
        return None, "foreign", False
    elif d.startswith("0"):
        d = d[1:]
    if not d:
        return None, "too_short", False
    if d[0] != "7":
        return None, "not_mobile", False
    if len(d) < 10:
        return None, "too_short", False
    if len(d) > 10:
        return None, "too_long", False
    if d[:2] in VALID_PREFIXES:
        return "+964" + d, None, False
    if d[:2] in UNCOMMON_PREFIXES:
        return "+964" + d, None, True
    return None, "unknown_prefix", False


def normalize_phone(text):
    """Validate one phone string; return '+9647XXXXXXXXX' or None.

    The whole string must be a single number (separators allowed); use
    ``parse_order`` to find numbers inside a message.
    """
    if not isinstance(text, str):
        raise TypeError("normalize_phone expects str, got %s" % type(text).__name__)
    from .normalize import clean_text

    s = clean_text(text).strip()
    if not s or re.search(r"[^0-9 \-./()+]", s):
        return None
    # same grouping rules as parse_order: '0770123456 7' is not a number
    res = extract_from_line(s)
    if len(res.valid) != 1 or res.invalid or res.valid[0].adjacent_digits:
        return None
    m = res.valid[0]
    if re.search(r"[0-9]", s[:m.start] + s[m.end:]):
        return None
    return m.number


def _glued_to_latin(line, start, end):
    before = line[start - 1] if start > 0 else ""
    after = line[end] if end < len(line) else ""
    return (before.isascii() and before.isalpha()) or (after.isascii() and after.isalpha())


def _runs(line):
    """Group digit groups into runs joined only by in-number separators.

    A short digit group glued to Latin letters is Arabizi or a unit
    ('3li', 'm7md', '100m') and is skipped; a long one ('mob07701234567')
    is still a phone candidate.
    """
    groups = [
        m
        for m in _GROUP.finditer(line)
        if len(m.group()) >= 7 or not _glued_to_latin(line, m.start(), m.end())
    ]
    runs, cur = [], []
    for m in groups:
        if cur and _GAP_OK.match(line[cur[-1].end():m.start()]):
            cur.append(m)
        else:
            if cur:
                runs.append(cur)
            cur = [m]
    if cur:
        runs.append(cur)
    return runs


def _national_len(group):
    g = group
    for prefix in ("00964", "964"):
        if g.startswith(prefix):
            g = g[len(prefix):]
            break
    return len(g[1:] if g.startswith("0") else g)


def _piece(line, run, i, j):
    """Canonicalise groups run[i:j] as one number, applying the grouping rules.

    * a group that already holds 8+ national digits is never glued to its
      neighbours: '0770123456 7' is a 10-digit typo plus a stray digit;
    * a 1-digit group is never inside a multi-group number (except the trunk
      '0' in '+964 0 770 ...');
    * a leading 964 / 00964 / 00 group is part of the number.
    """
    body = run[i:j]
    prefixed = body[0].group() in _PREFIX_GROUPS and len(body) > 1
    if prefixed:
        body = body[1:]
    if len(body) > 1:
        if any(_national_len(m.group()) >= 8 for m in body):
            return None, None, False
        for k, m in enumerate(body):
            if len(m.group()) == 1 and not (prefixed and k == 0 and m.group() == "0"):
                return None, None, False
    digits = "".join(m.group() for m in run[i:j])
    start = run[i].start()
    had_plus = start > 0 and line[start - 1] == "+"
    return canonicalize(digits, had_plus)


def _partition(line, run):
    """Best split of a run into valid numbers and leftover groups.

    Score (lexicographic): most valid numbers, then fewest leftover groups.
    Pieces never split a group.
    """
    n = len(run)
    best = [None] * (n + 1)  # best[k] = (score, pieces) for run[k:]
    best[n] = ((0, 0), [])
    for i in range(n - 1, -1, -1):
        nxt = best[i + 1]
        options = [((nxt[0][0], nxt[0][1] - 1), [("left", i, i + 1)] + nxt[1])]
        for j in range(i + 1, min(n, i + _MAX_GROUPS_PER_NUMBER) + 1):
            number, _, _ = _piece(line, run, i, j)
            if number:
                nxt = best[j]
                options.append(((nxt[0][0] + 1, nxt[0][1]), [("valid", i, j)] + nxt[1]))
        best[i] = max(options, key=lambda o: o[0])
    return best[0][1]


def _looks_like_phone_attempt(digits, had_plus):
    if had_plus or digits.startswith(("0", "7", "9")):
        return len(digits) >= 7
    return False


def _clear_start(line, run, i):
    g = run[i].group()
    return g.startswith(("0", "964")) or (run[i].start() > 0 and line[run[i].start() - 1] == "+")


def _widen(line, s, e):
    """Include a leading '+' and an RTL-artefact trailing '+' in a span."""
    if s > 0 and line[s - 1] == "+":
        s -= 1
    if e < len(line) and line[e] == "+":
        e += 1
    return s, e


def extract_from_line(line):
    """Find valid and invalid phone numbers in one line of clean text."""
    from .normalize import fold

    res = LineResult()
    for run in _runs(line):
        pieces = _partition(line, run)
        valid = [p for p in pieces if p[0] == "valid"]
        if not valid:
            s, e = _widen(line, run[0].start(), run[-1].end())
            digits = "".join(m.group() for m in run)
            had_plus = line[s] == "+"
            if _looks_like_phone_attempt(digits, had_plus):
                _, reason, _ = canonicalize(digits, had_plus)
                if len(run) > 1 and len(digits) - (3 if digits.startswith("964") else 0) in (11, 10):
                    reason = "ambiguous_grouping"
                res.invalid.append(InvalidPhone(line[s:e], reason or "too_long", s, e))
                res.spans.append((s, e))
            continue

        words_before = line[: run[0].start()].split()
        after_address_word = bool(words_before) and fold(words_before[-1]) in _ADDRESS_NUMBER_WORDS
        first_valid = valid[0][1]

        # leftover groups: classify each
        adjacent = {}  # index of valid piece -> list of short neighbours
        big_neighbour = set()
        for k, (kind, i, j) in enumerate(pieces):
            if kind != "left":
                continue
            g = run[i].group()
            s, e = _widen(line, run[i].start(), run[i].end())
            had_plus = s < run[i].start()
            if len(g) >= 7 and _looks_like_phone_attempt(g, had_plus):
                _, reason, _ = canonicalize(g, had_plus)
                res.invalid.append(InvalidPhone(line[s:e], reason or "too_long", s, e))
                res.spans.append((s, e))
                continue
            if i < first_valid and after_address_word and all(
                p[0] == "left" and len(run[p[1]].group()) <= 4 for p in pieces[:k + 1]
            ):
                continue  # 'دار 12 0770...' : house number
            neighbours = [n for n in (k - 1, k + 1) if 0 <= n < len(pieces) and pieces[n][0] == "valid"]
            for n in neighbours:
                if len(g) >= 5:
                    big_neighbour.add(n)
                elif n == k + 1 and _clear_start(line, run, pieces[n][1]):
                    # 'اريد 2 0770 123 4567': the number visibly starts at its
                    # trunk 0 / + / 964, so the 2 cannot belong to it
                    big_neighbour.add(n)
                else:
                    adjacent.setdefault(n, []).append(k)

        for k, (kind, i, j) in enumerate(pieces):
            if kind != "valid":
                continue
            number, _, uncommon = _piece(line, run, i, j)
            s, e = _widen(line, run[i].start(), run[j - 1].end())
            multi_group = (j - i) - (1 if run[i].group() in _PREFIX_GROUPS else 0) > 1
            if k in adjacent and multi_group:
                # '0770 123 4567 8': which digit is the stray one? Don't guess.
                ks = [k] + adjacent[k]
                lo = min(pieces[x][1] for x in ks)
                hi = max(pieces[x][2] for x in ks)
                s2, e2 = _widen(line, run[lo].start(), run[hi - 1].end())
                res.invalid.append(InvalidPhone(line[s2:e2], "ambiguous_grouping", s2, e2))
                res.spans.append((s2, e2))
                continue
            res.valid.append(PhoneMatch(number, s, e, uncommon, k in adjacent or k in big_neighbour))
            res.spans.append((s, e))
    return res
