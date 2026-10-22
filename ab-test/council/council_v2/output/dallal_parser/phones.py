"""Strict Iraqi-mobile grammar, no repair (D3).

Works on the folded copy (all digits already ASCII).  A linear scanner finds
digit *groups*; groups join into a *run* only across a short separator
(space, dash, dot, parenthesis, slash; at most 3 chars, never a newline),
with an optional leading ``+``.  Runs are segmented only at group boundaries.

Accepted forms (after removing separators):
  07[3-9]XXXXXXXX            national
  7[3-9]XXXXXXXX             bare 10 digits
  (+|00)?9647[3-9]XXXXXXXX   international
  (+|00)?96407[3-9]XXXXXXXX  redundant trunk 0 -> accepted + phone_trunk_zero_removed
Nothing is ever trimmed, padded or guessed.
"""
import re

_RE_NAT = re.compile(r"07[3-9]\d{8}")
_RE_BARE = re.compile(r"7[3-9]\d{8}")
_RE_INTL = re.compile(r"7[3-9]\d{8}")
_RE_INTL_TRUNK = re.compile(r"07[3-9]\d{8}")
_RE_BAD_PREFIX = re.compile(r"0?7[0-2]\d{8}")
# Iraqi landlines: Baghdad 01 + 7 digits; other governorates 0 + 2-digit area + 6-7 digits
_RE_LANDLINE = re.compile(r"0[1-6]\d{7,8}")
# a phone attempt with letter look-alikes (O for 0, l/I for 1): never repaired
_RE_LETTER_TYPO = re.compile(r"(?<![0-9a-z])\+?[0-9oli]{10,14}(?![0-9a-z])")

_SEPS = set(" -.()/_")
MAX_DIGITS = 17  # longest accepted form: 00 964 0 7XX XXX XXXX
_VALID_LENGTHS = {10, 11, 13, 14, 15, 16}  # 7XXXXXXXXX, 07…, 9647…, 96407…, 009647…, 0096407…
MIN_PHONELIKE = 9  # runs with >= this many digits are treated as phone attempts


class PhoneHit:
    """A span of the folded text that is a phone (valid or not)."""
    __slots__ = ("start", "end", "value", "warnings", "kind")

    def __init__(self, start, end, value, warnings, kind):
        self.start = start
        self.end = end
        self.value = value          # "+9647XXXXXXXXX" or None
        self.warnings = warnings    # list[str]
        self.kind = kind            # "valid" | "invalid" | "foreign"

    def __repr__(self):
        return "PhoneHit(%d,%d,%r,%r,%s)" % (self.start, self.end, self.value, self.warnings, self.kind)


def _isd(c):
    return "0" <= c <= "9"


def validate(digits, plus=False):
    """Return (e164, form, warnings) or None."""
    s = digits
    intl = plus
    if s.startswith("00"):
        s = s[2:]
        intl = True
    if s.startswith("964"):
        r = s[3:]
        if _RE_INTL.fullmatch(r):
            return "+964" + r, "intl", []
        if _RE_INTL_TRUNK.fullmatch(r):
            return "+964" + r[1:], "intl", ["phone_trunk_zero_removed"]
        return None
    if intl:
        return None
    if _RE_NAT.fullmatch(s):
        return "+964" + s[1:], "national", []
    if _RE_BARE.fullmatch(s):
        return "+964" + s, "bare10", []
    return None


def _classify_invalid(digits):
    s = digits
    if s.startswith("00"):
        s = s[2:]
    if s.startswith("964"):
        s = s[3:]
    if _RE_BAD_PREFIX.fullmatch(s):
        return "phone_invalid_prefix"
    if _RE_LANDLINE.fullmatch(digits):
        return "landline_ignored"
    return "phone_invalid_length"


def _scan_runs(norm):
    """Yield (start, end, plus, groups) for every digit run."""
    n = len(norm)
    i = 0
    while i < n:
        if not _isd(norm[i]):
            i += 1
            continue
        start = i
        plus = False
        j = i - 1
        while j >= 0 and norm[j] in " (":
            j -= 1
        if j >= 0 and norm[j] == "+":
            plus = True
            start = j
        groups = []
        k = i
        while True:
            gs = k
            while k < n and _isd(norm[k]):
                k += 1
            groups.append((gs, k))
            m = k
            cnt = 0
            while m < n and norm[m] in _SEPS and cnt < 3:
                m += 1
                cnt += 1
            if cnt and m < n and _isd(norm[m]):
                k = m
                continue
            break
        yield start, k, plus, groups
        i = k


def _segment_run(norm, start, plus, groups):
    """Segment one run into PhoneHits (only at group boundaries)."""
    digits = [norm[s:e] for s, e in groups]
    total = sum(len(d) for d in digits)
    hits = []
    ng = len(groups)
    i = 0
    first_start = start  # includes '+'

    # Foreign number: '+' or '00' followed by a country code other than 964.
    if plus or digits[0].startswith("00"):
        allc = "".join(digits)
        d = allc[2:] if allc.startswith("00") else allc
        if not d.startswith("964"):
            cut = ng
            for j in range(1, ng):
                acc = ""
                for k in range(j, ng):  # window bounded: a national number is 11 digits
                    acc += digits[k]
                    if len(acc) > 11:
                        break
                    if _RE_NAT.fullmatch(acc):
                        cut = j
                        break
                if cut != ng:
                    break
            hits.append(PhoneHit(first_start, groups[cut - 1][1], None, ["phone_foreign"], "foreign"))
            i = cut
            plus = False

    dropped = []  # indices of groups dropped since the last phone
    found_any = False
    while i < ng:
        found = None
        # candidate windows starting at group i; bounded by MAX_DIGITS so the
        # whole segmentation is linear in the number of groups
        cands = []
        acc = ""
        for j in range(i, ng):
            acc += digits[j]
            if len(acc) > MAX_DIGITS:
                break
            cands.append((j, acc))
        for j, cand in reversed(cands):
            if len(cand) not in _VALID_LENGTHS:
                continue
            v = validate(cand, plus=(plus and i == 0))
            if v:
                found = (j, v)
                break
        if found:
            j, (num, form, warns) = found
            warns = list(warns)
            s0 = first_start if (i == 0) else groups[i][0]
            # a long group (>= 9 digits) joined with a 1-2 digit group is not a
            # normal way of grouping a number ("0770123456 4"): flag it (F23)
            lens = [len(digits[g]) for g in range(i, j + 1)]
            if len(lens) > 1 and max(lens) >= 9 and min(lens) <= 2:
                warns.append("phone_ambiguous_join")
            if form == "bare10" and dropped:
                # the dropped leading group is part of the same (ambiguous)
                # number: keep it out of the address too
                warns.append("phone_ambiguous_prefix")
                s0 = first_start if dropped[0] == 0 else groups[dropped[0]][0]
                dropped = []
            _flush_dropped(norm, groups, digits, dropped, hits)
            hits.append(PhoneHit(s0, groups[j][1], num, warns, "valid"))
            found_any = True
            dropped = []
            i = j + 1
        else:
            dropped.append(i)
            i += 1
    if not found_any and not hits:
        if total >= MIN_PHONELIKE:
            hits.append(PhoneHit(first_start, groups[-1][1], None,
                                 [_classify_invalid("".join(digits))], "invalid"))
        return hits
    _flush_dropped(norm, groups, digits, dropped, hits)
    hits.sort(key=lambda h: h.start)
    return hits


def _flush_dropped(norm, groups, digits, dropped, hits):
    """Dropped groups stay as address text unless they form a long phone-like
    stretch (>= 9 digits), which is reported as an invalid phone."""
    if not dropped:
        return
    stretch = []
    for gi in dropped + [None]:
        if gi is not None and (not stretch or gi == stretch[-1] + 1):
            stretch.append(gi)
            continue
        if stretch:
            d = "".join(digits[g] for g in stretch)
            if len(d) >= MIN_PHONELIKE:
                hits.append(PhoneHit(groups[stretch[0]][0], groups[stretch[-1]][1], None,
                                     [_classify_invalid(d)], "invalid"))
        stretch = [gi] if gi is not None else []


def find_phones(norm):
    """Return list of PhoneHit (sorted, non-overlapping) for the folded text."""
    hits = []
    typo_spans = []
    for m in _RE_LETTER_TYPO.finditer(norm):
        tok = m.group(0)
        if sum(c.isdigit() for c in tok) >= 7 and any(c in "oli" for c in tok) \
                and tok.lstrip("+")[:1] in ("0", "7", "9"):
            typo_spans.append((m.start(), m.end()))
            hits.append(PhoneHit(m.start(), m.end(), None, ["phone_invalid_chars"], "invalid"))
    k = 0
    for start, end, plus, groups in _scan_runs(norm):
        while k < len(typo_spans) and typo_spans[k][1] <= start:
            k += 1
        if k < len(typo_spans) and typo_spans[k][0] < end and start < typo_spans[k][1]:
            continue
        hits.extend(_segment_run(norm, start, plus, groups))
    hits.sort(key=lambda h: h.start)
    return hits


def pick_phones(hits):
    """Return (phone, alt_phone, warnings) from PhoneHits, in text order."""
    vals = []
    warnings = []
    for h in hits:
        for w in h.warnings:
            if w not in warnings:
                warnings.append(w)
        if h.value and h.value not in vals:
            vals.append(h.value)
    phone = vals[0] if vals else None
    alt = vals[1] if len(vals) > 1 else None
    if len(vals) > 2:
        warnings.append("extra_phones")
    return phone, alt, warnings
