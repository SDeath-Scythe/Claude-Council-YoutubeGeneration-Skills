"""parse_order: the pipeline.

  fold -> phones -> tokens -> gazetteer hits -> labels -> segments
  -> name-label cut -> product / greeting handling -> hit annotation
  -> person-name governorates -> name -> governorate -> address -> flags.
"""
import bisect
import logging

from . import gazetteer as G
from .followup import BLOCKING, build_followup
from .normalize import fold, fold_simple, squeeze, is_arabic_letter
from .phones import find_phones
from .places import (annotate_hits, is_landmark_noun, is_street_word, is_trigger, match_places,
                     resolve)
from .segment import (NUM, PHONE, WORD, Segment, build_segments, detect_labels, tokenize)

log = logging.getLogger("dallal_parser")

MAX_INPUT = 20000
MAX_NAME_TOKEN = 25   # characters per name word
MAX_NAME_CHARS = 60   # characters for the whole name
CORE_FIELDS = ("name", "phone", "governorate", "address")


def _fs(lst):
    out = set()
    for w in lst:
        for t in fold_simple(w).replace("'", " ").split():
            out.add(t)
    return out


def _phrases(lst):
    out = [tuple(fold_simple(p).split()) for p in lst]
    return sorted([p for p in out if p], key=len, reverse=True)


_WEAK_ORDER = _fs(G.WEAK_ORDER_WORDS)
_ORDER = _fs(G.ORDER_WORDS) - _WEAK_ORDER   # strong product words (always product talk)
_COLOURS = _fs(G.COLOUR_WORDS)
_CORRECTION = _fs(G.CORRECTION_WORDS)
_SECONDARY = _fs(G.SECONDARY_PHONE_WORDS)
_PRIMARY = _fs(G.PRIMARY_PHONE_WORDS)
_THIS = _fs(["هذا", "هاذا", "وهذا", "this", "its", "it's"])
_AMBIG_GREET = _fs(G.AMBIGUOUS_GREETING_NAMES)
_GREET_PHRASES = _phrases(G.GREETING_PHRASES)
_GREET_WORDS = {p[0] for p in _GREET_PHRASES if len(p) == 1} - _AMBIG_GREET
_CONNECT = _fs(G.CONNECTORS)
_CHATTER = _fs(G.CHATTER) - _AMBIG_GREET
_CUES = _fs(G.DELIVERY_CUES)
_HELPER = _fs(G.HELPER_WORDS)
_PHONE_INTRO = _fs(G.PHONE_INTRO_WORDS)
_ADDR_CUT = _fs(G.ADDRESS_CUT_WORDS)
_LABEL_WORDS = _fs(G.NAME_LABELS + G.PHONE_LABELS + G.GOV_LABELS + G.ADDRESS_LABELS + G.NAME_INTRO)
_STREET = _fs(G.STREET_WORDS) | _fs(G.LANDMARK_TRIGGERS)
# words that can never be (part of) a customer name
_NAME_STOP = (_ORDER | _GREET_WORDS | _CONNECT | _CHATTER | _CUES | _LABEL_WORDS | _STREET
              | _HELPER | _CORRECTION | (_WEAK_ORDER - {"طلب"})
              | _fs(["ان", "شاء", "انشاء", "الله يخليك"]))
_NAME_STOP -= {"ابو", "ام", "عبد", "الله"} | _AMBIG_GREET
# words that can be glued to a و/ل prefix and still never be a name (ورقم، والثاني، للزبونة)
_PREFIXABLE_STOP = _LABEL_WORDS | _HELPER | _PHONE_INTRO
# words trimmed from the edges of address pieces / making a segment pure noise
_TRIM = (_CONNECT | _CHATTER | _CUES | _GREET_WORDS | _CORRECTION
         | _fs(["ساكن", "ساكنة", "عنواني", "العنوان", "to", "for", "please", "send", "deliver"]))
_TRIM -= _STREET
# "على"/"الى" fold to "علي"/"الي"; "علي" is Iraq's most common name, so these two
# are recognised on the ORIGINAL spelling only (review 1, F21).
_TRIM.discard("علي")
_TRIM_ORIGINAL = {"على", "الى", "إلى"}
_NOTE_WORDS = _fs(["اسمه", "اسمها", "يستلم", "تستلم", "يستلمه", "يستلمها", "المستلم", "receiver",
                   "recipient"])
# given names that start with ال (the ال-rule would otherwise reject them)
_AL_NAMES = _fs(["الاء", "آلاء", "الهام", "إلهام", "الياس", "إلياس", "الطاف", "الحاج", "الحجي",
                 "الشيخ", "السيد", "اليسا", "الين", "الان", "الماس"])
_KUNYA = {"ابو", "ام"}


def empty_record():
    return {"name": None, "phone": None, "governorate": None, "address": None,
            "alt_phone": None, "needs_review": True, "missing": list(CORE_FIELDS),
            "warnings": [], "followup_ar": None, "notes": None}


def parse_order(text):
    """Parse one Instagram DM into an order record.  Never raises."""
    try:
        if text is None:
            text = ""
        elif not isinstance(text, str):
            text = str(text)
        return _parse(text)
    except Exception:  # defensive (D10); exercised by tests/test_robustness.py
        log.exception("dallal_parser.parse_order failed; returning empty record")
        rec = empty_record()
        rec["warnings"] = ["internal_error"]
        rec["followup_ar"] = build_followup(rec)
        return rec


def _parse(text):
    warnings = []
    if len(text) > MAX_INPUT:
        text = text[:MAX_INPUT]
        warnings.append("input_truncated")
    norm, omap = fold(text)
    phone_hits = find_phones(norm)
    tokens = tokenize(norm, omap, phone_hits)
    phone, alt, pwarn = _select_phones(tokens)
    hits = match_places(tokens)

    line_starts = {}
    for t in tokens:
        if t.kind in (WORD, NUM, PHONE) and t.line not in line_starts:
            line_starts[t.line] = t.idx

    def is_place_token(k):
        return tokens[k].hit is not None

    def is_stop(w):
        return _is_stop_word(w)

    labels = detect_labels(tokens, line_starts, is_place_token, is_stop)
    segs = build_segments(tokens, labels)
    segs = _cut_name_labels(tokens, segs)
    _cut_phone_intros(tokens, segs)
    product_msg = False
    for s in segs:
        _strip_greetings(tokens, s)
        if s.field not in ("addr", "gov") and any(_is_order_at(tokens, s.toks, i)
                                                  for i in range(len(s.toks))):
            s.product = True
            product_msg = True
    segs = [s for s in segs if s.toks]
    for i, s in enumerate(segs):
        s.idx = i

    annotate_hits(tokens, hits, segs, product_msg)
    for h in hits:
        if h.seg is not None and h.seg.field == "name":
            h.excluded = True
        if h.seg is not None and h.seg.product and h.collision:
            h.excluded = True
    _person_name_rule(tokens, hits, segs)

    name_toks = _choose_name(tokens, segs)
    for h in hits:
        if any(k in name_toks for k in range(h.t0, h.t1)):
            h.excluded = True

    gov, gwarn, winner_hits, conflict = resolve(tokens, hits)
    notes = []
    address = _build_address(text, tokens, segs, name_toks, winner_hits, hits,
                             cue_resolved=("multiple_governorates" in gwarn and gov is not None),
                             notes=notes)
    name = _slice_tokens(text, tokens, sorted(name_toks)) if name_toks else None

    rec = {"name": name or None, "phone": phone, "governorate": gov, "address": address,
           "alt_phone": alt}
    for w in pwarn + gwarn:
        if w not in warnings:
            warnings.append(w)
    missing = [f for f in CORE_FIELDS if rec[f] is None]
    rec["needs_review"] = bool(missing) or any(w in BLOCKING for w in warnings)
    rec["missing"] = missing
    rec["warnings"] = warnings
    rec["followup_ar"] = build_followup(rec, conflict)
    rec["notes"] = "، ".join(notes) if notes else None
    return rec


# ------------------------------------------------------------------ helpers
def _is_order(w):
    """Strong product word (always product talk)."""
    if w in _ORDER:
        return True
    if len(w) > 3 and w[0] in "و" and w[1:] in _ORDER:
        return True
    return False


def _is_order_at(tokens, toks, i):
    """Product word at position i of a token list, judged in context (F41/F48/F49):
    قطعة 12 = plot number, 25 الف = price, لون اسود = colour, ابو طلب = name."""
    t = tokens[toks[i]]
    if t.kind != WORD:
        return False
    w = t.text
    if _is_order(w):
        return True
    base = w[1:] if (len(w) > 3 and w[0] == "و" and w[1:] in _WEAK_ORDER) else w
    if base not in _WEAK_ORDER:
        return False
    prev = tokens[toks[i - 1]] if i > 0 else None
    nxt = tokens[toks[i + 1]] if i + 1 < len(toks) else None
    if base in ("قطعه", "القطعه"):
        return not (nxt is not None and nxt.kind == NUM)
    if base == "الف":
        return prev is not None and prev.kind == NUM
    if base in ("لون", "اللون"):
        return nxt is not None and (nxt.text in _COLOURS or (nxt.text[:2] == "ال" and nxt.text[2:] in _COLOURS))
    if base in ("طلب", "الطلب"):
        return not (prev is not None and (prev.text in _KUNYA or is_landmark_noun(prev.text)))
    return False


_GREET_MAXLEN = max(len(p) for p in _GREET_PHRASES)
_GREET_SET = set(_GREET_PHRASES)


def _strip_greetings(tokens, seg):
    """Remove greeting/politeness phrases from both ends of a segment.  Greeting
    words that are also given names (سلام، هلا، رجاء، زين) are removed only when
    they are the whole remaining segment or are followed by another greeting."""
    toks = seg.toks
    lo, hi = 0, len(toks)
    texts = [tokens[k].text for k in toks]

    def ok_strip(start, L, at_front):
        if L != 1 or texts[start] not in _AMBIG_GREET:
            return True
        if hi - lo == 1:
            return True
        if at_front:
            nxt = start + 1
            return any(tuple(texts[nxt:nxt + M]) in _GREET_SET for M in range(1, _GREET_MAXLEN + 1))
        return False

    progress = True
    while progress and lo < hi:
        progress = False
        for L in range(min(_GREET_MAXLEN, hi - lo), 0, -1):
            if tuple(texts[lo:lo + L]) in _GREET_SET and ok_strip(lo, L, True):
                lo += L
                progress = True
                break
        if progress:
            continue
        for L in range(min(_GREET_MAXLEN, hi - lo - 1), 0, -1):
            if tuple(texts[hi - L:hi]) in _GREET_SET and ok_strip(hi - L, L, False):
                hi -= L
                progress = True
                break
    seg.toks = toks[lo:hi]


def _is_stop_word(w):
    if w in _NAME_STOP:
        return True
    for p in ("و", "لل", "ل"):
        if w.startswith(p) and len(w) - len(p) >= 3 and w[len(p):] in _PREFIXABLE_STOP:
            return True
    return False


def _plausible_word(w):
    if len(w) > MAX_NAME_TOKEN:
        return False
    for i in range(len(w) - 2):
        if w[i] == w[i + 1] == w[i + 2]:
            return False
    return True


def _name_tok_ok(tokens, k):
    t = tokens[k]
    if t.kind != WORD or t.label:
        return False
    w = t.text
    if len(w) < 2 and not w.isascii():
        return False
    if len(w) < 2:
        return False
    if _is_stop_word(w) or is_street_word(w) or is_trigger(w) or _is_order(w):
        return False
    if not _plausible_word(w):
        return False
    if t.hit is not None and not t.hit.excluded:
        return False
    return True


def _name_like(tokens, toks, labelled=False):
    if not toks:
        return False
    if len(toks) > (5 if labelled else 4):
        return False
    if not all(_name_tok_ok(tokens, k) for k in toks):
        return False
    if sum(len(tokens[k].text) for k in toks) + len(toks) - 1 > MAX_NAME_CHARS:
        return False
    if not labelled:
        first = tokens[toks[0]].text
        if first.startswith("ال") and first not in _AL_NAMES:
            return False
        if first in ("al", "el") and len(toks) == 1:
            return False
    if len(toks) == 1 and tokens[toks[0]].text in ("ابو", "ام", "عبد"):
        return False
    return True


def _cut_name_labels(tokens, segs):
    """A labelled name value ends at the next digit run, place, landmark word or
    stopword (max 5 tokens); the remainder becomes an ordinary segment (D7)."""
    out = []
    for s in segs:
        if s.field != "name":
            out.append(s)
            continue
        k = 0
        while k < len(s.toks) and k < 5:
            t = tokens[s.toks[k]]
            if t.kind != WORD:
                break
            h = t.hit
            w = t.text
            if h is not None and not h.person:
                # an ال-word right after a name word is a surname/nisba
                # ("الاسم: علي الزبير") unless it is a governorate or a capital
                # and something follows on the same field
                surname = (k >= 1 and w.startswith("ال") and h.t1 - h.t0 == 1 and not h.t1eq
                           and (k + 1 >= len(s.toks) or tokens[s.toks[k + 1]].hit is None))
                if not surname:
                    break
            elif _is_stop_word(w) or is_street_word(w) or is_trigger(w) or _is_order(w):
                break
            if not _plausible_word(w):
                break
            k += 1
        value, rest = s.toks[:k], s.toks[k:]
        if s.carried and not _name_like(tokens, value, labelled=True):
            s.field = None
            out.append(s)
            continue
        if value:
            s.toks = value
            out.append(s)
        if rest:
            r = Segment(None, s.line)
            r.toks = rest
            r.before_phone = s.before_phone
            r.first_in_line = False
            out.append(r)
            s.before_phone = False
    return out


def _window_words(tokens, start, step, limit):
    """Up to `limit` WORD texts from tokens[start] going in direction `step`,
    stopping at another phone or a line break."""
    out = []
    k = start
    while 0 <= k < len(tokens) and len(out) < limit:
        t = tokens[k]
        if t.kind in (PHONE, "nl"):
            break
        if t.kind == WORD:
            out.append(t.text)
        k += step
    return out


def _has(words, vocab):
    return any(w in vocab or (w[:1] == "و" and w[1:] in vocab) for w in words)


def _select_phones(tokens):
    """Primary / alternate phone with corrections (F32) and ranking (F34).
    Ambiguous joins/prefixes never fill a phone field (F46)."""
    warnings = []
    cands = []
    for t in tokens:
        if t.kind != PHONE:
            continue
        for w in t.phone.warnings:
            if w not in warnings:
                warnings.append(w)
        ambiguous = any(w in ("phone_ambiguous_prefix", "phone_ambiguous_join") for w in t.phone.warnings)
        if t.phone.value and not ambiguous:
            cands.append(t)
    # corrections: a correction word between two numbers retracts the earlier ones
    retracted = set()
    for i in range(1, len(cands)):
        between = [tokens[k].text for k in range(cands[i - 1].idx + 1, cands[i].idx)
                   if tokens[k].kind == WORD]
        if _has(between, _CORRECTION):
            retracted.update(c.idx for c in cands[:i])
    if retracted:
        warnings.append("phone_corrected")
    cands = [c for c in cands if c.idx not in retracted]

    def rank(t):
        before = _window_words(tokens, t.idx - 1, -1, 3)
        after = _window_words(tokens, t.idx + 1, 1, 4)
        if _has(before, _PRIMARY):
            return 0
        if _has(before, _SECONDARY) or (_has(after, _THIS) and _has(after, _SECONDARY)):
            return 2
        return 1
    cands.sort(key=lambda t: (rank(t), t.idx))
    vals = []
    for t in cands:
        if t.phone.value not in vals:
            vals.append(t.phone.value)
    if len(vals) > 2:
        warnings.append("extra_phones")
    return (vals[0] if vals else None), (vals[1] if len(vals) > 1 else None), warnings


def _cut_phone_intros(tokens, segs):
    """'هذا رقم اخوي 0770...', 'رقم المستلم: 0780...', 'تلفون البيت 01...': a
    phone-introduction word within the 3 words before a phone starts a phone
    label; it and the words after it are not address or name (F15/F26)."""
    for s in segs:
        if not s.before_phone or s.field not in (None, "addr", "gov"):
            continue
        n = len(s.toks)
        cut = None
        for j in range(max(0, n - 3), n):
            w = tokens[s.toks[j]].text
            if w in _PHONE_INTRO or (w.startswith("و") and w[1:] in _PHONE_INTRO):
                cut = j
                break
        if cut is None:
            continue
        for k in s.toks[cut:]:
            tokens[k].label = True
        s.toks = s.toks[:cut]


def phone_lines(tokens):
    return sorted({t.line for t in tokens if t.kind == PHONE})


def _person_name_rule(tokens, hits, segs):
    """D5(e): ميسان / مثنى / صلاح الدين in the leading name position are name
    tokens when another governorate is mentioned."""
    person_hits = [h for h in hits if h.person and not h.excluded and not h.landmark]
    if not person_hits:
        return
    words = [t.idx for t in tokens if t.kind == WORD and not t.label]
    first_phone = next((t.idx for t in tokens if t.kind == PHONE), None)
    lead = set(k for k in words[:3] if first_phone is None or k < first_phone)
    for t in tokens:
        if t.kind == PHONE:
            pos = bisect.bisect_left(words, t.idx)
            lead.update(k for k in words[max(0, pos - 3):pos] if tokens[k].line == t.line)
    for h in person_hits:
        if h.t0 not in lead or h.seg is None or len(h.seg.toks) > 3:
            continue
        if any(is_street_word(tokens[k].text) for k in h.seg.toks):
            continue
        # any other place evidence (another governorate, or the same one named
        # again, e.g. "المثنى السماوة ... مثنى عباس") makes this a name
        other = [g for g in hits if g is not h and not g.excluded and not g.landmark
                 and not (g.person and g.gov == h.gov and g.t0 in lead)]
        if other:
            h.excluded = True


def _eligible(s):
    return s.field is None and not s.product and not s.q


def _line_distance(seg, plines):
    if not plines:
        return 0
    i = bisect.bisect_left(plines, seg.line)
    d = []
    if i < len(plines):
        d.append(plines[i] - seg.line)
    if i > 0:
        d.append(seg.line - plines[i - 1])
    return min(d)


def _choose_name(tokens, segs):
    """Return the set of token indices forming the customer name (D7)."""
    # (1) labelled value / (2) phrase (انا X, اسمي X)
    for s in segs:
        if s.field == "name" and _name_like(tokens, s.toks, labelled=True):
            return set(s.toks)
    elig = [s for s in segs if _eligible(s)]
    plines = phone_lines(tokens)
    # (3) unlabelled short segments: before the phone, own line (closest to a
    #     phone line first), after the phone, first segment of a line
    for s in elig:
        if s.before_phone and _name_like(tokens, s.toks):
            return set(s.toks)
    own = [s for s in elig if s.own_line and _name_like(tokens, s.toks)]
    if own:
        own.sort(key=lambda s: (_line_distance(s, plines), s.idx))
        return set(own[0].toks)
    for pred in (lambda s: s.after_phone, lambda s: s.first_in_line):
        for s in elig:
            if pred(s) and _name_like(tokens, s.toks):
                return set(s.toks)
    # (4a) letter run immediately before the phone, after a place / number
    #      (a kunya may also end an address-labelled segment)
    for s in segs:
        if not s.before_phone or s.product or s.q:
            continue
        kunya_only = s.field in ("addr", "gov")
        if s.field is not None and not kunya_only:
            continue
        run = []
        k = len(s.toks) - 1
        while k >= 0 and _name_tok_ok(tokens, s.toks[k]) and len(run) < 5:
            run.insert(0, s.toks[k])
            k -= 1
        if not run or k < 0 or len(run) > 4:
            continue
        stop = tokens[s.toks[k]]
        # a kunya (ابو X / ام X) right before the phone is a name even after a
        # landmark, unless it directly follows a landmark noun ("قرب بيت ابو علي")
        for ki in range(len(run) - 2, max(len(run) - 4, -1), -1):
            if tokens[run[ki]].text in _KUNYA:
                before = tokens[run[ki - 1]] if ki > 0 else stop
                if not (before.kind == WORD and (is_street_word(before.text) or is_landmark_noun(before.text)
                                                 or before.text in ("بيت", "دار"))):
                    sub = run[ki:]
                    if _name_like(tokens, sub):
                        return set(sub)
                break
        if kunya_only:
            continue
        if not (stop.kind == NUM or (stop.hit is not None and not stop.hit.excluded)
                or _is_stop_word(stop.text) and (stop.text in _HELPER or stop.text in _LABEL_WORDS
                                                 or stop.text[1:] in _PREFIXABLE_STOP
                                                 or stop.text[2:] in _PREFIXABLE_STOP)):
            continue
        if any(tokens[j].kind == WORD and is_trigger(tokens[j].text) for j in s.toks[:k + 1]):
            continue
        if _name_like(tokens, run):
            return set(run)
    # (4b) leading letter run up to the first place token, or up to من/from + place
    for s in elig:
        run = []
        k = 0
        while k < len(s.toks) and _name_tok_ok(tokens, s.toks[k]) and len(run) < 5:
            run.append(s.toks[k])
            k += 1
        if not run or k >= len(s.toks) or len(run) > 4:
            continue
        stop = tokens[s.toks[k]]
        nxt = tokens[s.toks[k + 1]] if k + 1 < len(s.toks) else None
        place_stop = stop.hit is not None and not stop.hit.excluded and not stop.hit.landmark
        from_place = (stop.text in ("من", "from", "men", "min") and nxt is not None
                      and nxt.hit is not None and not nxt.hit.excluded)
        if (place_stop or from_place) and _name_like(tokens, run):
            return set(run)
    # (5) "order for Zainab": the run after for/لـ at the end of a product segment
    for s in segs:
        if not s.product or s.field is not None:
            continue
        for i, k in enumerate(s.toks):
            if tokens[k].text in ("for", "باسم") and 1 <= len(s.toks) - i - 1 <= 3:
                run = s.toks[i + 1:]
                if _name_like(tokens, run):
                    return set(run)
    return set()


def _slice_tokens(text, tokens, toks):
    """Original text of a token-index list; non-contiguous parts joined by a space."""
    if not toks:
        return ""
    runs = []
    cur = [toks[0]]
    for k in toks[1:]:
        if k == cur[-1] + 1:
            cur.append(k)
        else:
            runs.append(cur)
            cur = [k]
    runs.append(cur)
    parts = [squeeze(text[tokens[r[0]].os:tokens[r[-1]].oe]) for r in runs]
    return " ".join(p for p in parts if p)


def _is_cut_word(tokens, toks, j):
    """A clear chatter clause starts at toks[j] (payment/timing/call/thanks or a
    product word in context).  Never right after a landmark noun or trigger,
    so landmark names (مطعم اليوم، صيدلية رجاء) are kept."""
    t = tokens[toks[j]]
    if t.kind != WORD:
        return False
    if j > 0:
        p = tokens[toks[j - 1]]
        if p.kind == WORD and (is_landmark_noun(p.text) or is_trigger(p.text)):
            return False
    w = t.text
    if w in _ADDR_CUT or (w[:1] == "و" and w[1:] in _ADDR_CUT):
        return True
    if w == "ان" and j + 1 < len(toks) and tokens[toks[j + 1]].text == "شاء":
        return True
    return _is_order_at(tokens, toks, j)


def _build_address(text, tokens, segs, name_toks, winner_hits, hits, cue_resolved=False,
                   notes=None):
    """Address = what is left of the message in order, minus labels, phones,
    name, greetings/chatter/product talk and the winning governorate mention (D8)."""
    remove = set(name_toks)
    for h in winner_hits:
        if h.tier == 1 and not h.landmark:
            remove.update(range(h.t0, h.t1))
    cue_seg = None
    if cue_resolved and winner_hits:
        # one governorate carries the delivery cue: keep only the delivery side
        # (drop "انا بالحلة بس ابعثوه للناصرية" before the area) (F37)
        wh = winner_hits[0]
        cue_seg = wh.seg
        if cue_seg is not None:
            remove.update(k for k in cue_seg.toks if k < wh.t1)
        winner_govs = {h.gov for h in winner_hits}
        for h in hits:
            if not h.excluded and h.t1eq and h.gov not in winner_govs:
                remove.update(range(h.t0, h.t1))
    pieces = []
    all_kept = []
    for s in segs:
        if s.field in ("name", "phone"):
            continue
        toks = list(s.toks)
        has_place = any(tokens[k].hit is not None and not tokens[k].hit.excluded for k in toks)
        if s.product:
            first = next((i for i, k in enumerate(toks)
                          if tokens[k].hit is not None and not tokens[k].hit.excluded), None)
            if first is None:
                continue
            toks = toks[first:]
        if s.q and not has_place:
            continue
        words = [tokens[k].text for k in toks]
        # recipient / courier notes ("اخوي اسمه حيدر هو يستلم") without a place
        if not has_place and any(w in _NOTE_WORDS for w in words):
            if notes is not None:
                notes.append(_slice_tokens(text, tokens, toks))
            continue
        # phone-correction chatter ("عفوا الرقم غلط الصحيح") and phone talk
        # ("هذا رقم اخوي") without a place are not address
        if not has_place and (_has(words, _CORRECTION) or _has(words, _PHONE_INTRO)):
            continue
        # a segment that opens with a chatter clause and names no place is chatter
        if not has_place and toks and _is_cut_word(tokens, toks, 0):
            continue
        toks = [k for k in toks if k not in remove]
        lo, hi = 0, len(toks)
        while lo < hi and _trim_tok(text, tokens[toks[lo]]):
            lo += 1
        # cut a trailing chatter clause (payment/timing/call/product in context)
        for j in range(lo, hi):
            if _is_cut_word(tokens, toks, j):
                hi = j
                # a quantity right before a product word goes too ("2 قطعة")
                if hi > lo and tokens[toks[hi - 1]].kind == NUM and _is_order_at(tokens, toks, j):
                    hi -= 1
                break
        while hi > lo and _trim_tok(text, tokens[toks[hi - 1]]):
            # never trim a landmark's own name ("قرب مطعم اليوم")
            if hi - 2 >= lo:
                p = tokens[toks[hi - 2]]
                if p.kind == WORD and (is_landmark_noun(p.text) or is_trigger(p.text)):
                    break
            hi -= 1
        toks = toks[lo:hi]
        if not toks:
            continue
        if not any(tokens[k].kind == WORD for k in toks) and s.field not in ("addr", "gov"):
            continue
        piece = _slice_tokens(text, tokens, toks)
        if piece:
            pieces.append(piece)
            all_kept.extend(toks)
    if not pieces:
        return None

    # capital-only / governorate-only / filler-only address -> None (D8)
    def _empty_content(k):
        t = tokens[k]
        return (t.hit is not None and not t.hit.landmark and t.hit.t1eq) \
            or (t.kind == WORD and (_trim_tok(text, t) or t.text in _CHATTER))
    if all(_empty_content(k) for k in all_kept):
        return None
    if not any(tokens[k].kind == WORD for k in all_kept):
        return None
    sep = "، " if any(is_arabic_letter(c) for c in "".join(pieces)) else ", "
    return sep.join(pieces)


def _trim_tok(text, t):
    if t.kind != WORD:
        return False
    w = t.text
    if w in _TRIM:
        return True
    for p in ("و", "لل", "ل"):
        if w.startswith(p) and len(w) - len(p) >= 3 and w[len(p):] in (_HELPER | _PHONE_INTRO):
            return True
    if w.startswith("و") and len(w) > 3 and w[1:] in _TRIM:
        return True
    return text[t.os:t.oe] in _TRIM_ORIGINAL
