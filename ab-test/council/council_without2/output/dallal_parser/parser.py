"""Turn a free-form Instagram DM into a structured cash-on-delivery order."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from . import vocab
from .gazetteer import (
    CITY_KIND,
    GOVERNORATE_KIND,
    GOVERNORATES,
    GazetteerHit,
    find_places,
    governorate_alias_keys,
)
from .normalize import clean_text, has_arabic, make_key, norm
from .phones import PhoneMatch, find_phones

REVIEW, INFO = "review", "info"

# A label's value may be introduced by one of these.
_COLON = re.compile(r"[ \t]*[:：=]+|[ \t]+[\-–—]+(?=[ \t])")
# Everything allowed between the start of a line/segment and a START label.
_LINE_LEAD = re.compile(r"[\s\-*•·.)(\d]*")
_SEGMENT_BREAK = "\n،,;؛|.!?؟"
# Splits text into segments. Hyphens and slashes between letters/digits
# ("al-Mansour", "دار 5/12") are kept.
_SEPARATOR = re.compile(
    r"[\n،,;؛|]|[–—]|(?<![a-z0-9])-|-(?![a-z0-9])|(?<!\d)/|/(?!\d)|\.(?=\s|$)|[:：]"
)
_EDGE_PUNCT = " \t.!؟?\"'“”«»()[]{}*•·:-_~"
_TOKEN = re.compile(r"\S+")
_NAME_TOKEN = re.compile(r"^[^\W\d_]+(?:['\-][^\W\d_]+)*$")

# Address keywords that, right before a governorate name, make it part of a
# street or landmark name ("شارع بغداد", "فندق بابل") rather than the governorate.
_EMBED_BEFORE = frozenset(norm(w) for w in [
    "شارع", "حي", "جامع", "مسجد", "مستشفى", "فندق", "جسر", "سوق", "مدرسة", "ساحة", "مطعم", "مول",
    "جامعة", "مجمع", "كراج", "فلكة", "سيطرة", "street", "st", "road", "hotel", "hospital", "mosque",
    "school", "bridge", "market", "square", "university", "mall", "garage",
])
_EMBED_AFTER = frozenset(norm(w) for w in [
    "مول", "street", "st", "road", "rd", "hotel", "mall", "hospital", "mosque", "school", "bridge",
    "market", "square", "university", "garage", "tower",
])
_LANDMARK_LEADS = re.compile(
    "|".join([rf"(?<!\w)(?:[وب]?ال)?{norm(w)}(?!\w)" for w in ["قرب", "مقابل", "خلف", "جنب", "يم", "بجانب", "قريب", "بالقرب"]]
             + [r"(?<![a-z])(?:near|opposite|behind|next to|beside|across from)(?![a-z])"])
)
_FUZZY_KEYS = governorate_alias_keys()


@dataclass
class _Label:
    start: int
    end: int
    value_start: int
    field: str
    strength: str


@dataclass
class _Segment:
    start: int
    end: int
    tag: str | None = None
    hits: list[GazetteerHit] = field(default_factory=list)
    question: bool = False
    region: int | None = None  # index of the label region the segment came from


class _Work:
    """Clean text plus its matching key, with consumed spans blanked to newlines."""

    def __init__(self, clean: str):
        self.orig = clean
        self.clean = list(clean)
        self.key = list(make_key(clean))

    def consume(self, start: int, end: int) -> None:
        for i in range(start, end):
            self.clean[i] = "\n"
            self.key[i] = "\n"

    @property
    def key_str(self) -> str:
        return "".join(self.key)

    def text(self, start: int, end: int) -> str:
        return "".join(self.clean[start:end])

    def keytext(self, start: int, end: int) -> str:
        return "".join(self.key[start:end])


def _warn(warnings: list, code: str, fld: str, message: str, severity: str) -> None:
    warnings.append({"code": code, "field": fld, "severity": severity, "message": message})


# --------------------------------------------------------------------------- labels

def _at_segment_start(key: str, pos: int) -> bool:
    i = pos
    while i > 0 and key[i - 1] not in _SEGMENT_BREAK:
        i -= 1
    return _LINE_LEAD.fullmatch(key, i, pos) is not None


def _find_labels(key: str) -> list[_Label]:
    candidates: list[_Label] = []
    for pattern, fld, strength in vocab.LABEL_PATTERNS:
        for m in pattern.finditer(key):
            colon = _COLON.match(key, m.end())
            has_colon = colon is not None
            if strength == vocab.STRONG:
                ok = True
            elif strength == vocab.START:
                # "والعنوان كربلاء": a leading و starts a new clause, like a line break.
                ok = has_colon or _at_segment_start(key, m.start()) or bool(m.groupdict().get("waw"))
            elif strength == vocab.WEAK_NAME:
                ok = has_colon or _at_segment_start(key, m.start())
            else:  # COLON
                ok = has_colon
            if ok:
                value_start = colon.end() if colon else m.end()
                candidates.append(_Label(m.start(), m.end(), value_start, fld, strength))
    # Longest label wins on overlap ("رقم الهاتف" over "الهاتف", "انا من" over "انا").
    candidates.sort(key=lambda l: (-(l.end - l.start), l.start))
    chosen: list[_Label] = []
    for lab in candidates:
        if all(lab.end <= c.start or lab.start >= c.end for c in chosen):
            chosen.append(lab)
    chosen.sort(key=lambda l: l.start)
    return chosen


def _label_regions(work: _Work, labels: list[_Label]) -> list[tuple[int, int, str, str]]:
    """(start, end, field, strength) of each label's value."""
    key = work.key_str
    regions = []
    for idx, lab in enumerate(labels):
        next_start = labels[idx + 1].start if idx + 1 < len(labels) else len(key)
        nl = key.find("\n", lab.value_start)
        end = min(next_start, nl if nl != -1 else len(key))
        start = lab.value_start
        if not key[start:end].strip() and end == nl and nl < next_start:
            # Template style: "الاسم:" on one line, the value on the next.
            orig_nl = work.orig.find("\n", lab.end)
            if orig_nl != -1 and orig_nl <= nl:
                line_start = orig_nl + 1
                while line_start < len(key) and key[line_start] in " \n" and line_start < next_start:
                    line_start += 1
                line_end = key.find("\n", line_start)
                line_end = len(key) if line_end == -1 else line_end
                if line_start < next_start and work.orig.rfind("\n", 0, line_start) == orig_nl:
                    start, end = line_start, min(line_end, next_start)
        regions.append((start, end, lab.field, lab.strength))
    return regions


# --------------------------------------------------------------------------- segments

def _split_segments(work: _Work, regions) -> list[_Segment]:
    key = work.key_str
    segments: list[_Segment] = []
    pos = 0
    bounds = [(m.start(), m.end()) for m in _SEPARATOR.finditer(key)] + [(len(key), len(key))]
    for sep_start, sep_end in bounds:
        seg = _trim(work, pos, sep_start)
        if seg:
            tag = region = None
            for idx, (r_start, r_end, fld, strength) in enumerate(regions):
                if r_start <= seg[0] < r_end:
                    tag = "weak_name" if strength == vocab.WEAK_NAME else fld
                    region = idx
                    break
            raw = work.orig[pos:sep_start]
            segments.append(_Segment(seg[0], seg[1], tag, question="?" in raw or "؟" in raw, region=region))
        pos = sep_end
    return segments


def _trim(work: _Work, start: int, end: int) -> tuple[int, int] | None:
    while start < end and work.clean[start] in _EDGE_PUNCT + "\n":
        start += 1
    while end > start and work.clean[end - 1] in _EDGE_PUNCT + "\n":
        end -= 1
    return (start, end) if start < end else None


def _tokens(work: _Work, start: int, end: int) -> list[tuple[int, int, str]]:
    """Tokens as (start, end, key) with edge punctuation removed."""
    out = []
    for m in _TOKEN.finditer(work.keytext(start, end)):
        s, e = start + m.start(), start + m.end()
        while s < e and work.key[s] in _EDGE_PUNCT:
            s += 1
        while e > s and work.key[e - 1] in _EDGE_PUNCT:
            e -= 1
        if s < e:
            out.append((s, e, work.keytext(s, e)))
    return out


def _strip_edges(work: _Work, seg: _Segment, words: frozenset) -> _Segment | None:
    toks = _tokens(work, seg.start, seg.end)
    while toks and toks[0][2] in words:
        toks.pop(0)
    while toks and toks[-1][2] in words:
        toks.pop()
    if not toks:
        return None
    return _Segment(toks[0][0], toks[-1][1], seg.tag, [h for h in seg.hits if h.start >= toks[0][0] and h.end <= toks[-1][1]])


def _in_hit(pos: int, hits: list[GazetteerHit]) -> bool:
    return any(h.start <= pos < h.end for h in hits)


def _keyword_spans(work: _Work, start: int, end: int) -> list[tuple[int, int]]:
    return [(start + m.start(), start + m.end()) for m in vocab.ADDRESS_KEYWORD_RE.finditer(work.keytext(start, end))]


# --------------------------------------------------------------------------- names

def _name_token_ok(tok: str) -> bool:
    return (
        _NAME_TOKEN.match(tok) is not None
        and tok not in vocab.NAME_STOP
        and tok not in vocab.EDGE_WORDS
        and tok not in vocab.LABEL_WORDS
        and not (re.search("[a-z]", tok) and len(tok) < 2)
    )


def _take_name(work: _Work, seg: _Segment, hits: list[GazetteerHit]) -> tuple[tuple[int, int] | None, int]:
    """Leading name tokens of a labelled value -> (span or None, index where the rest starts)."""
    kw = _keyword_spans(work, seg.start, seg.end)
    taken = []
    for s, e, tok in _tokens(work, seg.start, seg.end):
        if len(taken) == 5 or not _name_token_ok(tok) or _in_hit(s, hits) or any(ks <= s < ke for ks, ke in kw):
            break
        taken.append((s, e))
    if not taken:
        return None, seg.start
    return (taken[0][0], taken[-1][1]), taken[-1][1]


def _is_name_candidate(work: _Work, seg: _Segment) -> bool:
    toks = [t for _, _, t in _tokens(work, seg.start, seg.end)]
    if not 1 <= len(toks) <= 5 or seg.hits or _keyword_spans(work, seg.start, seg.end):
        return False
    if not all(_name_token_ok(t) for t in toks):
        return False
    first = toks[0]
    # Unknown places usually start with the article (البنوك, الضباط); first names don't.
    if has_arabic(first) and first.startswith("ال") and not first.startswith("الله"):
        return False
    if len(toks) == 1 and len(first) < 3:
        return False
    return True


def _format_name(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(_EDGE_PUNCT)
    if not has_arabic(text):
        text = " ".join(w[:1].upper() + w[1:].lower() if w.lower() not in ("al", "el", "bin", "ibn") else w.lower()
                        for w in text.split())
        text = re.sub(r"\b(al|el)-(\w)", lambda m: m.group(1).capitalize() + "-" + m.group(2).upper(), text,
                      flags=re.IGNORECASE)
    return text


# --------------------------------------------------------------------------- governorate

def _is_embedded(work: _Work, hit: GazetteerHit) -> bool:
    before = work.keytext(max(0, hit.start - 20), hit.start).split()
    after = work.keytext(hit.end, min(len(work.key), hit.end + 20)).split()
    return bool(before and before[-1].strip(_EDGE_PUNCT) in _EMBED_BEFORE) or bool(
        after and after[0].strip(_EDGE_PUNCT) in _EMBED_AFTER
    )


def _fuzzy_governorate(work: _Work, segs: list[_Segment]) -> str | None:
    for seg in segs:
        toks = [t for _, _, t in _tokens(work, seg.start, seg.end)]
        grams = toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]
        for g in grams:
            if len(g) < 4:
                continue
            match = difflib.get_close_matches(g, _FUZZY_KEYS.keys(), n=1, cutoff=0.8)
            if match:
                return _FUZZY_KEYS[match[0]]
    return None


# --------------------------------------------------------------------------- main entry

def parse_order(text: str) -> dict:
    """Extract name, phone, governorate and address from a customer DM.

    Never raises on odd input; problems are reported in ``warnings`` /
    ``missing`` and summarised by ``needs_review``.
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_order expects str, got {type(text).__name__}")

    warnings: list[dict] = []
    work = _Work(clean_text(text))

    # 1. Phones first: they are the most reliable anchor and act as separators.
    phones, bad_numbers = find_phones(work.orig)
    for p in phones:
        work.consume(p.start, p.end)
    for b in bad_numbers:
        work.consume(b.start, b.end)

    # 2. Greetings ("السلام عليكم") would otherwise look like names.
    for pattern in vocab.GREETING_PATTERNS:
        for m in pattern.finditer(work.key_str):
            work.consume(m.start(), m.end())

    # 3. Labels ("الاسم:", "عنواني", "my number is").
    labels = _find_labels(work.key_str)
    regions = _label_regions(work, labels)
    alt_phone_ids = _alt_phone_ids(work, labels, phones)
    for lab in labels:
        work.consume(lab.start, lab.value_start)

    # 4. Segments, with place mentions attached.
    hits = find_places(work.key_str)
    segments = _split_segments(work, regions)
    for seg in segments:
        seg.hits = [h for h in hits if h.start >= seg.start and h.end <= seg.end]

    name_span: tuple[int, int] | None = None
    surname_span: tuple[int, int] | None = None
    candidates: list[tuple[_Segment, bool]] = []  # (segment, came from an address line)
    address_segs: list[_Segment] = []
    notes: list[_Segment] = []
    queue = list(segments)
    untagged: list[_Segment] = []
    greeting_before: set[int] = set()  # segment starts that had "هلا"/"salam" stripped

    # 4a. Labelled names first, so unlabelled lines cannot override them.
    labelled_name = any(s.tag == vocab.NAME for s in queue)
    seen_regions: set[int] = set()
    for seg in queue:
        if seg.question and seg.tag not in (vocab.NAME, vocab.PHONE, vocab.PHONE_ALT):
            notes.append(seg)  # "توصلون للموصل؟" is a question, not an address
        elif seg.tag in (vocab.NAME, "weak_name"):
            if name_span is None:
                span, rest = _take_name(work, seg, seg.hits)
                if span and seg.tag == "weak_name":
                    whole = _Segment(span[0], span[1])
                    # "انا علي حسين" yes, "I'm interested" no: weak markers need two words.
                    if not _is_name_candidate(work, whole) or len(_tokens(work, *span)) < 2:
                        span, rest = None, seg.start
                if span:
                    name_span = span
                tail = _trim(work, rest, seg.end)
                if tail:
                    untagged.append(_Segment(tail[0], tail[1], None, [h for h in seg.hits if h.start >= tail[0]]))
            else:
                untagged.append(_Segment(seg.start, seg.end, None, seg.hits))
        elif seg.tag == vocab.SURNAME:
            span, rest = _take_name(work, seg, seg.hits)
            if span and surname_span is None:
                surname_span = span
            else:
                untagged.append(_Segment(seg.start, seg.end, None, seg.hits))
        elif seg.tag in (vocab.PHONE, vocab.PHONE_ALT, None):
            untagged.append(_Segment(seg.start, seg.end, None, seg.hits, seg.question))
        elif (not labelled_name and seg.region is not None and seg.region in seen_regions
              and _is_name_candidate(work, seg)):
            # "العنوان: بغداد الكرادة، علي حسين" - a bare name after the address.
            untagged.append(_Segment(seg.start, seg.end, None, seg.hits))
        else:
            address_segs.append(seg)
        if seg.region is not None:
            seen_regions.add(seg.region)

    # 4b. Unlabelled pieces.
    for seg in sorted(untagged, key=lambda s: s.start):
        if seg.question:
            notes.append(seg)
            continue
        stripped = _strip_edges(work, seg, vocab.FILLER | vocab.EDGE_WORDS)
        if stripped is None:
            continue
        lead = _tokens(work, seg.start, stripped.start)
        if lead and lead[-1][2] in vocab.NAME_LIKE_GREETINGS:
            greeting_before.add(stripped.start)
        seg = stripped
        kw = _keyword_spans(work, seg.start, seg.end)
        if seg.hits or kw:
            # "علي حسين بغداد الكرادة": a name glued to the front of an address.
            # Only split before a known place, never before a mere keyword.
            if seg.hits and name_span is None:
                first_place = seg.hits[0].start
                prefix = _trim(work, seg.start, first_place)
                if prefix and not any(k[0] < first_place for k in kw):
                    pseg = _Segment(prefix[0], prefix[1])
                    if _is_name_candidate(work, pseg) and len(_tokens(work, *prefix)) >= 2:
                        candidates.append((pseg, True))
                        seg = _Segment(first_place, seg.end, None, seg.hits)
            address_segs.append(seg)
            continue
        toks = [t for _, _, t in _tokens(work, seg.start, seg.end)]
        follows_address = bool(address_segs) and _adjacent(work, address_segs[-1], seg)
        if any(t in vocab.COMMERCE for t in toks):
            notes.append(seg)
        elif _is_name_candidate(work, seg):
            candidates.append((seg, False))
        elif toks and (toks[0].startswith("ال") or re.match(r"(al|el)[\-\s]", toks[0])):
            address_segs.append(seg)  # likely an area name we do not know
        elif follows_address and re.search(r"\d", work.text(seg.start, seg.end)):
            address_segs.append(seg)  # "مدينة الصدر - قطاع 45"
        else:
            notes.append(seg)

    # 4c. "انا من البصرة بس التوصيل لبغداد": the delivery destination wins.
    delivery_govs = {h.governorate for s in address_segs if s.tag == vocab.DELIVERY for h in s.hits}
    if delivery_govs:
        kept = []
        for s in address_segs:
            other = {h.governorate for h in s.hits}
            if s.tag != vocab.DELIVERY and other and not other & delivery_govs:
                notes.append(s)
                _warn(warnings, "other_location_ignored", "address",
                      f"Ignored {work.text(s.start, s.end)!r}: the customer asked for delivery elsewhere.", INFO)
            else:
                kept.append(s)
        address_segs = kept

    # 5. Choose the name.
    if name_span is None and candidates:
        def score(item):
            seg, from_address = item
            n = len(_tokens(work, seg.start, seg.end))
            base = 3 if 2 <= n <= 4 else (2 if n == 5 else 1)
            return base + (1 if _next_to_phone(work, seg, phones) else 0) + (0.5 if from_address else 0)

        best = max(candidates, key=lambda c: (score(c), -c[0].start))
        name_span = (best[0].start, best[0].end)
        others = [c for c in candidates if c is not best]
        if others:
            _warn(warnings, "name_ambiguous", "name",
                  "Several lines could be the customer's name; picked the most likely one: "
                  + ", ".join(repr(work.text(c[0].start, c[0].end)) for c in [best] + others), REVIEW)
            notes.extend(c[0] for c in others)
    elif candidates:
        notes.extend(c[0] for c in candidates)

    name = _format_name(work.text(*name_span)) if name_span else None
    if name and surname_span:
        name = f"{name} {_format_name(work.text(*surname_span))}"
    if name_span and name_span[0] in greeting_before:
        _warn(warnings, "name_after_greeting", "name",
              f"The word before {name!r} was read as a greeting (e.g. هلا/Salam) but could be part of the name.", REVIEW)
    if name and len(name.split()) == 1:
        _warn(warnings, "name_single_word", "name", f"Only one name given ({name!r}); couriers usually need at least two.", REVIEW)

    # 6. Phones.
    primary = [p for i, p in enumerate(phones) if i not in alt_phone_ids]
    ordered = primary + [p for i, p in enumerate(phones) if i in alt_phone_ids]
    seen: list[str] = []
    for p in ordered:
        if p.e164 not in seen:
            seen.append(p.e164)
    phone = seen[0] if seen else None
    alt_phones = seen[1:]
    if phone:
        main = next(p for p in ordered if p.e164 == phone)
        if not main.known_operator:
            _warn(warnings, "phone_unknown_operator", "phone",
                  f"{phone} does not start with a known Iraqi mobile prefix (075/077/078/079).", REVIEW)
    if alt_phones:
        _warn(warnings, "multiple_phones", "phone", f"Extra number(s) kept in alt_phones: {', '.join(alt_phones)}", INFO)
    for b in bad_numbers:
        _warn(warnings, "phone_invalid", "phone",
              f"Could not read {b.raw.strip()!r} as an Iraqi mobile number (expected 07XX XXX XXXX).",
              INFO if phone else REVIEW)

    # 7. Governorate.
    governorate, used_hits = _choose_governorate(work, address_segs, warnings)

    # 8. Address.
    address, vague = _compose_address(work, address_segs, used_hits)
    if address and vague:
        _warn(warnings, "address_vague", "address",
              "Address only names a city/area; ask for the street, area and nearest landmark (أقرب نقطة دالة).", REVIEW)

    notes_text = "\n".join(re.sub(r"\s+", " ", work.text(s.start, s.end)).strip()
                           for s in sorted(notes, key=lambda s: s.start)) or None

    result = {
        "name": name,
        "phone": phone,
        "alt_phones": alt_phones,
        "governorate": governorate,
        "governorate_ar": GOVERNORATES[governorate] if governorate else None,
        "address": address,
        "notes": notes_text,
    }
    missing = [k for k in ("name", "phone", "governorate", "address") if not result[k]]
    result["missing"] = missing
    result["warnings"] = warnings
    result["needs_review"] = bool(missing) or any(w["severity"] == REVIEW for w in warnings)
    return result


def _alt_phone_ids(work: _Work, labels: list[_Label], phones: list[PhoneMatch]) -> set[int]:
    """Indexes of phones that directly follow a "second number" label."""
    ids = set()
    key = work.key_str
    for i, p in enumerate(phones):
        before = [lab for lab in labels if lab.end <= p.start]
        if not before:
            continue
        lab = before[-1]
        gap = key[lab.value_start:p.start]
        if lab.field == vocab.PHONE_ALT and re.fullmatch(r"[\s:：=\-]*", gap):
            ids.add(i)
    return ids


def _adjacent(work: _Work, a: _Segment, b: _Segment) -> bool:
    """True when only separators lie between segment ``a`` and the later segment ``b``."""
    return a.end <= b.start and re.fullmatch(r"[\s،,;؛|\-–—/.:]*", work.orig[a.end:b.start]) is not None


def _next_to_phone(work: _Work, seg: _Segment, phones: list[PhoneMatch]) -> bool:
    for p in phones:
        if p.start >= seg.end and re.fullmatch(r"[\s،,;:\-|]*", work.orig[seg.end:p.start]):
            return True
        if p.end <= seg.start and re.fullmatch(r"[\s،,;:\-|]*", work.orig[p.end:seg.start]):
            return True
    return False


def _choose_governorate(work: _Work, address_segs: list[_Segment], warnings: list):
    # Priority: "deliver to ..." > "المحافظة: ..." > everything else.
    gov_segs = [s for s in address_segs if s.tag == vocab.DELIVERY] + [
        s for s in address_segs if s.tag == vocab.GOVERNORATE]
    ordered = gov_segs + [s for s in address_segs if s not in gov_segs]
    evidence = [h for s in ordered for h in s.hits if not _is_embedded(work, h)]
    explicit = [h for h in evidence if h.kind == GOVERNORATE_KIND]
    cities = [h for h in evidence if h.kind == CITY_KIND]

    labelled = [h for s in gov_segs for h in s.hits if h.kind == GOVERNORATE_KIND and not _is_embedded(work, h)]
    labelled_city = [h for s in gov_segs for h in s.hits if h.kind == CITY_KIND]

    governorate = None
    if labelled:
        governorate = labelled[0].governorate
    elif explicit:
        governorate = explicit[0].governorate
    elif labelled_city or cities:
        governorate = (labelled_city or cities)[0].governorate
        _warn(warnings, "governorate_inferred", "governorate",
              f"Governorate inferred as {governorate} from the city/area "
              f"{work.text((labelled_city or cities)[0].start, (labelled_city or cities)[0].end)!r}.", INFO)
    else:
        guess = _fuzzy_governorate(work, gov_segs or address_segs[:3])
        if guess:
            governorate = guess
            _warn(warnings, "governorate_fuzzy", "governorate",
                  f"Governorate spelling not recognised exactly; best guess is {guess}.", REVIEW)
        else:
            labelled_segs = [s for s in gov_segs if s.tag == vocab.GOVERNORATE]
            if labelled_segs:
                _warn(warnings, "governorate_unrecognized", "governorate",
                      f"Could not recognise the governorate {work.text(labelled_segs[0].start, labelled_segs[0].end)!r}.",
                      REVIEW)

    if governorate:
        other_explicit = sorted({h.governorate for h in explicit} - {governorate})
        if other_explicit:
            _warn(warnings, "governorate_conflict", "governorate",
                  f"Message mentions more than one governorate ({governorate}, {', '.join(other_explicit)}); using {governorate}.",
                  REVIEW)
        other_city = sorted({h.governorate for h in cities} - {governorate})
        if other_city:
            places = ", ".join(repr(work.text(h.start, h.end)) for h in cities if h.governorate != governorate)
            _warn(warnings, "governorate_city_mismatch", "governorate",
                  f"{places} is in {', '.join(other_city)}, not {governorate}.", REVIEW)

    used = [h for h in explicit if h.governorate == governorate]
    return governorate, used


def _compose_address(work: _Work, segs: list[_Segment], used_hits: list[GazetteerHit]) -> tuple[str | None, bool]:
    pieces: list[str] = []
    residual_words = 0
    used = {(h.start, h.end) for h in used_hits}
    for seg in sorted(segs, key=lambda s: s.start):
        chars = list(work.text(seg.start, seg.end))
        keychars = list(work.keytext(seg.start, seg.end))

        def blank(s, e):
            for i in range(max(s, 0), min(e, len(chars))):
                chars[i] = " "
                keychars[i] = " "

        for h in seg.hits:
            if (h.start, h.end) in used:
                blank(h.start - seg.start, h.end - seg.start)
        key = "".join(keychars)
        for rx in (vocab.GOV_WORD_RE, vocab.COUNTRY_RE):
            for m in rx.finditer(key):
                blank(m.start(), m.end())
        text = re.sub(r"\s+", " ", "".join(chars)).strip(_EDGE_PUNCT + "،,")
        key = make_key(text)
        toks = text.split()
        ktoks = key.split()
        # Trim connectors/filler at the edges and cut trailing order chatter.
        while ktoks and (ktoks[0] in vocab.EDGE_WORDS or ktoks[0] in vocab.FILLER or ktoks[0] in vocab.COMMERCE):
            toks.pop(0), ktoks.pop(0)
        for i, t in enumerate(ktoks):
            if t in vocab.ORDER_INTENT:
                toks, ktoks = toks[:i], ktoks[:i]
                break
        while ktoks and (ktoks[-1] in vocab.EDGE_WORDS or ktoks[-1] in vocab.FILLER):
            toks.pop(), ktoks.pop()
        if not toks:
            continue
        piece = " ".join(toks).strip(_EDGE_PUNCT + "،,")
        if not piece:
            continue
        if seg.tag == vocab.LANDMARK and not _LANDMARK_LEADS.match(make_key(piece)):
            piece = ("قرب " if has_arabic(piece) else "near ") + piece
        pieces.append(piece)

        # Words left once every known place name is removed: is there any
        # street / landmark detail beyond "Baghdad, Karrada"?
        rest = list(work.keytext(seg.start, seg.end))
        for h in seg.hits:
            for i in range(h.start - seg.start, h.end - seg.start):
                rest[i] = " "
        rest_key = "".join(rest)
        for rx in (vocab.GOV_WORD_RE, vocab.COUNTRY_RE):
            rest_key = rx.sub(" ", rest_key)
        residual_words += sum(
            1 for t in rest_key.split()
            if re.search(r"[^\W_]", t) and t.strip(_EDGE_PUNCT) not in vocab.EDGE_WORDS | vocab.FILLER | vocab.COMMERCE
        )

    if not pieces:
        return None, False
    joiner = "، " if any(has_arabic(p) for p in pieces) else ", "
    return joiner.join(pieces), residual_words == 0
