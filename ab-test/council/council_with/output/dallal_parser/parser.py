"""parse_order: turn one customer DM into a clean order record.

Pipeline (see README "How it works"):
  clean text -> phones (removed from the text) -> segments -> noise stripped
  -> labels -> roles (name / address / notes) -> governorate -> address.
Precision over recall: when unsure, a field is None or flagged, never guessed.
"""

import logging
import re
from dataclasses import dataclass, field

from . import lexicon as lx
from .governorate import Candidate, accept, find_mentions, proclitic_variants, resolve
from .names import GIVEN_NAMES
from .normalize import clean_text, fold, has_letters
from .phones import extract_from_line
from .schema import CORE_FIELDS, empty_result

log = logging.getLogger("dallal_parser")
log.addHandler(logging.NullHandler())

MAX_INPUT_CHARS = 4000


# --- lexicon helpers ---------------------------------------------------------

def _phrases(words):
    """Folded phrases grouped by length, for longest-first prefix matching."""
    by_len = {}
    for w in words:
        k = tuple(fold(t) for t in w.split() if fold(t))
        if k:
            by_len.setdefault(len(k), set()).add(k)
    return sorted(by_len.items(), reverse=True)


def _word_set(words):
    return {fold(w) for w in words if " " not in w}


_LABELS = {kind: _phrases(words) for kind, words in lx.LABELS.items()}
_EDGE_NOISE = _phrases(lx.EDGE_NOISE)
_WHOLE_NOISE = _phrases(lx.WHOLE_NOISE + lx.EDGE_NOISE)
_NAME_LIKE_GREETINGS = _word_set(lx.NAME_LIKE_GREETINGS)
_COURTESY_TAILS = _word_set(lx.COURTESY_TAILS) | _word_set(lx.EDGE_NOISE) | _word_set(lx.WHOLE_NOISE)
_PRODUCT = _word_set(lx.PRODUCT_WORDS)
_CORRECTION = _word_set(lx.PHONE_CORRECTION)
_DELIVERY = _word_set(lx.DELIVERY_WORDS)
_NOISE_WORDS = _word_set(lx.EDGE_NOISE) | _word_set(lx.WHOLE_NOISE)
_ADDRESS_KW = _word_set(lx.ADDRESS_KEYWORDS)
_LANDMARK = _phrases(lx.LANDMARK_MARKERS)
_GLUE = _word_set(lx.NAME_GLUE)
_NAME_TRAILERS = _word_set(lx.NAME_TRAILERS)
_GIVEN = {fold(n) for n in GIVEN_NAMES}
_ARABIZI_SIZE = re.compile(r"^(\d+(x|k|pcs?|xl|xxl|l|m|s)|x\d+|[a-z]{1,2}\d+|.*\d\d.*)$", re.I)


def _verified(tokens):
    """Positive evidence: the line contains a common given name."""
    for t in tokens:
        f = fold(t)
        if f in _GIVEN or (f.startswith("ال") and f[2:] in _GIVEN) or any(v in _GIVEN for v in proclitic_variants(f)[1:]):
            return True
    return False
_PHONE_LABEL_WORDS = _word_set(lx.LABELS["phone"] + lx.LABELS["phone2"]) - {"no", "or", "او"}
_ALL_LABEL_WORDS = {t for ph in lx.LABELS.values() for w in ph for t in [fold(x) for x in w.split()]}
_NOT_NAME = (
    (_word_set(lx.EDGE_NOISE) | _word_set(lx.WHOLE_NOISE)) - _NAME_LIKE_GREETINGS | _PRODUCT | _ADDRESS_KW
    | _word_set(lx.NOT_NAME_WORDS)
    | {fold(w) for w in lx.LABELS["phone"] + lx.LABELS["governorate"] + lx.LABELS["address"]
       + lx.LABELS["area"] if " " not in w}
)


def _in(token_fold, wordset):
    if token_fold in wordset:
        return True
    for v in proclitic_variants(token_fold):
        if v in wordset or (v.startswith("ال") and v[2:] in wordset):
            return True
    return token_fold.startswith("ال") and token_fold[2:] in wordset


def _match_prefix(folded, phrases, start=0):
    for n, keys in phrases:
        if tuple(folded[start:start + n]) in keys:
            return n
    return 0


def _match_suffix(folded, phrases):
    for n, keys in phrases:
        if n <= len(folded) and tuple(folded[len(folded) - n:]) in keys:
            return n
    return 0


def _is_symbol_token(tok):
    return not any(ch.isalnum() for ch in tok)


def _strip_symbols(tok):
    """Drop edge punctuation from a display token (emoji are gone already)."""
    return tok.strip(" .,،؛;:!?؟'\"()[]{}<>«»\\|-_=+*~`^…•·")


def _is_address_kw(display_token):
    return _in(fold(display_token), _ADDRESS_KW)


# --- segments ------------------------------------------------------------------

@dataclass
class Seg:
    tokens: list
    order: int
    line: int
    role: str = ""  # name | address | notes | unclassified
    label: str = ""
    mentions: list = field(default_factory=list)
    product: bool = False
    has_kw: bool = False
    landmark: str = None
    prefix_address: bool = False  # remainder of a governorate-labelled value
    no_name: bool = False  # value of a rejected label: may be address/notes, never the name

    @property
    def folded(self):
        return [fold(t) for t in self.tokens]

    @property
    def text(self):
        return " ".join(self.tokens)


_SEP = re.compile(
    r"[،,؛;|•\n]"
    r"|(?<![0-9])\s+[/\-–—]\s+(?![0-9])"  # spaced ' / ' and ' - '
    r"|(?<=[^\s0-9])/(?=[^\s0-9])"  # 'baghdad/zayona'
    r"|(?<=[^\s0-9])[.؟?!]+(?=\s|$)"  # sentence ends: 'rahimawa. name: Lana'
)
_COLON = re.compile(r"\s*[:：=]+\s*")


_STRONG_LABELS = {
    tuple(fold(t) for t in w.split())
    for w in ("الاسم", "الاسم الثلاثي", "الاسم الكامل", "العنوان", "المحافظة", "المنطقة", "اقرب نقطة دالة",
              "أقرب نقطة دالة", "المحافظة والمنطقة")
}
_SPLIT_KINDS = ("name", "governorate", "governorate_area", "city", "area", "address", "landmark", "phone",
                "phone2")


def _split_embedded_labels(tokens):
    """'الاسم: علي الرقم: ... المحافظة: بغداد العنوان: ...' on one line -> one part per label."""
    folded = [fold(t) for t in tokens]
    cuts = []
    for i in range(1, len(tokens)):
        for kind in _SPLIT_KINDS:
            n = _match_prefix(folded, _LABELS[kind], i)
            if not n:
                continue
            colon = i + n < len(tokens) and tokens[i + n] == ":"
            strong = tuple(folded[i:i + n]) in _STRONG_LABELS and i + n < len(tokens)
            if colon or strong:
                cuts.append(i)
                break
    parts, prev = [], 0
    for c in cuts:
        if c > prev:
            parts.append(tokens[prev:c])
            prev = c
    parts.append(tokens[prev:])
    return [p for p in parts if p]


def _segments(lines):
    segs = []
    for li, line in enumerate(lines):
        for part in _SEP.split(line):
            part = _COLON.sub(" : ", part).strip()
            if part:
                for toks in _split_embedded_labels(part.split()):
                    segs.append(Seg(toks, 0, li))
    return segs


def _noise_fold(tok):
    f = fold(tok)
    for v in proclitic_variants(f)[1:]:
        if v in _NOISE_WORDS:
            return v  # 'وشكرا' -> 'شكرا'
    return f


def _strip_noise(seg):
    """Remove greetings / thanks / acknowledgements at the edges of a segment."""
    toks = list(seg.tokens)
    while toks:
        folded = [_noise_fold(t) for t in toks]
        if _is_symbol_token(toks[0]) and toks[0] != ":":
            toks.pop(0)
            continue
        n = _match_prefix(folded, _EDGE_NOISE)
        if n:
            toks = toks[n:]
            continue
        # هلا / زين / سلام are also names: strip only if what follows is not a name
        if folded[0] in _NAME_LIKE_GREETINGS:
            nxt = toks[1] if len(toks) > 1 else None
            if nxt is None or _is_symbol_token(nxt) or fold(nxt) in _COURTESY_TAILS:
                toks.pop(0)
                if nxt is not None and fold(nxt) in _COURTESY_TAILS and fold(nxt) not in _NAME_LIKE_GREETINGS:
                    toks.pop(0)  # 'هلا بيكم'
                continue
        break
    while toks:
        folded = [_noise_fold(t) for t in toks]
        if _is_symbol_token(toks[-1]) and toks[-1] != ":":
            toks.pop()
            continue
        n = _match_suffix(folded, _EDGE_NOISE)
        if n and n < len(toks):
            toks = toks[:-n]
            continue
        break
    toks = [t for t in (_strip_symbols(t) if t != ":" else t for t in toks) if t]
    if toks and _match_prefix([_noise_fold(t) for t in toks], _WHOLE_NOISE) == len(toks):
        toks = []
    if toks and all(t == ":" for t in toks):
        toks = []
    seg.tokens = toks
    return seg


def _find_label(seg):
    """Return (kind, value_tokens, explicit_separator) or (None, None, False)."""
    best = (0, None)
    if not seg.tokens:
        return None, None, False
    base = seg.folded
    for first in proclitic_variants(base[0]):
        folded = [first] + base[1:]
        for kind, phrases in _LABELS.items():
            n = _match_prefix(folded, phrases)
            if n > best[0]:
                best = (n, kind)
    n, kind = best
    if not n:
        return None, None, False
    rest = seg.tokens[n:]
    explicit = bool(rest) and rest[0] in (":", "-")
    while rest and rest[0] in (":", "-"):
        rest = rest[1:]
    if not explicit and kind not in lx.SPACE_OK_LABELS:
        return None, None, False
    if not explicit and n == len(seg.tokens):
        explicit = True  # a label alone on its line: value on the next line
    if not explicit and kind in ("phone", "phone2"):
        # 'رقم الدار 12' is an address, not a phone label
        return None, None, False
    return kind, rest, explicit


# --- name shape ---------------------------------------------------------------

_ARABIC = re.compile("[؀-ۿ]")


def _name_units(tokens):
    """Count name tokens with 'عبد X', 'ابو X', 'ام X' as one unit."""
    units, i = 0, 0
    while i < len(tokens):
        if fold(tokens[i]) in _GLUE and i + 1 < len(tokens):
            i += 2
        else:
            i += 1
        units += 1
    return units


def _trim_name(tokens):
    """Drop trailing 'من' / 'ساكن' / 'ورقمها' left over after a split."""
    while tokens and (_in(fold(tokens[-1]), _NAME_TRAILERS) or _in(fold(tokens[-1]), _PHONE_LABEL_WORDS)):
        tokens = tokens[:-1]
    return tokens


_NAME_TOKEN_BAD = re.compile("[^\\w'’.\\-\u064b-\u065f\u0670]|_")


def _name_shaped(tokens, mentions=(), max_units=5):
    if not tokens or not 1 <= _name_units(tokens) <= max_units or len(" ".join(tokens)) > 60:
        return False
    for t in tokens:
        f = fold(t)
        if not any(ch.isalpha() for ch in t) or _NAME_TOKEN_BAD.search(t):
            return False
        if sum(ch.isalnum() for ch in t) < 2 and not t.endswith("."):
            return False  # 'و', 'b'
        if f in _ALL_LABEL_WORDS:
            return False
        if any(ch.isdigit() for ch in t):
            # digits only as Arabizi letters ('3li', '7sen'), never sizes / models
            if (_ARABIC.search(t) or len(re.findall("[A-Za-z]", t)) < 2 or _ARABIZI_SIZE.match(t)
                    or re.search("[014]", t)):
                return False
        if f in _NOT_NAME or _in(f, _ADDRESS_KW) or _in(f, _PRODUCT):
            return False
        if t == ":":
            return False
    if any(not m.gated and not m.reference for m in mentions):
        return False
    return True


# --- main ---------------------------------------------------------------------

def parse_order(text):
    """Parse one customer message (or several joined with '\\n').

    Returns a dict with a fixed set of keys; see README / SCHEMA_KEYS.
    ``None`` is treated as an empty message; other non-str types raise TypeError.
    """
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise TypeError("parse_order expects str, got %s" % type(text).__name__)

    result = empty_result()
    warnings = []

    def warn(code, detail=""):
        warnings.append({"code": code, "detail": detail})

    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
        warn("input_truncated", "only the first %d characters were parsed" % MAX_INPUT_CHARS)

    clean = clean_text(text)
    if not has_letters(clean) and not re.search("[0-9]", clean):
        warn("empty_input", "no letters or digits in the message")
        return _finish(result, warnings)

    # 1. phones ---------------------------------------------------------------
    lines = clean.split("\n")
    valid, invalid = [], []
    prev_label = ""
    for li, line in enumerate(lines):
        found = extract_from_line(line)
        for pm in found.valid:
            kind = _phone_label_kind(line[:pm.start]) or (prev_label if not line[:pm.start].strip() else "")
            valid.append((li, pm.start, pm, kind))
        for ip in found.invalid:
            invalid.append(ip)
        for s, e in sorted(found.spans, reverse=True):
            line = line[:s] + " ، " + line[e:]
        lines[li] = line
        stripped = line.replace("،", " ").strip()
        prev_label = _phone_label_kind(stripped) if stripped and _only_phone_label(stripped) else (
            prev_label if not stripped else "")

    _assign_phones(result, valid, invalid, warn)

    # 2. segments, noise, labels ----------------------------------------------
    segs, seen = [], set()
    for seg in (_strip_noise(x) for x in _segments(lines)):
        key = tuple(fold(t) for t in seg.tokens)
        if seg.tokens and key not in seen:  # a resent order: keep the first copy
            seen.add(key)
            segs.append(seg)
    for i, s in enumerate(segs):
        s.order = i

    out = []  # segments after label handling (may split / merge)
    name_label_value = None
    gov_label_cands = []
    pending = None
    for s in segs:
        kind, value, explicit = _find_label(s)
        if kind is None and pending:
            kind, value, explicit = pending, s.tokens, True
        pending = None
        if kind in ("phone", "phone2"):
            if not value:
                continue  # label whose number was already extracted
            kind = None  # text after a phone label but no number: ordinary text
        if kind and not value:
            pending = kind
            continue
        if kind in ("name", "intro"):
            value, rest = _split_place_off(value)
            value = _trim_name(value)
            ok = value and (_name_shaped(value) or (kind == "name" and explicit and _loose_name(value)))
            if rest:
                # 'الاسم: علي حسين بغداد الكرادة' / "I'm Ahmed from Najaf"
                out.append(Seg(rest, s.order + 0.5, s.line))
            if ok and kind == "name":
                name_label_value = Seg(value, s.order, s.line, role="name", label="name")
            elif ok:
                out.append(Seg(value, s.order, s.line, role="name", label="intro"))
            elif value:
                # 'اني ساكن بحي الجامعة قرب الجامع': not a name, but keep the text
                lead = 0
                while lead < len(value) and _in(fold(value[lead]), _NAME_TRAILERS):
                    lead += 1
                if value[lead:]:
                    out.append(Seg(value[lead:], s.order, s.line, no_name=True))
            continue
        if kind == "city":
            kind = "governorate"
        if kind in ("governorate", "governorate_area"):
            ms = [m for m in accept(find_mentions(value), value, labelled=True, is_keyword=_is_address_kw)
                  if not m.reference]
            if ms:
                m = ms[0]
                gov_label_cands.append(Candidate(m, s.order, True, label=True))
                rest = value[:m.start] + value[m.end:]
                rest = [t for t in rest if t not in (":", "-")]
                if rest:
                    out.append(Seg(rest, s.order, s.line, role="address", label=kind, prefix_address=True))
                continue
            out.append(Seg(value, s.order, s.line, no_name=True))  # 'المحافظة: مدري'
            continue
        if kind in ("area", "address", "landmark"):
            seg = Seg(value, s.order, s.line, role="address", label=kind)
            if kind == "landmark":
                seg.landmark = " ".join(value)
            out.append(seg)
            continue
        out.append(s)

    # 3. roles for unlabelled segments ----------------------------------------
    final = []
    for s in out:
        if s.role:
            s.mentions = accept(find_mentions(s.tokens), s.tokens, is_keyword=_is_address_kw)
            final.append(s)
            continue
        final.extend(_classify(s, out))

    # whole-segment personal-name collisions ('ميسان' on its own line) only
    # count as a place when nothing else in the message names a governorate
    other_strong = any(
        not m.gated and not m.reference for s in final if s.role == "address" for m in s.mentions
    )
    if other_strong:
        for s in final:
            if (s.role == "address" and s.mentions and not s.label
                    and all(m.whole and m.gated == "name" for m in s.mentions)):
                s.role, s.mentions = "name", []

    # 4. name -----------------------------------------------------------------
    _assign_name(result, final, name_label_value, warn)

    # 5. governorate ----------------------------------------------------------
    cands = list(gov_label_cands)
    for s in final:
        if s.role == "name" and not any(m.name_position for m in s.mentions):
            continue
        if s.role == "notes" and not s.product:
            continue
        for m in s.mentions:
            if s.product and (m.tier == "C" or m.gated):
                continue
            cands.append(Candidate(m, s.order, m.start == 0))
    res = resolve(cands)
    if res.governorate:
        result["governorate"] = res.governorate
        result["governorate_source"] = res.source
        result["governorate_raw"] = res.raw
        result["confidence"]["governorate"] = res.confidence
        for code, detail in res.warnings:
            warn(code, detail)

    # 6. address & landmark -----------------------------------------------------
    _assign_address(result, final, res, warn)

    # 7. notes ----------------------------------------------------------------
    result["notes"] = [s.text for s in final if s.role in ("notes", "unclassified") and s.text]
    log.debug("parsed: name=%r governorate=%r via %s", result["name"], result["governorate"],
              result["governorate_source"])
    return _finish(result, warnings)


def _split_place_off(tokens):
    """Split a name value at the first real place mention: (name, rest)."""
    found = find_mentions(tokens)
    strong = accept(list(found), tokens, is_keyword=_is_address_kw)
    ms = [m for m in found if not m.reference and (
        (m in strong and not m.gated)
        or m.start == 0 or _in(fold(tokens[m.start - 1]), _NAME_TRAILERS))]
    if not ms:
        return tokens, []
    return tokens[:ms[0].start], tokens[ms[0].start:]


def _loose_name(tokens):
    """Explicitly labelled names get a little more slack (up to 7 parts)."""
    return _name_shaped(tokens, max_units=7)


def _phone_label_kind(prefix):
    """Primary / secondary phone label right before a number, if any."""
    part = _SEP.split(prefix)[-1] if prefix else ""
    folded = [fold(t) for t in _COLON.sub(" ", part).split() if fold(t)]
    if not folded:
        return ""
    if any(_in(f, _CORRECTION) for f in folded[-4:]):
        return "corrected"  # 'عفوا غلط، الرقم الصحيح 0780...'
    for start in range(len(folded)):
        tail = folded[start:]
        for kind in ("phone2", "phone"):
            for n, keys in _LABELS[kind]:
                if n == len(tail) and tuple(tail) in keys:
                    return "secondary" if kind == "phone2" else "primary"
    return ""


def _only_phone_label(text):
    folded = [fold(t) for t in _COLON.sub(" ", text).split() if fold(t)]
    for kind in ("phone2", "phone"):
        for n, keys in _LABELS[kind]:
            if n == len(folded) and tuple(folded) in keys:
                return True
    return False


def _assign_phones(result, valid, invalid, warn):
    valid.sort(key=lambda v: (v[0], v[1]))
    primary = next((v for v in valid if v[3] == "corrected"), None) or next(
        (v for v in valid if v[3] == "primary"), None)
    if primary is None:
        primary = next((v for v in valid if v[3] != "secondary"), None) or (valid[0] if valid else None)
    ordered = ([primary] if primary else []) + [v for v in valid if v is not primary]
    phones = []
    for v in ordered:
        if v[2].number not in phones:
            phones.append(v[2].number)
    result["phones"] = phones
    result["invalid_phones"] = [{"raw": ip.raw, "reason": ip.reason} for ip in invalid]
    if primary:
        pm = primary[2]
        result["phone"] = pm.number
        result["confidence"]["phone"] = "medium" if (pm.adjacent_digits or pm.uncommon_prefix) else "high"
        if pm.uncommon_prefix:
            warn("uncommon_prefix", "%s uses the rare 076 prefix" % pm.number)
        if pm.adjacent_digits:
            warn("phone_adjacent_digits", "extra digits were written next to %s" % pm.number)
    if len(phones) > 1:
        warn("multiple_phones", "%d different numbers; primary %s" % (len(phones), phones[0]))
    for ip in invalid:
        warn("invalid_phone", "%s (%s)" % (ip.raw, ip.reason))


def _classify(s, segs):
    """Decide the role of one unlabelled segment; may split it in two."""
    if ":" in s.tokens and s.tokens[0] != ":":
        # 'دزوها على: كرار ستار' - an ad-hoc label; classify the parts
        parts, cur = [], []
        for t in s.tokens:
            if t == ":":
                if cur:
                    parts.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            parts.append(cur)
        out = []
        for k, p in enumerate(parts):
            out.extend(_classify(Seg(p, s.order + k / 100.0, s.line), segs))
        return out
    folded = s.folded
    raw = [m for m in find_mentions(s.tokens) if not m.reference]
    in_place = {i for m in raw if not m.gated for i in range(m.start, m.end)}
    product_at = [i for i, f in enumerate(folded) if i not in in_place and _in(f, _PRODUCT)]
    s.product = bool(product_at)
    if s.product:
        # 'اريد الطلب اسمي مرتضى جبار من الديوانية ...': keep what follows the chatter
        cut = _detail_start(s.tokens, product_at)
        if cut:
            head = Seg(s.tokens[:cut], s.order, s.line, role="notes", product=True)
            return [head] + _classify(Seg(s.tokens[cut:], s.order + 0.01, s.line, no_name=s.no_name), segs)
    s.mentions = accept(find_mentions(s.tokens), s.tokens, product=s.product, is_keyword=_is_address_kw)
    s.has_kw = any(_in(f, _ADDRESS_KW) for f in folded)
    if s.product and all(_in(folded[i], _DELIVERY) for i in product_at) and (
            any(not m.gated for m in raw) or any(_in(f, _ADDRESS_KW) for f in folded)):
        # 'توصيل لبيت عمي بالكوت حي الزهراء': a delivery address
        s.product = False
        s.mentions = accept(find_mentions(s.tokens), s.tokens, is_keyword=_is_address_kw)
        s.role = "address"
        return [s]
    if s.product:
        s.role = "notes"
        return [s]
    strong = [m for m in s.mentions if not m.reference]
    if strong:
        first = strong[0]
        if first.start > 0:
            left = s.tokens[:first.start]
            left_kind, left_value, _ = _find_label(Seg(left, s.order, s.line))
            name_part = _trim_name(left_value if left_kind == "name" and left_value else left)
            right = s.tokens[first.start:]
            if _name_shaped(name_part) and not any(_in(fold(t), _ADDRESS_KW) for t in left):
                right_has_more = any(_in(fold(t), _ADDRESS_KW) for t in right[first.end - first.start:]) or len(
                    [m for m in strong if m is not first]) > 0
                other_address = any(
                    x is not s and (x.has_kw or any(not m.reference for m in x.mentions))
                    for x in segs
                    if x.role in ("", "address")
                )
                if not right_has_more and len(right) == first.end - first.start and other_address:
                    # 'محمد جاسم البصرة' + a separate address line: the place sits in
                    # name position - weak evidence, keep the line as the name
                    first.name_position = True
                    s.role = "name"
                    s.mentions = [first]
                    return [s]
                name_seg = Seg(name_part, s.order, s.line, role="name")
                addr_seg = Seg(right, s.order, s.line, role="address")
                shift = first.start
                for m in s.mentions:
                    m.start -= shift
                    m.end -= shift
                addr_seg.mentions = [m for m in s.mentions if m.start >= 0]
                addr_seg.has_kw = any(_in(fold(t), _ADDRESS_KW) for t in right)
                return [name_seg, addr_seg]
        s.role = "address"
        return [s]
    if s.has_kw:
        s.role = "address"
        return [s]
    kind, value, _ = _find_label(s)
    if (kind in ("name", "intro") and value and not s.no_name and not _split_place_off(value)[1]
            and _name_shaped(_trim_name(value))):
        s.tokens = _trim_name(value)
        s.role = "name"
        s.label = "intro"
        return [s]
    if _name_shaped(s.tokens, s.mentions) and not s.no_name:
        s.role = "name"
        return [s]
    s.role = "unclassified"
    return [s]


def _detail_start(tokens, product_at):
    """Index where order details begin after product chatter, or 0."""
    last = max(product_at)
    for i in range(last + 1, len(tokens)):
        f = fold(tokens[i])
        is_label = any(_match_prefix([v] + [fold(t) for t in tokens[i + 1:]], _LABELS[k])
                       for v in proclitic_variants(f) for k in ("name", "intro"))
        if is_label:
            return i
    return 0


def _assign_name(result, segs, labelled, warn):
    # unclassified text right after an address line continues the address
    for i, s in enumerate(segs):
        if (s.role == "unclassified" and i > 0 and segs[i - 1].role == "address"
                and (segs[i - 1].line == s.line or (segs[i - 1].line == s.line - 1 and re.search("[0-9]", s.text)))):
            s.role = "address"  # only with an address signal (house / alley numbers)
    if labelled is not None:
        result["name"] = " ".join(labelled.tokens)
        result["confidence"]["name"] = "high"
        for i, s in enumerate(segs):
            if s.role == "name":
                # 'هەولێر، شۆڕش': text right after the address line is the area
                s.role = "address" if i > 0 and segs[i - 1].role == "address" else "notes"
        return
    cands = [s for s in segs if s.role == "name"]
    if not cands:
        return
    first_addr = next((s.order for s in segs if s.role == "address"), None)
    if len(cands) > 1 and first_addr is not None:
        # a short candidate right after the address continues it ('بغداد\nالبنوك')
        before = [c for c in cands if c.order < first_addr]
        if before:
            for c in cands:
                if c.order > first_addr and c not in before:
                    prev = segs[segs.index(c) - 1]
                    if prev.role == "address":
                        # only with an address signal; 'الدفع عند الاستلام' is chatter
                        same_line = prev.line == c.line  # 'البصرة - القبلة'
                        c.role = "address" if same_line or re.search("[0-9]", c.text) else "notes"
            cands = [s for s in segs if s.role == "name"]
    if len(cands) > 1:
        verified = [c for c in cands if _verified(c.tokens)]
        if len(verified) == 1:  # the other lines are chatter ('عليكم السلام')
            for c in cands:
                if c is not verified[0]:
                    c.role = "notes"
            cands = verified
    if len(cands) == 1:
        c = cands[0]
        result["name"] = " ".join(c.tokens)
        if not _verified(c.tokens):
            result["confidence"]["name"] = "low"
            warn("name_unverified", "'%s' contains no common given name; please confirm" % result["name"])
        elif len(c.tokens) >= 2:  # 'ام علي' / 'ابو مهدي' are full identifications
            result["confidence"]["name"] = "high"
        else:
            result["confidence"]["name"] = "medium"
            warn("name_single_word", "only one word was given as the name")
        if any(m.name_position for m in c.mentions):
            result["confidence"]["name"] = "low"
        return
    # several candidates: nearest before the first address segment (else first)
    if first_addr is not None and any(c.order < first_addr for c in cands):
        chosen = max((c for c in cands if c.order < first_addr), key=lambda c: c.order)
    else:
        chosen = cands[0]
    result["name"] = " ".join(chosen.tokens)
    result["confidence"]["name"] = "low"
    warn("name_uncertain", "several lines could be the name: %s" % " | ".join(" ".join(c.tokens) for c in cands))
    for c in cands:
        if c is not chosen:
            c.role = "notes"


def _assign_address(result, segs, res, warn):
    parts, landmark = [], None
    for s in segs:
        if s.role != "address":
            continue
        toks = list(s.tokens)
        if s.landmark:
            landmark = landmark or s.landmark
        # drop a leading governorate name that set the governorate
        if res.governorate:
            lead = [m for m in s.mentions
                    if m.start == 0 and m.strip_ok and not m.reference and m.governorate == res.governorate]
            if lead:
                toks = toks[lead[0].end:]
        toks = _trim_address(toks)
        if toks:
            parts.append(toks)
    if not parts:
        return
    if landmark is None:
        for toks in parts:
            folded = [fold(t) for t in toks]
            for i in range(len(folded)):
                n = _match_prefix(folded, _LANDMARK, i)
                if n and i + n < len(toks):
                    landmark = " ".join(toks[i + n:])
                    break
            if landmark:
                break
    address = " - ".join(" ".join(p) for p in parts)
    result["address"] = address
    result["landmark"] = landmark
    n_tokens = sum(len(p) for p in parts)
    if n_tokens < 2 and not landmark:
        result["confidence"]["address"] = "low"
        warn("address_short", "the address is only '%s'; ask for the area and nearest landmark" % address)
    else:
        result["confidence"]["address"] = "high"


_ADDR_EDGE_JUNK = {"و", "او", "or", "/", "&", "and", "+"}
_ADDR_LABEL_WORDS = {fold(w) for k in ("address", "area", "city", "governorate") for w in lx.LABELS[k]
                     if " " not in w}


def _trim_address(toks):
    """Drop connectors / phone labels / ':' left at the edges of an address part."""
    toks = [t for t in toks if t not in (":", "-", "/")]
    # cut at an inline phone label ('... رقم ابني', '... واتساب')
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if i > 0 and _in(fold(t), _PHONE_LABEL_WORDS) and len(toks) - i <= 3 and not _is_address_kw(nxt):
            toks = toks[:i]
            break

    def junk(t):
        f = fold(t)
        return f in _ADDR_EDGE_JUNK or _in(f, _PHONE_LABEL_WORDS) or _in(f, _NOISE_WORDS) or not any(
            ch.isalnum() for ch in t)

    while toks and (junk(toks[0]) or fold(toks[0]) in _ADDR_LABEL_WORDS):
        toks = toks[1:]
    while toks and junk(toks[-1]):
        toks = toks[:-1]
    return toks


def _finish(result, warnings):
    seen, uniq = set(), []
    for w in warnings:
        key = (w["code"], w["detail"])
        if key not in seen:
            seen.add(key)
            uniq.append(w)
    result["warnings"] = uniq
    result["missing"] = [f for f in CORE_FIELDS if result[f] is None]
    for f in CORE_FIELDS:
        if result[f] is None:
            result["confidence"][f] = None
    result["needs_followup"] = bool(
        result["missing"]
        or any(result["confidence"][f] == "low" for f in CORE_FIELDS)
        or any(w["code"] == "governorate_inferred" for w in uniq)
    )
    return result
