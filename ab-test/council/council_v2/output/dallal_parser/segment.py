"""Tokenisation, label detection and segmentation (D6).

Tokens carry spans in both the folded copy and the original text, so any
token range can be sliced back out of the original message as typed.

Segments = lines, split further at ``،`` ``,`` ``/`` ``|`` ``;`` ``؛`` ``!``
``?``, at `` - `` (dash with spaces), at ``.`` followed by whitespace (not
after st/rd/no or between digits), at phone numbers, and at labels.  Each
segment remembers the label field it belongs to (name/phone/gov/addr/None).
"""
from . import gazetteer as G
from .normalize import fold_simple, is_arabic_letter, is_latin_letter

WORD, NUM, PHONE, NL, SEP, Q, COLON = "word", "num", "phone", "nl", "sep", "q", "colon"


class Token:
    __slots__ = ("kind", "text", "ns", "ne", "os", "oe", "line", "idx", "phone",
                 "label", "label_field", "hit")

    def __init__(self, kind, text, ns, ne, omap, line):
        self.kind = kind
        self.text = text
        self.ns = ns
        self.ne = ne
        self.os = omap[ns] if omap else 0
        self.oe = (omap[ne - 1] + 1) if omap else 0
        self.line = line
        self.idx = -1
        self.phone = None        # PhoneHit for PHONE tokens
        self.label = False       # token belongs to a label
        self.label_field = None
        self.hit = None          # gazetteer Hit covering this token

    def __repr__(self):
        return "<%s %r>" % (self.kind, self.text)


def _split_alnum(s, start):
    """Split an alnum run into word/num pieces.  Latin words with fewer than
    3 digits stay whole (Arabizi: 3li, jami3)."""
    has_digit = any("0" <= c <= "9" for c in s)
    if not has_digit:
        return [(WORD, start, start + len(s))]
    if not any(c.isalpha() for c in s):
        return [(NUM, start, start + len(s))]
    ndig = sum(1 for c in s if "0" <= c <= "9")
    if ndig < 3 and not any(is_arabic_letter(c) for c in s):
        return [(WORD, start, start + len(s))]
    out = []
    cur = None
    cs = 0
    for k, c in enumerate(s):
        cls = NUM if "0" <= c <= "9" else WORD
        if cls != cur:
            if cur is not None:
                out.append((cur, start + cs, start + k))
            cur, cs = cls, k
    out.append((cur, start + cs, start + len(s)))
    return out


def tokenize(norm, omap, phone_hits):
    tokens = []
    phone_at = {h.start: h for h in phone_hits}
    n = len(norm)
    i = 0
    line = 0

    def add(kind, s, e):
        t = Token(kind, norm[s:e], s, e, omap, line)
        t.idx = len(tokens)
        tokens.append(t)
        return t

    while i < n:
        if i in phone_at:
            h = phone_at[i]
            t = add(PHONE, h.start, h.end)
            t.phone = h
            i = h.end
            continue
        c = norm[i]
        if c == "\n":
            add(NL, i, i + 1)
            line += 1
            i += 1
            continue
        if c.isalnum():
            j = i
            while j < n and norm[j].isalnum() and j not in phone_at:
                j += 1
            for kind, s, e in _split_alnum(norm[i:j], i):
                add(kind, s, e)
            i = j
            continue
        prev = norm[i - 1] if i > 0 else " "
        nxt = norm[i + 1] if i + 1 < n else " "
        if c in ",،|;؛!\\":
            add(SEP, i, i + 1)
        elif c == "/":
            if not ("0" <= prev <= "9" and "0" <= nxt <= "9"):
                add(SEP, i, i + 1)
        elif c in "?؟":
            add(Q, i, i + 1)
        elif c in ":=":
            add(COLON, i, i + 1)
        elif c == ".":
            last = tokens[-1].text if tokens else ""
            if nxt in " \n" and last not in ("st", "rd", "no", "dr", "mr", "mrs", "nb") \
                    and not ("0" <= prev <= "9" and "0" <= nxt <= "9"):
                add(SEP, i, i + 1)
        elif c in "-–—":
            if prev in " \n" and nxt in " \n":
                add(SEP, i, i + 1)
        i += 1
    return tokens


# ---------------------------------------------------------------- labels
def _fold_phrases(lst):
    out = []
    for p in lst:
        toks = tuple(fold_simple(p).replace("'", " ").split())
        if toks:
            out.append(toks)
    out.sort(key=len, reverse=True)
    return out


_LABELS = []
for _f, _lst in (("name", G.NAME_LABELS), ("phone", G.PHONE_LABELS), ("gov", G.GOV_LABELS),
                 ("city", G.CITY_LABELS), ("addr", G.ADDRESS_LABELS), ("intro", G.NAME_INTRO)):
    for _p in _fold_phrases(_lst):
        _LABELS.append((_p, _f))
_LABELS.sort(key=lambda x: len(x[0]), reverse=True)
_GENERIC_PHONE = set(_fold_phrases(G.GENERIC_PHONE_LABELS))
_LABELS_BY_FIRST = {}
for _p, _f in _LABELS:
    _LABELS_BY_FIRST.setdefault(_p[0], []).append((_p, _f))


def _next_content(tokens, j):
    """Index of the next non-colon token at/after j (same line), or None."""
    while j < len(tokens) and tokens[j].kind == COLON:
        j += 1
    if j < len(tokens) and tokens[j].kind != NL:
        return j
    return None


def _match_label_at(tokens, i):
    """Return (field, length) of a label starting at token i, or None."""
    t0 = tokens[i]
    if t0.kind != WORD or t0.hit is not None:
        return None
    w0 = t0.text
    cands = _LABELS_BY_FIRST.get(w0, [])
    if w0.startswith("و") and w0[1:] in _LABELS_BY_FIRST:
        cands = cands + _LABELS_BY_FIRST[w0[1:]]
    if not cands:
        return None
    best = None
    for phrase, field in cands:
        L = len(phrase)
        if i + L > len(tokens):
            continue
        ok = True
        for k in range(L):
            t = tokens[i + k]
            if t.kind != WORD:
                ok = False
                break
            w = t.text
            if k == 0 and w != phrase[0] and not (w.startswith("و") and w[1:] == phrase[0]):
                ok = False
                break
            if k > 0 and w != phrase[k]:
                ok = False
                break
        if ok and (best is None or L > len(best[1])):
            best = (field, phrase, L)
    return best


def detect_labels(tokens, line_starts, is_place_token, is_stop_word):
    """Mark label tokens.  Returns list of (start_idx, end_idx, field)."""
    labels = []
    i = 0
    n = len(tokens)
    while i < n:
        m = _match_label_at(tokens, i)
        if not m:
            i += 1
            continue
        field, phrase, L = m
        j = i + L
        nxt = _next_content(tokens, j)
        at_line_start = line_starts.get(tokens[i].line) == i
        colon_follows = j < n and tokens[j].kind == COLON
        valid = True
        if field == "phone":
            phone_next = nxt is not None and tokens[nxt].kind == PHONE
            if phrase in _GENERIC_PHONE or not at_line_start:
                valid = phone_next
        elif field == "city":
            valid = at_line_start or colon_follows
            field = "gov"
        elif field == "intro":
            # انا/اني X: only when X looks like a name (not من / ساكن / a place ...)
            valid = (nxt is not None and tokens[nxt].kind == WORD
                     and not is_stop_word(tokens[nxt].text) and not is_place_token(nxt))
            field = "name"
        elif field == "name":
            # "name" must be followed by something (avoid "name of the product?")
            valid = nxt is not None or colon_follows or True
        if valid:
            for k in range(i, j):
                tokens[k].label = True
                tokens[k].label_field = field
            labels.append((i, j, field))
            i = j
        else:
            i += 1
    return labels


class Segment:
    __slots__ = ("toks", "field", "line", "own_line", "after_phone", "before_phone",
                 "first_in_line", "product", "q", "idx", "carried")

    def __init__(self, field, line):
        self.toks = []          # token indices of content tokens (word/num)
        self.field = field
        self.line = line
        self.own_line = False
        self.after_phone = False
        self.before_phone = False
        self.first_in_line = False
        self.product = False
        self.q = False
        self.idx = -1
        self.carried = False    # field carried over from a label on a previous line

    def __repr__(self):
        return "<Seg %s %r>" % (self.field, self.toks)


def build_segments(tokens, labels):
    """Split tokens into segments, tracking the label field of each."""
    label_start = {s: (e, f) for s, e, f in labels}
    segs = []
    cur = None
    field = None
    pending_carry = None   # label with empty value at end of line -> next line
    label_had_value = False
    last_boundary_phone = False
    i = 0
    n = len(tokens)

    def close():
        nonlocal cur
        if cur is not None and cur.toks:
            cur.idx = len(segs)
            segs.append(cur)
        cur = None

    line = 0
    while i < n:
        t = tokens[i]
        if i in label_start:
            close()
            e, f = label_start[i]
            field = f
            label_had_value = False
            last_boundary_phone = False
            i = e
            continue
        if t.kind == NL:
            close()
            if field is not None and not label_had_value and field in ("name", "addr", "gov"):
                pending_carry = field
            else:
                pending_carry = None
            field = None
            last_boundary_phone = False
            line = t.line + 1
            i += 1
            continue
        if t.kind in (SEP, Q):
            if t.kind == Q and cur is not None:
                cur.q = True
            elif t.kind == Q and segs and segs[-1].line == t.line:
                segs[-1].q = True
            close()
            if field in ("name", "phone"):
                field = None
            i += 1
            continue
        if t.kind == COLON:
            i += 1
            continue
        if t.kind == PHONE:
            if cur is not None:
                cur.before_phone = True
            elif segs and segs[-1].line == t.line and segs[-1].field != "phone":
                # "العنوان، الاسم، 0770..." : the segment right before the phone
                # across a separator (، , - /) is still "before the phone" (F36)
                j = i - 1
                while j >= 0 and tokens[j].kind in (SEP, COLON):
                    j -= 1
                if j >= 0 and segs[-1].toks and segs[-1].toks[-1] == j:
                    segs[-1].before_phone = True
            close()
            if field == "phone":
                field = None
            label_had_value = True
            last_boundary_phone = True
            i += 1
            continue
        # content token
        if cur is None:
            f = field
            carried = False
            if f is None and pending_carry is not None:
                f = pending_carry
                carried = True
            cur = Segment(f, t.line)
            cur.carried = carried
            cur.after_phone = last_boundary_phone
            last_boundary_phone = False
            if carried and f == "name":
                pending_carry = None
        cur.toks.append(i)
        label_had_value = True
        i += 1
    close()
    # line-level properties
    by_line = {}
    for s in segs:
        by_line.setdefault(s.line, []).append(s)
    for line_segs in by_line.values():
        line_segs[0].first_in_line = True
        if len(line_segs) == 1:
            line_segs[0].own_line = True
    return segs
