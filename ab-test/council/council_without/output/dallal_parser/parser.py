"""``parse_order``: turn a free-form Instagram DM into a delivery record.

Pipeline
--------
1. ``clean_text``: ASCII digits, no emoji / invisible characters.
2. Phones are pulled out of the raw text first (they are the most reliable
   field) and their spans are replaced by segment breaks.
3. The rest is split into *segments* (lines, commas, ``/``, `` - ``...), and
   again at strong field labels ("الاسم", "العنوان", "Name:"...).
4. Each segment gets an optional label, greetings/fillers are removed, and it
   is classified as name / address / notes / unknown. Unlabelled segments
   that contain a place name are addresses; if the place name is preceded by
   name-looking words ("احمد علي بغداد الكرادة") the segment is split.
5. The governorate is resolved from all address segments with a priority
   order (labelled field > governorate name > city > neighbourhood), conflicts
   are reported as warnings.
6. The governorate word itself is removed from the address; the rest of the
   address segments are joined with " - ".

Nothing here guesses silently: anything uncertain lands in ``warnings`` and
flips ``needs_review`` so the bot can confirm with the customer before the
order is sent to the courier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import lexicon as lx
from .gazetteer import KIND_PRIORITY, Location, arabic_name, find_locations, fuzzy_find, strip_proclitic
from .matcher import token_in
from .normalize import clean_text, has_digit, is_latin, norm_token, strip_article, tokenize
from .phone import extract_phones, is_common_prefix

REQUIRED_FIELDS = ("name", "phone", "governorate", "address")

# Segment separators. Dashes split only when spaced or between non-Latin
# characters, so "al-Karrada" and house numbers like "12-5" stay intact.
_SEP = re.compile(
    r"[\n،,;؛|/\\•·]+"
    r"|\s[-–—_]+|[-–—_]+\s"
    r"|(?<=[^\x00-\x7f])[-–—_]+(?=[^\x00-\x7f])"
    r"|(?<=[^\x00-\x7f])[-–—_]+(?=[A-Za-z])|(?<=[A-Za-z])[-–—_]+(?=[^\x00-\x7f])"
    r"|\.(?=\s|$)|\.\.+"
)

_PUNCT_ONLY = re.compile(r"^[^\w]+$")

# Map / Instagram links. They go to notes untouched (a Google Maps pin is
# gold for the courier) and must not be split into "address" pieces.
_URL = re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|org|gl|ly|me|app|iq)(?:/\S*)?",
                  re.IGNORECASE)
_EDGE = re.compile(r"^[\s\W_]+|[\s\W_]+$")


@dataclass
class Segment:
    tokens: list[str]
    label: str | None = None  # name / phone / governorate / address / landmark / notes
    index: int = 0  # position in the message
    had_intro: bool = False  # "اني ..." / "I am ..." was stripped
    locations: list[Location] = field(default_factory=list)
    kind: str = ""  # final classification


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def _blank_spans(text: str, spans: list[tuple[int, int]]) -> str:
    out, last = [], 0
    for start, end in sorted(spans):
        out.append(text[last:start])
        out.append("\n")
        last = end
    out.append(text[last:])
    return "".join(out)


def _split_on_labels(tokens: list[str]) -> list[list[str]]:
    """Split a token list before every strong label (or any label + ':')."""
    norms = [norm_token(t) for t in tokens]
    cuts = [0]
    m0 = lx.LABEL_MATCHER.match_at(tokens, 0, norms)
    i = m0.end if m0 else 1
    while i < len(tokens):
        m = lx.LABEL_MATCHER.match_at(tokens, i, norms)
        if m:
            _, strong = m.payload
            followed_by_colon = m.end < len(tokens) and tokens[m.end] == ":"
            preceded_by_colon = tokens[i - 1] == ":"
            if (strong or followed_by_colon) and not preceded_by_colon and not _place_phrase_at(tokens, i, m.end):
                cuts.append(i)
                i = m.end
                continue
        i += 1
    cuts.append(len(tokens))
    return [tokens[a:b] for a, b in zip(cuts, cuts[1:]) if tokens[a:b]]


def _place_phrase_at(tokens: list[str], i: int, label_end: int) -> bool:
    """A place name starting at ``i`` that is longer than the label there
    ("مدينة الصدر" is a place, not the label "مدينة" + "الصدر")."""
    return any(loc.start == 0 and loc.end > label_end - i for loc in find_locations(tokens[i:]))


def _detect_label(tokens: list[str]) -> tuple[str | None, list[str]]:
    m = lx.LABEL_MATCHER.match_at(tokens, 0)
    if not m or _place_phrase_at(tokens, 0, m.end):
        return None, tokens
    label, strong = m.payload
    rest = tokens[m.end:]
    colon = bool(rest) and rest[0] in (":", "-", "=")
    while rest and rest[0] in (":", "-", "="):
        rest = rest[1:]
    # Weak English "number"/"order"/"size"... without a colon are ordinary
    # words; let the segment be classified on its content instead.
    if not strong and not colon and label in ("phone", "notes") and is_latin(tokens[0]):
        return None, tokens
    if label == "phone" and rest and not colon and token_in(rest[0], lx.ADDRESS_WORDS):
        return None, tokens  # "رقم الدار 12" is an address, not a phone label
    return label, rest


def _strip_phrases(tokens: list[str], matcher, *, anywhere: bool) -> tuple[list[str], bool]:
    """Remove phrases from the start (or everywhere). Returns (tokens, removed?)."""
    removed = False
    if anywhere:
        matches = matcher.find_all(tokens)
        if matches:
            drop = {k for m in matches for k in range(m.start, m.end)}
            tokens = [t for k, t in enumerate(tokens) if k not in drop]
            removed = True
        return tokens, removed
    while tokens:
        m = matcher.match_at(tokens, 0)
        if not m:
            break
        tokens = tokens[m.end:]
        removed = True
        while tokens and tokens[0] in (":", "-"):
            tokens = tokens[1:]
    return tokens, removed


def _strip_trailing_phone_words(tokens: list[str]) -> list[str]:
    while tokens and (tokens[-1] in (":", "-") or _PUNCT_ONLY.match(tokens[-1])
                      or token_in(tokens[-1], lx.PHONE_WORDS)):
        tokens = tokens[:-1]
    return tokens


def _clean_tokens(tokens: list[str]) -> list[str]:
    out = []
    for t in tokens:
        if t == ":" or _PUNCT_ONLY.match(t):
            continue
        out.append(t)
    return out


def _segments(text: str) -> list[Segment]:
    segs: list[Segment] = []
    for chunk in _SEP.split(text):
        tokens = tokenize(chunk)
        if not tokens:
            continue
        for part in _split_on_labels(tokens):
            segs.append(Segment(part))
    out = []
    for seg in segs:
        tokens, _ = _strip_phrases(seg.tokens, lx.GREETING_MATCHER, anywhere=True)
        label, tokens = _detect_label(tokens)
        tokens, intro = _strip_phrases(tokens, lx.INTRO_MATCHER, anywhere=False)
        if intro and label is None:
            # "اني ..." / "I am ..." may be followed by a label ("I am, name: ...")
            label, tokens = _detect_label(tokens)
        tokens = _strip_trailing_phone_words(tokens)
        tokens = _clean_tokens(tokens)
        if not tokens or (label is None and all(token_in(t, lx.NON_NAME_WORDS) for t in tokens)):
            continue  # nothing left, or only filler like "هذا" / "this is"
        out.append(Segment(tokens, label, len(out), intro))
    # Weak greetings ("سلام", "هلا") are dropped only at the very start or end.
    for pos in (0, -1):
        if out and out[pos].label is None and all(token_in(t, lx.WEAK_GREETINGS) for t in out[pos].tokens):
            out.pop(pos)
    for k, seg in enumerate(out):
        seg.index = k
        seg.locations = find_locations(seg.tokens)
    return out


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _has_any(tokens: list[str], keys: frozenset[str]) -> bool:
    return any(token_in(t, keys) for t in tokens)


def _name_score(tokens: list[str], *, had_intro: bool = False, first: bool = False) -> float:
    """How much does this token list look like a person's name? (<1 = no)."""
    if not tokens or len(tokens) > 5:
        return -10
    if any(has_digit(t) for t in tokens):
        return -10
    if any(_has_any(tokens, words) for words in (lx.ADDRESS_WORDS, lx.NOTE_WORDS, lx.NON_NAME_WORDS)):
        return -10
    if any(not re.search(r"\w", t) for t in tokens):
        return -10
    while tokens and token_in(tokens[0], lx.HONORIFICS):
        tokens = tokens[1:]
    if not tokens:
        return -10
    score = 0.0
    first_norm = norm_token(tokens[0])
    if strip_article(first_norm)[0] in lx.FIRST_NAMES:
        score += 2
    if 2 <= len(tokens) <= 4:
        score += 1
    if strip_article(first_norm)[1]:
        score -= 2  # "الكرادة", "al-Mansour": places start with the article, names rarely do
    if len(tokens) == 5:
        score -= 1
    if had_intro:
        score += 1
    if first:
        score += 0.5
    return score


def _trim_name_prefix(tokens: list[str]) -> list[str]:
    """Drop trailing fillers from a name prefix: "احمد علي من" / "... محافظة"."""
    while tokens and (token_in(tokens[-1], lx.GOV_WORDS)
                      or lx.ADDRESS_FILLER_MATCHER.match_at(tokens, len(tokens) - 1)
                      or lx.INTRO_MATCHER.match_at(tokens, len(tokens) - 1)):
        tokens = tokens[:-1]
    return tokens


def _format_name(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = _EDGE.sub("", text)
    if is_latin(text):
        text = " ".join(w[:1].upper() + w[1:].lower() if not w.isupper() or len(w) > 3 else w
                        for w in text.split())
    return text


def _join(tokens: list[str]) -> str:
    return _EDGE.sub("", " ".join(tokens))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_order(text: str) -> dict:
    """Parse a customer's order-details message.

    Returns a dict with:

    ``name``, ``phone``, ``governorate``, ``address``
        The four required fields (``None`` when not found). ``phone`` is
        E.164 (``+9647XXXXXXXXX``); ``governorate`` is the English name of one
        of Iraq's 19 governorates (see ``GOVERNORATES``).
    ``governorate_ar``
        Arabic name of the governorate, for courier labels.
    ``landmark``
        The "nearest landmark" part of the address, if identifiable
        (it is *also* contained in ``address``).
    ``alt_phones``
        Further valid mobile numbers, in order of appearance.
    ``notes``
        Order / delivery remarks that are not part of the address.
    ``missing``
        Required fields that are ``None``, in the order the bot should ask.
    ``warnings``
        Human-readable problems (invalid numbers, conflicting places...).
    ``confidence``
        ``"high" | "medium" | "low"`` per found required field.
    ``is_complete``
        All four required fields present.
    ``needs_review``
        True if anything is missing, any warning was raised or any field has
        low confidence. Treat ``needs_review=False`` as "safe to confirm
        back to the customer and ship".
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_order expects str, got {type(text).__name__}")

    warnings: list[str] = []
    cleaned = clean_text(text)
    urls = list(_URL.finditer(cleaned))
    url_spans = [(u.start(), u.end()) for u in urls]
    for start, end in url_spans:  # keep offsets, hide link digits from the phone finder
        cleaned = cleaned[:start] + " " * (end - start) + cleaned[end:]

    # --- phones ------------------------------------------------------------
    hits = extract_phones(cleaned)
    phones: list[str] = []
    for h in hits:
        if h.problem is None:
            if h.number not in phones:
                phones.append(h.number)
        elif h.problem == "wrong_length":
            warnings.append(f"Phone number '{h.raw}' has the wrong number of digits "
                            f"(Iraqi mobiles are 07XX XXX XXXX).")
        elif h.problem == "non_iraqi":
            warnings.append(f"Phone number '{h.raw}' is not an Iraqi number.")
        else:
            warnings.append(f"Phone number '{h.raw}' is not an Iraqi mobile number.")
    for p in phones:
        if not is_common_prefix(p):
            warnings.append(f"Phone number {p} uses an uncommon prefix 0{p[4:6]}; please verify.")

    segments = _segments(_blank_spans(cleaned, [(h.start, h.end) for h in hits] + url_spans))

    # --- classify segments ---------------------------------------------------
    # A name candidate: (score, segment index, name tokens, address parts to use
    # if this candidate wins, address parts to use if it loses).
    candidates: list[tuple[float, int, list[str], list, list]] = []
    address_parts: list[tuple[int, list[str], list[Location], str | None]] = []
    notes: list[str] = [u.group() for u in urls]
    labelled_names: list[list[str]] = []

    for seg in segments:
        toks, locs, idx = seg.tokens, seg.locations, seg.index
        whole = [(idx, toks, locs, "unknown")]
        if seg.label == "name":
            # "my name is ali and im in basra" / "اسمي علي وهذا رقم اخوي"
            name_toks, tail = _take_name(toks)
            split = _split_name_and_place(name_toks, find_locations(name_toks), labelled=True)
            if split:
                name_toks, place, place_locs = split
                address_parts.append((idx, place, place_locs, None))
            if name_toks:
                labelled_names.append(name_toks)
            if tail:
                tail_locs = find_locations(tail)
                if tail_locs:
                    address_parts.append((idx, tail, tail_locs, None))
                else:
                    notes.append(_join(tail))
        elif seg.label in ("governorate", "address", "landmark"):
            # Never pull a name out of a labelled address.
            address_parts.append((idx, toks, locs, seg.label))
        elif seg.label in ("notes", "phone"):
            notes.append(_join(toks))
        elif locs:
            split = _split_name_and_place(toks, locs, labelled=False, had_intro=seg.had_intro,
                                          first=idx == 0)
            if split:
                name_toks, rest, rest_locs = split
                score = _name_score(name_toks, had_intro=seg.had_intro, first=idx == 0)
                candidates.append((score + 0.25, idx, name_toks, [(idx, rest, rest_locs, None)],
                                   [(idx, toks, locs, None)]))
            elif (suffix := _name_suffix(toks, locs)):
                # "بغداد البلديات احمد فاضل": name written after the place
                score = _name_score(toks[-suffix:])
                candidates.append((score, idx, toks[-suffix:], [(idx, toks[:-suffix], locs, None)],
                                   [(idx, toks, locs, None)]))
            else:
                address_parts.append((idx, toks, locs, None))
        elif _has_any(toks, lx.ADDRESS_WORDS):
            # Address words mixed with order chatter ("اريد الي بالستوري قرب...")
            # are kept but flagged.
            address_parts.append((idx, toks, locs, "unknown" if _has_any(toks, lx.NOTE_WORDS) else None))
        elif _has_any(toks, lx.NOTE_WORDS) or _has_any(toks, lx.NON_NAME_WORDS):
            # order chatter, or a sentence ("هسه انطيك المعلومات") rather than a place
            notes.append(_join(toks))
        else:
            score = _name_score(toks, had_intro=seg.had_intro, first=idx == 0)
            # If another segment wins the name, a losing segment that starts with
            # a known first name is a second person (notes); anything else
            # unrecognised is most likely part of the address.
            is_person = score >= 1 and token_in(toks[0], lx.FIRST_NAMES)
            candidates.append((score, idx, toks, [], [("note", toks)] if is_person else whole))

    # --- name ------------------------------------------------------------------
    name: str | None = None
    name_conf: str | None = None
    winner = None
    if labelled_names:
        name_tokens = labelled_names[0]
        name = _format_name(name_tokens) or None
        name_conf = "high"
        if len(name_tokens) > 5:
            warnings.append("The name field is unusually long; please check it.")
            name_conf = "low"
        distinct = []
        for toks in labelled_names:
            if _join(toks) not in distinct:
                distinct.append(_join(toks))
        if len(distinct) > 1:
            warnings.append("More than one name was given; using the first.")
            notes.extend(distinct[1:])
    else:
        viable = [c for c in candidates if c[0] >= 1]
        if viable:
            winner = max(viable, key=lambda c: (c[0], -c[1]))
            name = _format_name(winner[2]) or None
            name_conf = "medium" if winner[0] >= 2 else "low"
    for cand in candidates:
        parts = cand[3] if cand is winner else cand[4]
        for part in parts:
            if part[0] == "note":
                if not (name and _join(part[1]) == name):
                    notes.append(_join(part[1]))
            else:
                address_parts.append(part)
    address_parts.sort(key=lambda p: p[0])

    # --- governorate -----------------------------------------------------------
    governorate, gov_conf, gov_warnings = _resolve_governorate(address_parts)
    warnings.extend(gov_warnings)
    fuzzy = [(k, loc) for k, part in enumerate(address_parts) for loc in fuzzy_find(part[1])
             if not any(l.start <= loc.start < l.end for l in part[2])]
    if governorate is None:
        govs = {loc.governorate for _, loc in fuzzy}
        if len(govs) == 1:
            governorate = govs.pop()
            gov_conf = "low"
            k, loc = fuzzy[0]
            word = " ".join(address_parts[k][1][loc.start:loc.end])
            warnings.append(f"Governorate guessed as {governorate} from the misspelled word '{word}'.")
    # A misspelt governorate word that agrees with the resolved governorate
    # ("بغدااد حي العامل") is removed from the address like the real word.
    # Misspelt *city* names stay in the address.
    for k, loc in fuzzy:
        if loc.governorate == governorate and loc.kind == "fuzzy-gov":
            idx, toks, locs, label = address_parts[k]
            address_parts[k] = (idx, toks, locs + [Location(loc.start, loc.end, loc.governorate, "gov")], label)
    for idx, toks, locs, label in address_parts:
        if label == "governorate" and not locs and governorate is None:
            warnings.append(f"Unrecognised governorate '{_join(toks)}'.")

    # --- address & landmark ----------------------------------------------------
    pieces: list[str] = []
    landmark: str | None = None
    has_strong_address = False
    has_detail = False  # anything beyond bare place names
    unrecognised: list[str] = []
    for idx, toks, locs, label in address_parts:
        drop = _governorate_token_indices(toks, locs, governorate)
        in_place = {k for l in locs for k in range(l.start, l.end)}
        display = list(toks)
        for l in locs:
            display[l.start] = strip_proclitic(display[l.start])
        kept = [(display[k], k in in_place) for k in range(len(toks)) if k not in drop]
        kept = [(t, p) for t, p in _strip_leading_junk(kept) if not (t == ":" or _PUNCT_ONLY.match(t))]
        if not kept:
            continue
        remaining = [t for t, _ in kept]
        piece = _join(remaining)
        if not piece or piece in pieces:
            continue
        pieces.append(piece)
        if not all(p for _, p in kept):
            has_detail = True
        if label == "unknown":
            unrecognised.append(piece)
        if label in ("address", "landmark") or _has_any(remaining, lx.ADDRESS_WORDS) \
                or any(l.kind in ("city", "district") for l in locs):
            has_strong_address = True
        if label == "landmark" and landmark is None:
            landmark = piece
    if landmark is None:
        landmark = _find_landmark(pieces)
    address = " - ".join(pieces) or None

    address_conf = None
    if address:
        if unrecognised:
            # Unrecognised text is kept (losing a real address piece is worse),
            # but the order must be checked.
            warnings.append("The address may contain text that is not part of it: "
                            + ", ".join(f"'{u}'" for u in unrecognised) + ".")
            address_conf = "low"
        elif not has_detail:
            address_conf = "low"  # only a city / neighbourhood name: ask for street + landmark
        elif has_strong_address and (len(address.split()) >= 3 or landmark):
            address_conf = "high"
        elif has_strong_address or len(address.split()) >= 2:
            address_conf = "medium"
        else:
            address_conf = "low"  # one unknown word, e.g. "الشعب"

    # --- result ----------------------------------------------------------------
    phone = phones[0] if phones else None
    phone_conf = None
    if phone:
        phone_conf = "high" if is_common_prefix(phone) else "medium"
    if not phone and any(h.problem for h in hits):
        phone_conf = None

    result = {
        "name": name,
        "phone": phone,
        "governorate": governorate,
        "address": address,
        "governorate_ar": arabic_name(governorate) if governorate else None,
        "landmark": landmark,
        "alt_phones": phones[1:],
        "notes": " | ".join(n for n in notes if n) or None,
    }
    confidence = {k: v for k, v in (("name", name_conf), ("phone", phone_conf),
                                    ("governorate", gov_conf), ("address", address_conf)) if v}
    missing = [f for f in REQUIRED_FIELDS if result[f] is None]
    result["missing"] = missing
    result["warnings"] = warnings
    result["confidence"] = confidence
    result["is_complete"] = not missing
    result["needs_review"] = bool(missing or warnings or "low" in confidence.values())
    return result


def _split_name_and_place(tokens, locs, *, labelled, had_intro=False, first=False):
    """Split "احمد علي بغداد الكرادة" into name tokens and address tokens."""
    if not locs:
        return None
    start = locs[0].start
    if start == 0:
        return None
    prefix = _trim_name_prefix(tokens[:start])
    if not prefix:
        return None
    if not labelled and _name_score(prefix, had_intro=had_intro, first=first) < 1:
        return None
    if labelled and (_has_any(prefix, lx.ADDRESS_WORDS) or any(has_digit(t) for t in prefix)):
        return None
    rest = tokens[len(prefix):]
    return prefix, rest, find_locations(rest)


def _name_suffix(tokens, locs) -> int:
    """Length of a trailing name after the last place ("... البلديات احمد فاضل"), or 0.

    Stricter than a leading name: it must start with a known first name and
    contain no address words, because "... حي الحسين" also ends in a name.
    """
    start = max(l.end for l in locs)
    tail = tokens[start:]
    if not 1 <= len(tail) <= 4 or not token_in(tail[0], lx.FIRST_NAMES):
        return 0
    if strip_article(norm_token(tail[0]))[1] or _name_score(tail) < 2:
        return 0
    return len(tail)


def _resolve_governorate(address_parts):
    candidates = []  # (priority, order, gov, kind)
    order = 0
    for idx, toks, locs, label in address_parts:
        for loc in locs:
            priority = 0 if label == "governorate" else KIND_PRIORITY.get(loc.kind, 4)
            before = toks[max(0, loc.start - 3):loc.start]
            if _has_any(before, lx.RESIDENCE_WORDS):
                priority -= 1  # "ساكن ببغداد", "deliver to Kut"
            elif before and token_in(before[-1], lx.ORIGIN_WORDS):
                priority += 0.5  # "اني من النجف", "اشتغل بالبصرة"
            candidates.append((priority, order, loc.governorate, loc.kind))
            order += 1
    if not candidates:
        return None, None, []
    best_priority = min(c[0] for c in candidates)
    best = [c for c in candidates if c[0] == best_priority]
    best.sort(key=lambda c: c[1])
    governorate = best[0][2]
    warnings = []
    all_govs = []
    for c in sorted(candidates, key=lambda c: c[1]):
        if c[2] not in all_govs:
            all_govs.append(c[2])
    if len(all_govs) > 1:
        warnings.append("The message mentions places in more than one governorate ("
                        + ", ".join(all_govs) + f"); using {governorate}.")
    if best_priority <= 1.5:
        conf = "high"
    else:
        conf = "medium"
    if len({c[2] for c in best}) > 1:
        conf = "low"
    elif len(all_govs) > 1:
        conf = "medium" if conf == "high" else "low"
    return governorate, conf, warnings


def _governorate_token_indices(tokens, locs, governorate):
    """Indices of governorate-level words for the chosen governorate (and an
    adjacent "محافظة"/"governorate"), which are dropped from the address."""
    drop = set()
    for loc in locs:
        if loc.kind == "gov" and loc.governorate == governorate:
            drop.update(range(loc.start, loc.end))
            if loc.start > 0 and token_in(tokens[loc.start - 1], lx.GOV_WORDS):
                drop.add(loc.start - 1)
            if loc.end < len(tokens) and token_in(tokens[loc.end], lx.GOV_WORDS):
                drop.add(loc.end)
    return drop


def _strip_leading_junk(kept):
    """Drop leading fillers ("من", "ساكن في", "and im in") from (token, is_place) pairs."""
    while kept:
        tokens = [t for t, _ in kept]
        m = lx.ADDRESS_FILLER_MATCHER.match_at(tokens, 0) or lx.INTRO_MATCHER.match_at(tokens, 0)
        if m:
            kept = kept[m.end:]
        elif not kept[0][1] and (token_in(tokens[0], lx.NON_NAME_WORDS) or tokens[0] in (":", "-")):
            kept = kept[1:]
        else:
            break
    return kept


def _take_name(tokens):
    """Split a labelled name value into (name, tail) at the first non-name word."""
    while tokens and token_in(tokens[0], lx.NON_NAME_WORDS):
        tokens = tokens[1:]
    for k in range(1, len(tokens)):
        if token_in(tokens[k], lx.NON_NAME_WORDS) or lx.INTRO_MATCHER.match_at(tokens, k):
            return tokens[:k], tokens[k:]
    return tokens, []


def _find_landmark(pieces: list[str]) -> str | None:
    for piece in pieces:
        toks = piece.split()
        for k, t in enumerate(toks):
            if token_in(t, lx.LANDMARK_MARKERS):
                if k == len(toks) - 1:
                    break
                return " ".join(toks[k:])
    return None
