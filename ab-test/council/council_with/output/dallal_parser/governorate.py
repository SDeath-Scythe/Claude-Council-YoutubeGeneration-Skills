"""Find place mentions in a segment and resolve the governorate.

Matching is on folded whole tokens / phrases, longest first.  Gated words
(ordinary words or personal names that are also places) only count in strong
positions; mentions right after a reference word (شارع, كراج, مول ...) are
references, not where the customer lives.
"""

from dataclasses import dataclass, field

from . import gazetteer as gz
from .normalize import fold

_MAX_PHRASE = 3


def proclitic_variants(tok):
    """'ببغداد' -> 'بغداد', 'بالبصره' -> 'البصره', 'للنجف' -> 'النجف'."""
    out = [tok]
    if len(tok) > 4 and tok[:3] in ("بال", "وال", "فال", "كال"):
        out.append("ال" + tok[3:])
    if len(tok) > 4 and tok.startswith("لل"):
        out.append("ال" + tok[2:])
    if len(tok) > 3 and tok[0] in "وبلف":
        out.append(tok[1:])
    return out


def _key(text):
    return tuple(fold(t) for t in text.split() if fold(t))


@dataclass(frozen=True)
class Entry:
    governorate: str
    tier: str  # 'A' governorate name, 'AP' phrase containing it, 'B' city, 'C' Baghdad district
    alias: str


def _build():
    lookup = {}

    def add(alias, gov, tier):
        k = _key(alias)
        if k and k not in lookup:  # first (highest) tier wins on duplicates
            lookup[k] = Entry(gov, tier, alias)

    for gov, aliases in gz.TIER_A.items():
        for a in aliases:
            add(a, gov, "A")
    for gov, aliases in gz.EXPLICIT_PHRASES.items():
        for a in aliases:
            add(a, gov, "AP")
    for gov, aliases in gz.TIER_B.items():
        for a in aliases:
            add(a, gov, "B")
    for a in gz.TIER_C_BAGHDAD:
        add(a, "Baghdad", "C")
    return lookup


LOOKUP = _build()
_NAME_COLLISIONS = {_key(w) for w in gz.NAME_COLLISIONS}
_GATED = {_key(w) for w in gz.GATED}
_REFERENCE = {fold(w) for w in gz.REFERENCE_WORDS}
_REFERENCE_AFTER = {fold(w) for w in gz.REFERENCE_WORDS_AFTER}
_PARTICLES = {fold(w) for w in gz.NAME_PARTICLES}
_COLOUR_WORDS = {fold(w) for w in ("لون", "اللون", "color", "colour")}


@dataclass
class Mention:
    governorate: str
    tier: str
    start: int  # token index in the segment
    end: int
    raw: str
    reference: bool = False
    gated: str = ""  # '' | 'name' | 'common'
    whole: bool = False  # the mention is the entire segment
    name_position: bool = False
    labelled: bool = False
    prev: str = ""  # folded token before the mention

    @property
    def strip_ok(self):
        return self.tier == "A"


def _match_at(folded, i):
    for n in range(min(_MAX_PHRASE, len(folded) - i), 0, -1):
        first = folded[i]
        rest = tuple(folded[i + 1:i + n])
        for v in proclitic_variants(first):
            k = (v,) + rest
            if k in LOOKUP:
                return n, k
    return 0, None


def find_mentions(tokens):
    """All candidate place mentions in a list of display tokens (unfiltered)."""
    folded = [fold(t) for t in tokens]
    out = []
    i = 0
    while i < len(folded):
        if not folded[i]:
            i += 1
            continue
        n, k = _match_at(folded, i)
        if not n:
            i += 1
            continue
        entry = LOOKUP[k]
        prev = folded[i - 1] if i > 0 else ""
        prev_variants = set(proclitic_variants(prev)) | ({prev[2:]} if prev.startswith("ال") else set())
        m = Mention(
            governorate=entry.governorate,
            tier=entry.tier,
            start=i,
            end=i + n,
            raw=" ".join(tokens[i:i + n]),
            reference=bool(prev_variants & _REFERENCE)
            or (i + n < len(folded) and folded[i + n] in _REFERENCE_AFTER),
            gated="name" if k in _NAME_COLLISIONS else ("common" if k in _GATED else ""),
            whole=(i == 0 and i + n == len(folded)),
            prev=prev,
        )
        # 'عبد الخضر', 'ابو القاسم', 'ام علي': a name part, never a place
        if prev in _PARTICLES and n == 1:
            i += n
            continue
        out.append(m)
        i += n
    return out


def accept(mentions, tokens, *, labelled=False, product=False, is_keyword=lambda t: False):
    """Apply the strong-position rules for gated words; drop rejected mentions.

    ``is_keyword(display_token)`` tells whether a token is an address keyword.
    """
    starts = {m.start: m for m in mentions}
    kept = []
    for m in mentions:
        if product and m.tier != "A":
            continue  # 'اريد الكوت الرمادي': order chatter, not a place
        if m.prev in _COLOUR_WORDS:
            continue
        if m.gated:
            if product:
                continue
            nxt = starts.get(m.end)
            followed = (m.end < len(tokens) and is_keyword(tokens[m.end])) or (
                nxt is not None and not nxt.gated and not nxt.reference
            )
            strong = labelled or followed or m.whole
            if m.gated == "common" and m.start == 0:
                strong = True
            if not strong:
                continue
        m.labelled = labelled
        kept.append(m)
    return kept


def resolve_governorate(text):
    """Map one place string (e.g. 'الناصرية', 'هولير', 'basrah') to a governorate.

    Treated like the value of a governorate label.  Returns the English name or
    None when nothing (or something ambiguous) matches.
    """
    if not isinstance(text, str):
        raise TypeError("resolve_governorate expects str, got %s" % type(text).__name__)
    from .normalize import clean_text

    tokens = clean_text(text).split()
    found = [m for m in accept(find_mentions(tokens), tokens, labelled=True) if not m.reference]
    govs = {m.governorate for m in found}
    if len(govs) != 1:
        return None
    return govs.pop()


@dataclass
class Candidate:
    mention: Mention
    order: int  # segment order in the message
    at_start: bool
    label: bool = False


@dataclass
class Resolution:
    governorate: str = None
    source: str = None
    raw: str = None
    confidence: str = None
    warnings: list = field(default_factory=list)
    winner: Mention = None


_RANK = {"A": 1, "AP": 1, "B": 1, "C": 2}


def resolve(cands):
    """D6: label > Tier A/B (segment start first, then first occurrence) > Tier C > reference."""
    res = Resolution()
    if not cands:
        return res
    nonref = [c for c in cands if not c.mention.reference]
    if not nonref:
        c = cands[0]
        res.governorate, res.raw, res.winner = c.mention.governorate, c.mention.raw, c.mention
        res.source, res.confidence = "reference", "low"
        res.warnings.append(("governorate_inferred", "only a street/landmark name mentions %s" % c.mention.governorate))
        return res
    strong = [c for c in nonref if not c.mention.name_position]
    pool = strong or nonref

    def key(c):
        rank = 0 if c.label else _RANK[c.mention.tier]
        return (rank, 0 if c.at_start else 1, c.order, c.mention.start)

    win = min(pool, key=key)
    m = win.mention
    res.governorate, res.raw, res.winner = m.governorate, m.raw, m
    if win.label:
        res.source = "label"
    else:
        res.source = {"A": "explicit", "AP": "explicit", "B": "city", "C": "district"}[m.tier]
    res.confidence = "low" if (m.tier == "C" and not win.label) else "high"
    if res.source == "district":
        res.warnings.append(("governorate_inferred", "inferred from the Baghdad district '%s'" % m.raw))

    same = [c for c in pool if c.mention.governorate == m.governorate]
    if all(c.mention.gated == "name" and not c.label for c in same):
        res.confidence = "low"
        res.warnings.append(("governorate_inferred", "'%s' is also a common personal name" % m.raw))
    if not strong:
        res.confidence = "low"
        res.warnings.append(("governorate_inferred", "'%s' was written next to the name" % m.raw))
        res.warnings.append(("name_uncertain", "the name line also contains the place '%s'" % m.raw))

    others = sorted({c.mention.governorate for c in strong if c.mention.governorate != m.governorate})
    if others:
        res.confidence = "low"
        res.warnings.append(
            ("multiple_governorates", "chose %s; also mentioned: %s" % (m.governorate, ", ".join(others)))
        )
    return res
