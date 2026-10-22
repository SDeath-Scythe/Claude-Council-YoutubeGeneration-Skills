# dallal_parser

Order-details parser for **Dallal**, the Instagram DM sales assistant for Iraqi
cash-on-delivery shops. It turns whatever the customer typed — Iraqi Arabic,
English, Kurdish or a mix — into a clean delivery record.

```python
from dallal_parser import parse_order

parse_order("""السلام عليكم
اني حيدر كاظم
بغداد زيونة شارع الربيعي قرب مطعم ابو رامي
٠٧٩٠ ١٢٣ ٤٥٦٧
اريد القطعة السودة قياس L""")
```

```python
{
  "name": "حيدر كاظم",
  "phone": "+9647901234567",
  "governorate": "Baghdad",
  "address": "زيونة شارع الربيعي قرب مطعم ابو رامي",
  "governorate_ar": "بغداد",
  "landmark": "قرب مطعم ابو رامي",
  "alt_phones": [],
  "notes": "اريد القطعة السودة قياس L",
  "missing": [],
  "warnings": [],
  "confidence": {"name": "medium", "phone": "high", "governorate": "high", "address": "high"},
  "is_complete": True,
  "needs_review": False
}
```

No dependencies (Python ≥ 3.9 standard library only), deterministic, about
1 ms per message.

## Installation and usage

```bash
pip install ./output              # or just put output/ on PYTHONPATH
python -m dallal_parser "علي حسين - البصرة العشار - 07701234567"
echo "..." | dallal-parse         # console script installed by pip
```

Run the tests (standard library `unittest`; pytest also works if installed):

```bash
cd output
python -m unittest discover -s tests -t .
```

## Output fields

| key | type | meaning |
|---|---|---|
| `name` | str / None | Customer name as written (Latin names are title-cased). |
| `phone` | str / None | First valid Iraqi mobile, E.164: `+9647XXXXXXXXX`. |
| `governorate` | str / None | English name, one of the 19 in `GOVERNORATES` (below). |
| `address` | str / None | Everything else needed to find the customer: city, neighbourhood, street, house, landmark. The governorate name itself is removed; pieces from different lines are joined with ` - `. |
| `governorate_ar` | str / None | Arabic governorate name, handy for courier waybills. |
| `landmark` | str / None | The "أقرب نقطة دالة" part ("قرب جامع ..."), if identifiable. Also included in `address`. |
| `alt_phones` | list[str] | Additional valid mobile numbers. |
| `notes` | str / None | Product / delivery chatter and anything not part of the address ("اريد قياس L", "بعد العصر"). Separate items joined with ` \| `. |
| `missing` | list[str] | Required fields that are `None`, in the order `name, phone, governorate, address` — the bot can ask for exactly these. |
| `warnings` | list[str] | Human-readable problems: invalid / foreign numbers, uncommon prefix, places in two governorates, guessed misspelling, unrecognised governorate... |
| `confidence` | dict | `high` / `medium` / `low` for each required field that was found. |
| `is_complete` | bool | All four required fields present. |
| `needs_review` | bool | `True` if anything is missing, any warning exists, or any confidence is `low`. |

### How the bot should use it

1. `is_complete` is `False` → ask the customer for the fields in `missing`.
2. `needs_review` is `True` → read the parsed record back to the customer
   ("تأكيد: الاسم ..، الرقم ..، المحافظة ..، العنوان ..") and ask them to
   confirm or correct, or route it to the shop owner.
3. `needs_review` is `False` → still worth a one-line confirmation message
   before shipping (that is good COD practice anyway), but the record can go
   straight to the courier.

## Design decisions

The brief left these open; each was decided for *fewer failed deliveries*,
which in practice means **never guess silently — flag instead**.

**Rule-based, no ML / LLM, no dependencies.** The parser has to be
predictable, cheap to run on every DM, work offline, and be debuggable by
reading a word list. The trade-off is coverage: unusual phrasing degrades to
`missing` / `needs_review` rather than to a confident wrong answer. If an LLM
is added later, use it as a fallback only when `needs_review` is `True`, and
keep this parser's phone validation as the source of truth.

**Phones.**
- Only Iraqi *mobile* numbers are accepted: `7` + 9 digits after 964, i.e.
  `07XX XXX XXXX`, third digit 3–9. All usual spellings are normalised:
  `07…`, `7…` (missing 0), `+964…`, `00964…`, `964…`, `+964 07…` (redundant
  0), Arabic-Indic `٠٧٧…` and Persian `۰۷۷…` digits, spaces/dashes/dots/
  parentheses anywhere.
- 075 (Korek), 077 (Asiacell), 078/079 (Zain) are accepted silently. Other
  07[3-9] prefixes are accepted but get a warning and `medium` confidence.
- A number with the wrong digit count, a foreign number (`+971…`) or a
  landline is **never "fixed" or dropped silently**: `phone` stays `None`
  (or uses another valid number) and a warning names the bad number. Wrong
  numbers are the most expensive COD failure.
- The first valid number is `phone`; others go to `alt_phones`; duplicates
  (same number written twice in different formats) are merged.
- House numbers are not glued onto phones: "دار 5 07701234567" gives
  `+9647701234567`.

**Governorate.**
- 19 governorates including **Halabja** (made Iraq's 19th governorate by
  law in May 2025, separated from Sulaymaniyah). English names used:
  Baghdad, Basra, Nineveh, Erbil, Sulaymaniyah, Duhok, Halabja, Kirkuk,
  Diyala, Anbar, Babil, Karbala, Najaf, Wasit, Maysan, Dhi Qar, Muthanna,
  Qadisiyyah, Saladin.
- Recognised from Arabic, English and Kurdish spellings, with attached
  prepositions (ببغداد، بالبصرة، للنجف، من كربلاء), diacritics, tatweel,
  and letter variants (أ/ا، ة/ه، ى/ي، Kurdish ە ێ ۆ ک ی).
- Customers often name only the city or neighbourhood, so major cities /
  district centres (الموصل → Nineveh, الحلة → Babil, الناصرية → Dhi Qar,
  الزبير → Basra, …) and well-known Baghdad neighbourhoods (الكرادة, زيونة,
  مدينة الصدر, …) also identify the governorate, with `medium` confidence.
- Priority: labelled field ("المحافظة: …") > governorate name > city >
  neighbourhood. A place after "ساكن / التوصيل / I live / deliver to" is
  preferred, a place after "من / اشتغل / from" (origin, workplace) is
  demoted. Whenever places from **two governorates** appear, a warning is
  raised (`needs_review`): the customer must confirm.
- "شارع بغداد" in Basra, "كراج النجف" in Baghdad, "حي القادسية" in any city,
  "Al-Muthanna neighborhood" in Mosul: a governorate/city name right after
  شارع / حي / سوق / كراج / جامع … (or before street / neighborhood … in
  English) is treated as a street/place name, not as the governorate.
- Single-letter typos of governorate/city names (بغدااد, Baghdat) are
  matched only as a last resort; the result gets `low` confidence and a
  warning. Surname forms like البغدادي are explicitly not matched.
- Place names that are also common personal names or everyday words are
  deliberately left out of the gazetteer (الرفاعي, القاسم, الحمزة, حديثة,
  الحي, بلد, …) or require the article (المنصور ≠ the name منصور, المثنى ≠
  the name مثنى, العمارة). Missing a governorate is recoverable (the bot
  asks); routing an order to the wrong city is not.

**Address.**
- Kept in the customer's own words (only digits are converted to ASCII and
  emoji removed) — couriers read Arabic, and "corrected" text can lose
  meaning.
- The governorate word (and an adjacent "محافظة") is removed because it is
  in its own field. **City and neighbourhood names are kept**, because a
  governorate has many cities (الموصل is not the only city in Nineveh).
- Only a governorate (e.g. just "البصرة") is *not* an address: `address`
  is `None` and listed in `missing` so the bot asks for the area and the
  nearest landmark.
- Unrecognised text that is clearly not the name and not order chatter is
  appended to the address rather than discarded (losing "كمب سارة" would be
  worse), **but it always raises a warning** naming the text, so the order
  is reviewed. Lines that read like sentences (contain words like هذا،
  لان، اذا، and, but) or order chatter go to `notes` instead.
- Address confidence is `low` (→ review) when the address is only a place
  name ("الكرادة", "الديوانية") or one unknown word: the courier still
  needs a street or landmark. `high` needs an address word (حي، شارع،
  قرب، street, near…) or a known neighbourhood plus a landmark or
  some detail.
- Attached prepositions are removed from kept place names ("ساكنين
  بالديوانية" → "الديوانية").
- Links (Google Maps pins, Instagram links) are copied to `notes` as-is and
  never parsed as address or phone digits.

**Name.**
- Taken from a label ("الاسم", "اسمي", "المستلم", "Name:", "ناوم") when
  present (`high` confidence). The value stops at the first word that never
  occurs in names ("اسمي علي وهذا رقم اخوي" → "علي"; "my name is ali and im
  in basra" → "Ali", Basra). If both a recipient (المستلم) and an orderer
  are named, the first one is used, the other goes to `notes`, and a
  warning is raised.
- Otherwise the best-scoring unlabelled line: 1–5 words, no digits, no
  address words, not starting with the article (places do, names rarely),
  bonus for a known first name (650+ Arabic, Kurdish and Latin-script first
  names, plus kunya forms ابو / ام). A single word needs a known first name.
  `medium` with a known first name, `low` (→ `needs_review`) without.
- "احمد علي بغداد الكرادة" on one line is split into name + address; so is
  "بغداد الكرادة احمد فاضل" when the trailing words start with a known
  first name (stricter, because "كربلاء حي الحسين" also ends in a name).
- Greetings (السلام عليكم، مرحبا، hi…) are removed. سلام / هلا are also
  given names, so they are only dropped when they stand alone at the start
  or end of the message.
- Honorifics and kunyas are kept as written (الست هدى, حجي ابو مصطفى, ام
  حسين: this is how the courier will ask for the customer at the door); they
  are ignored only when judging whether a line looks like a name.

**Notes.** Product and delivery chatter (اريد, قياس, اللون, بعد العصر,
size, color…) goes to `notes` so it neither pollutes the address nor is lost.

## Known limitations

- Free-form sentences in which name and address are interleaved in unusual
  orders ("بغداد الكرادة اسمي علي" works; long prose may not). These come
  out with fields missing or `needs_review`, not silently wrong in the cases
  we tested — but not every case can be tested.
- The neighbourhood list is strongest for Baghdad. Unknown neighbourhoods in
  other cities still go into `address`; the governorate is then only found
  if the customer names it or its city.
- Arabizi (Latin-script Arabic, "ana mn baghdad") is only partly handled:
  common words (ana, mn, ismi, ra8mi, salam 3likum) and English spellings of
  places are known, but names written with digits for letters (7amza, 3abbas)
  are not. Such messages come out with `needs_review=True`.
- A place name used as part of a longer place name we don't know ("حي
  الجامعة بغداد", meaning near Baghdad University) is not used for the
  governorate; the bot asks instead.
- Two customers' details in one message cannot be separated; the first name
  is used and the rest goes to `notes` with a warning.
- Disputed-territory districts (e.g. Akre, Makhmour, Sinjar's administrative
  status) follow federal governorate boundaries where included, or are left
  out.

## Layout

```
output/
  dallal_parser/
    __init__.py     public API: parse_order, normalize_phone, extract_phones, GOVERNORATES
    parser.py       pipeline: segmentation, labels, classification, assembly
    phone.py        Iraqi mobile extraction / validation
    gazetteer.py    governorates, cities, neighbourhoods; place matching
    lexicon.py      labels, greetings, fillers, address words, first names
    matcher.py      phrase matcher over normalised tokens
    normalize.py    digit / letter / diacritic normalisation
    __main__.py     CLI
  tests/            unittest suite (phones + end-to-end messages)
```

To extend coverage, add words to `lexicon.py` / `gazetteer.py` and a test
message to `tests/test_parse_order.py`; no code changes are usually needed.
