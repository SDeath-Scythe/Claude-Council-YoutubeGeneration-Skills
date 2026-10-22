"""Gazetteer matching and governorate resolution (D4, D5)."""
from . import gazetteer as G
from .normalize import fold_simple, latin_skeleton, is_latin_letter
from .segment import WORD, NUM

_AR_PREFIXES = ["وبال", "وال", "بال", "فال", "كال", "وعال", "عال", "ولل", "لل", "وب", "ول", "و", "ب", "ل", "ف", ""]
_AL_PREFIXES = {"وبال", "وال", "بال", "فال", "كال", "وعال", "عال", "ولل", "لل"}
_LATIN_AL = ("al", "el", "an", "as", "ad", "ar", "at")
_CONTEXT_PREFIXES = {"ب", "ل", "بال", "لل", "وب", "ول", "وبال", "ولل", "عال", "وعال"}


def _is_latin(word):
    return any(is_latin_letter(c) for c in word)


def _word_form(w):
    return latin_skeleton(w) if _is_latin(w) else w


class Entry:
    __slots__ = ("gov", "tier", "capital", "collision", "person", "needs_al", "alias",
                 "building", "district_named")

    def __init__(self, gov, tier, capital, alias):
        self.gov = gov
        self.tier = tier
        self.capital = capital
        self.alias = alias
        self.collision = False
        self.person = False
        self.needs_al = False
        self.building = False
        self.district_named = False


def _alias_key(alias):
    """Return (key tuple, had_al) for a gazetteer alias."""
    f = fold_simple(alias).replace("-", " ").replace("'", " ")
    toks = [t for t in "".join(c if (c.isalnum() or c == " ") else " " for c in f).split()]
    if not toks:
        return None, False
    had_al = False
    if _is_latin(toks[0]):
        toks = [latin_skeleton(t) for t in toks]
        if len(toks) > 1 and toks[0] in ("al", "el", "an", "as", "ad", "ar", "at"):
            toks = toks[1:]
            had_al = True
        return tuple(toks), had_al
    if toks[0].startswith("ال") and len(toks[0]) > 3:
        toks[0] = toks[0][2:]
        had_al = True
    return tuple(toks), had_al


def _folded_set(lst):
    return {_alias_key(a)[0] for a in lst if _alias_key(a)[0]}


_COLLISION = _folded_set(G.COLLISION_ALIASES)
_COLLISION_NEEDS_AL = {_alias_key(a)[0] for a in G.COLLISION_ALIASES
                       if _alias_key(a)[1] and not _is_latin(a)}
_PERSON = _folded_set(G.PERSON_NAME_GOVS)
_DISTRICT_NAMED = _folded_set(G.DISTRICT_NAMED_GOVS)
_BUILDING = _folded_set(G.BUILDING_AMBIGUOUS)

INDEX = {}
MAXLEN = 1


def _add(alias, gov, tier, capital):
    global MAXLEN
    key, had_al = _alias_key(alias)
    if not key:
        return
    e = Entry(gov, tier, capital, alias)
    e.collision = key in _COLLISION
    e.needs_al = key in _COLLISION_NEEDS_AL or key in _BUILDING
    e.person = key in _PERSON
    e.building = key in _BUILDING
    e.district_named = key in _DISTRICT_NAMED
    lst = INDEX.setdefault(key, [])
    if any(x.gov == gov and x.tier <= tier for x in lst):
        return
    lst[:] = [x for x in lst if not (x.gov == gov and x.tier > tier)]
    lst.append(e)
    MAXLEN = max(MAXLEN, len(key))


for _gov, _d in G.GOVERNORATES.items():
    for _a in _d["aliases"]:
        _add(_a, _gov, 1, True)
for _gov, _cap, _lst in G.TIER2:
    for _a in _lst:
        _add(_a, _gov, 2, _cap)
for _gov, _lst in G.TIER3:
    for _a in _lst:
        _add(_a, _gov, 3, False)

FIRST_TOKENS = {k[0] for k in INDEX}

_LANDMARK_NOUNS = {fold_simple(w) for w in G.LANDMARK_NOUNS}
_LANDMARK_NOUNS |= {latin_skeleton(w) for w in G.LANDMARK_NOUNS if _is_latin(w)}
_LATIN_FOLLOW = {latin_skeleton(w) for w in G.LATIN_FOLLOW_NOUNS} | set(G.LATIN_FOLLOW_NOUNS)
TRIGGERS = {fold_simple(w) for w in G.LANDMARK_TRIGGERS}
STREET_WORDS = {fold_simple(w) for w in G.STREET_WORDS}
_BUILD_NEXT = {fold_simple(w) for w in G.BUILDING_NEXT_WORDS}
_BUILD_PREV = {fold_simple(w) for w in G.BUILDING_PREV_WORDS}
_CUES = {fold_simple(w) for w in G.DELIVERY_CUES}
_CUE_PREPS = {fold_simple(w) for w in G.DELIVERY_PREPS}


def strip_prefix_word(w):
    """Remove one attached و/ب/ل and ال for word-list lookups."""
    forms = [w]
    for p in ("و", "ب", "ل", "وب", "ول", "بال", "وال", "لل", "ال"):
        if w.startswith(p) and len(w) - len(p) >= 2:
            r = w[len(p):]
            forms.append(r)
            if r.startswith("ال") and len(r) > 3:
                forms.append(r[2:])
    return forms


def is_landmark_noun(w):
    return any(f in _LANDMARK_NOUNS for f in strip_prefix_word(w)) or latin_skeleton(w) in _LANDMARK_NOUNS


def is_trigger(w):
    return w in TRIGGERS or (w.startswith("و") and w[1:] in TRIGGERS)


def is_street_word(w):
    return any(f in STREET_WORDS for f in strip_prefix_word(w)[:2]) or w in STREET_WORDS


class Hit:
    __slots__ = ("gov", "tier", "capital", "collision", "person", "t0", "t1", "seg",
                 "landmark", "excluded", "prefix", "entry", "in_phrase", "district")

    def __init__(self, entry, t0, t1, prefix):
        self.entry = entry
        self.gov = entry.gov
        self.tier = entry.tier
        self.capital = entry.capital
        self.collision = entry.collision
        self.person = entry.person
        self.t0 = t0
        self.t1 = t1          # exclusive
        self.seg = None
        self.landmark = False
        self.excluded = False
        self.in_phrase = False
        self.district = False
        self.prefix = prefix

    @property
    def t1eq(self):
        return self.tier == 1 or self.capital

    def __repr__(self):
        return "<Hit %s t%d %s%s%s>" % (self.gov, self.tier, self.entry.alias,
                                        " LM" if self.landmark else "",
                                        " X" if self.excluded else "")


def _first_forms(w):
    """(form, had_al, prefix) variants for the first token of a key."""
    if _is_latin(w):
        return [(latin_skeleton(w), False, "")]
    out = []
    for p in _AR_PREFIXES:
        if p and not (w.startswith(p) and len(w) - len(p) >= 3):
            continue
        r = w[len(p):]
        had_al = p in _AL_PREFIXES
        if p == "" and r.startswith("ال") and len(r) > 3:
            out.append((r[2:], True, "ال"))
            continue
        if p and not had_al and r.startswith("ال") and len(r) > 3:
            out.append((r[2:], True, p + "ال"))
            continue
        out.append((r, had_al, p))
    return out


def match_places(tokens):
    """Find gazetteer hits over runs of consecutive WORD tokens."""
    hits = []
    n = len(tokens)
    i = 0
    while i < n:
        if tokens[i].kind != WORD:
            i += 1
            continue
        found = None
        forms0 = _first_forms(tokens[i].text)
        is_al = tokens[i].text in _LATIN_AL
        if not is_al and not any(f in FIRST_TOKENS for f, _a, _p in forms0):
            i += 1
            continue
        for L in range(MAXLEN + 1, 0, -1):
            if i + L > n or any(tokens[k].kind != WORD for k in range(i, i + L)):
                continue
            rest = tuple(_word_form(tokens[k].text) for k in range(i + 1, i + L))
            if L <= MAXLEN:
                for f, had_al, p in forms0:
                    entries = [e for e in INDEX.get((f,) + rest, ()) if not e.needs_al or had_al]
                    if entries:
                        found = (entries, L, p)
                        break
            # Latin "al"/"el" before a key is optional: "al mansour", "al-zuhur"
            if not found and L >= 2 and tokens[i].text in _LATIN_AL:
                entries = [e for e in INDEX.get(rest, ()) if not e.needs_al or True]
                if entries:
                    found = (entries, L, "")
            if found:
                break
        if not found:
            i += 1
            continue
        entries, L, p = found
        for e in entries[:1]:
            h = Hit(e, i, i + L, p)
            hits.append(h)
            for k in range(i, i + L):
                tokens[k].hit = h
        i += L
    return hits


def _prev_word(tokens, i, seg_set):
    j = i - 1
    if j >= 0 and j in seg_set and tokens[j].kind in (WORD, NUM):
        return tokens[j]
    return None


def _next_word(tokens, i, seg_set):
    if i < len(tokens) and i in seg_set and tokens[i].kind in (WORD, NUM):
        return tokens[i]
    return None


def annotate_hits(tokens, hits, segs, product_msg):
    """Apply building, landmark, district, collision-context rules (D4/D5)."""
    seg_of = {}
    for s in segs:
        for k in s.toks:
            seg_of[k] = s
    line_info = {}
    for s in segs:
        info = line_info.setdefault(s.line, {"place": False, "street": False, "addr": False})
        if s.field in ("addr", "gov"):
            info["addr"] = True
        for k in s.toks:
            w = tokens[k].text
            if is_street_word(w) or is_trigger(w):
                info["street"] = True
            h = tokens[k].hit
            if h is not None and not h.collision and not h.entry.building:
                info["place"] = True

    # per-segment precomputation (keeps the whole pass linear)
    seg_info = {}
    for s in segs:
        first_trigger = None
        nhit_tokens = 0
        all_hit = True
        for k in s.toks:
            t = tokens[k]
            if first_trigger is None and t.kind == WORD and is_trigger(t.text):
                first_trigger = k
            if t.hit is not None:
                nhit_tokens += 1
            else:
                all_hit = False
        seg_info[id(s)] = (set(s.toks), first_trigger, nhit_tokens, all_hit)
    seg_hits = {}

    for h in hits:
        s = seg_of.get(h.t0)
        h.seg = s
        if s is None:
            h.excluded = True
            continue
        sset, first_trigger, nhit_tokens, all_hit = seg_info[id(s)]
        prev = _prev_word(tokens, h.t0, sset)
        nxt = _next_word(tokens, h.t1, sset)
        seg_has_other_place = nhit_tokens > (h.t1 - h.t0)
        # (d) العمارة = building
        if h.entry.building:
            if (nxt is not None and (nxt.kind == NUM or nxt.text in _BUILD_NEXT)) or \
               (prev is not None and prev.text in _BUILD_PREV and seg_has_other_place):
                h.excluded = True
                continue
        # (a) landmark noun directly before (tier 1/2 only)
        if h.tier in (1, 2) and prev is not None and prev.kind == WORD and is_landmark_noun(prev.text):
            h.landmark = True
        if _is_latin(tokens[h.t0].text) and nxt is not None and nxt.kind == WORD and \
                (nxt.text in _LATIN_FOLLOW or latin_skeleton(nxt.text) in _LATIN_FOLLOW):
            h.landmark = True
        # inside a landmark phrase (after قرب/يم/near ... in the same segment)
        if first_trigger is not None and first_trigger < h.t0:
            h.in_phrase = True
        # collision aliases need an address context
        if h.collision:
            info = line_info.get(s.line, {})
            ctx = (s.field in ("addr", "gov") or info.get("addr") or info.get("street")
                   or info.get("place") or h.prefix.rstrip("ال") in _CONTEXT_PREFIXES
                   or h.prefix in _CONTEXT_PREFIXES
                   or (prev is not None and prev.text in ("من", "في", "ب", "ع", "عل", "from", "in", "to")))
            if not ctx and not product_msg:
                ctx = all_hit
            if not ctx or s.product:
                h.excluded = True
                continue
        # (e) district-named governorates after a place of another governorate
        if h.tier == 1 and h.entry.district_named:
            for g in seg_hits.get(id(s), ()):
                if g.gov != h.gov and not g.excluded and g.tier in (1, 2) and not g.landmark:
                    h.landmark = True
                    h.district = True
                    break
        seg_hits.setdefault(id(s), []).append(h)


def resolve(tokens, hits):
    """Return (governorate, warnings, winner_hits, conflict_govs)."""
    live = [h for h in hits if not h.excluded]
    # (b) landmark-phrase demotion only when a plain place exists elsewhere
    plain = [h for h in live if not h.landmark and not h.in_phrase]
    if plain:
        for h in live:
            if h.in_phrase:
                h.landmark = True
    else:
        for h in live:
            if h.in_phrase and not h.landmark:
                pass  # phrase-only evidence still counts (e.g. "قرب الكرادة")
    ev = [h for h in live if not h.landmark]
    if not ev:
        return None, [], [], []
    # A tier-3 neighbourhood never conflicts with a governorate, capital or
    # district town of another governorate: many neighbourhood names (حي الجهاد،
    # الدورة، الشعلة) also exist outside the city they are best known in, so
    # the explicit higher-tier place wins silently (review 1, F28/F8).
    if any(h.tier <= 2 for h in ev):
        strong_govs = {h.gov for h in ev if h.tier <= 2}
        ev = [h for h in ev if h.tier <= 2 or h.gov in strong_govs]
    govs = []
    for h in ev:
        if h.gov not in govs:
            govs.append(h.gov)
    warnings = []
    if len(govs) == 1:
        gov = govs[0]
        if not any(h.tier == 1 for h in ev):
            warnings.append("governorate_inferred_from_city")
        return gov, warnings, [h for h in ev if h.gov == gov], []
    t1govs = []
    for h in ev:
        if h.t1eq and h.gov not in t1govs:
            t1govs.append(h.gov)
    if len(t1govs) >= 2:
        warnings.append("multiple_governorates")
        cued = _cued_govs(tokens, ev)
        cued = [g for g in cued if g in t1govs]
        gov = cued[0] if len(set(cued)) == 1 else None
        return gov, warnings, [h for h in ev if h.gov == gov] if gov else [], t1govs[:2]
    if len(t1govs) == 1:
        gov = t1govs[0]
        other = [g for g in govs if g != gov]
        warnings.append("governorate_conflict")
        if not any(h.tier == 1 and h.gov == gov for h in ev):
            warnings.append("governorate_inferred_from_city")
        return gov, warnings, [h for h in ev if h.gov == gov], [gov, other[0]]
    # only tier 2/3 evidence for several governorates
    best = min(h.tier for h in ev)
    top = []
    for h in ev:
        if h.tier == best and h.gov not in top:
            top.append(h.gov)
    if len(top) == 1:
        gov = top[0]
        other = [g for g in govs if g != gov]
        return gov, ["governorate_conflict", "governorate_inferred_from_city"], \
            [h for h in ev if h.gov == gov], [gov, other[0]]
    return None, ["multiple_governorates"], [], top[:2]


def _cued_govs(tokens, ev):
    """Governorates attached to a delivery cue: "ابعثوه للناصرية", "send to Erbil"."""
    out = []
    for h in ev:
        for k in range(h.t0 - 1, max(h.t0 - 4, -1), -1):
            if tokens[k].kind != WORD:
                break
            w = tokens[k].text
            if w in _CUES or latin_skeleton(w) in _CUES:
                out.append(h.gov)
                break
            if w not in _CUE_PREPS:
                break
    return out
