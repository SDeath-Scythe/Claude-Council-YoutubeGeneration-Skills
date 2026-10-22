# dallal_parser

Turns the order details a customer sends in an Instagram DM into a clean
cash-on-delivery order record. It handles Iraqi Arabic, English, Arabizi and mixed text.

```python
from dallal_parser import parse_order

parse_order("""السلام عليكم
اسمي زهراء كاظم ورقمي ٠٧٥٠ ١٢٣ ٤٥٦٧
وانا من النجف حي الأنصار قرب مدرسة الغدير""")
```

```json
{
  "name": "زهراء كاظم",
  "phone": "+9647501234567",
  "alt_phones": [],
  "governorate": "Najaf",
  "governorate_ar": "النجف",
  "address": "حي الأنصار قرب مدرسة الغدير",
  "notes": null,
  "missing": [],
  "warnings": [],
  "needs_review": false
}
```

There are no dependencies (only the standard library) and it needs Python 3.9 or newer. It runs
offline and gives the same output for the same input.

```bash
pip install ./output                     # or just put output/ on PYTHONPATH
python -m dallal_parser "علي حسين 07701234567 بغداد الكرادة قرب جامع براثا"
python -m unittest discover -s tests     # run from output/
```

## Output fields

| key | type | meaning |
|---|---|---|
| `name` | str \| None | Customer name as written. Diacritics are removed and Latin names are Title-Cased. |
| `phone` | str \| None | Main Iraqi mobile number in E.164 form, `+9647XXXXXXXXX`. |
| `alt_phones` | list[str] | Any other valid mobiles in the message, with duplicates removed. A number written after "رقم ثاني / second number" always goes here. |
| `governorate` | str \| None | One of the 19 English names in `dallal_parser.GOVERNORATES`. |
| `governorate_ar` | str \| None | The standard Arabic name of that governorate, for labels and for messages back to the customer. |
| `address` | str \| None | Everything else about the location: city, area, street, house number and landmark. The governorate name, the word "محافظة" and "العراق/Iraq" are taken out. |
| `notes` | str \| None | Text that is not part of the order record, such as product, size or questions. Kept so nothing the customer wrote gets lost. |
| `missing` | list[str] | Which of `name`, `phone`, `governorate`, `address` could not be found. |
| `warnings` | list[dict] | Each one has `{code, field, severity, message}`. `severity` is `"review"` or `"info"`. |
| `needs_review` | bool | True if anything is in `missing` or any warning has severity `review`. |

**How to use it in Dallal:** if `needs_review` is false, the record is ready to
use. If it is true, have the bot ask a follow-up based on `missing` and `warnings`. For example:
`address_vague` → "شنو أقرب نقطة دالة؟" and `name_single_word` → "ممكن الاسم الثلاثي؟".
I'd suggest always sending the parsed order back to the customer to confirm before shipping
("الاسم: … / الرقم: … / العنوان: … صح؟"). With COD, that one confirmation message is the
cheapest protection against a failed delivery.

If a customer sends their details across several DMs, join their recent messages
with `"\n"` and parse the result once.

### Warning codes

| code | severity | when |
|---|---|---|
| `phone_invalid` | review if there is no valid phone, otherwise info | A long run of digits that is not a valid Iraqi mobile, for example 10 digits instead of 11. It is never "fixed" by guessing. |
| `phone_unknown_operator` | review | The number is valid in shape but its prefix is not 075/077/078/079. |
| `multiple_phones` | info | Extra numbers were put in `alt_phones`. |
| `governorate_inferred` | info | The governorate was worked out from a city or district (الموصل → Nineveh, الكرادة → Baghdad). |
| `governorate_fuzzy` | review | The spelling was close but not exact (بقداد → Baghdad). |
| `governorate_unrecognized` | review | A "المحافظة:" field was given but could not be recognised. |
| `governorate_conflict` | review | Two different governorates are mentioned. |
| `governorate_city_mismatch` | review | The city belongs to a different governorate (بغداد … الزبير). |
| `other_location_ignored` | info | "انا من البصرة بس التوصيل لبغداد…": the delivery destination was used and the other location went to notes. |
| `address_vague` | review | The address is only a city or area name, with no street or landmark. |
| `name_single_word` | review | Only one name was given. |
| `name_ambiguous` | review | Several unlabelled lines look like names. The most likely one was picked and the others are in notes. |
| `name_after_greeting` | review | A greeting that is also a first name (هلا, Salam) was removed from in front of the name. |

## How it works

1. **Normalize.** Arabic-Indic and Persian digits become ASCII. Diacritics, tatweel, bidi marks
   and emoji are removed. A separate matching key folds أ/إ/آ→ا, ة→ه, ى/ی→ي, گ→ك and Kurdish
   letters, and lowercases Latin. The key maps one character to one character, so a match
   position in the key is also the right position in the clean text, which is what gets
   returned.
2. **Phones first.** Groups of digits separated only by spaces, dashes, dots, brackets or `+`
   are joined and checked against the Iraqi mobile format: 10 national digits starting with 7.
   The prefixes `+964`, `00964`, `964`, a leading `0` and `+964 (0)` are accepted. Phones are
   then removed from the text and act as separators.
3. **Labels and markers.** Examples: `الاسم:`, `اسمي`, `رقمي`, `عنواني`, `ساكن`, `انا من`,
   `المحافظة`, `اقرب نقطة دالة`, `التوصيل الى`, `Name:`, `my number is`, `I live in`, and the
   Arabizi `esmi`, `ra8mi`, `sakin`. Generic words such as `city`, `number` and `مدينة` count as
   labels only when followed by a colon or at the start of a line. A label with an empty value
   takes the next line, which handles templates with the answer on the line below.
4. **Segments.** The rest is split on new lines, `، , ; | / – .` and on hyphens between words.
   Each piece is classified as address (it names a known place or has an address word like
   حي/شارع/قرب/زقاق/near/street), order chatter (product, size, price or a question goes to
   notes), a possible name (1–5 letter-only words), or leftover.
5. **Governorate.** The places found are matched against a list of the 19 governorates plus
   about 200 cities and districts (around 600 Arabic and Latin spellings in total). Priority order: the "deliver to" value, then the
   "المحافظة:" value, then an explicit governorate name, then the governorate of a named city.
6. **Address.** The address pieces are joined in the order they appear, and the governorate
   token, "محافظة" and "العراق" are removed.

## Decisions I made (you weren't available, so here is what I chose and why)

- **Wrong data is worse than missing data.** When unsure, the parser leaves a field empty or
  sets `needs_review`, rather than guessing quietly. A follow-up question costs a message. A
  wrong governorate costs a failed delivery.
- **Mobile numbers only.** Iraqi COD couriers call mobiles, so landlines and foreign numbers are
  reported as `phone_invalid`. Numbers with the right shape but an unknown operator prefix
  (e.g. 076) are kept but flagged, because new number ranges do get issued.
- **The first number is the main phone.** A number labelled "رقم ثاني/احتياط/second number" is
  always an alternate.
- **19 governorates, including Halabja.** Iraq's parliament approved Halabja as the 19th
  governorate in 2025. Halabja is also kept separate from Sulaymaniyah because couriers in the
  Kurdistan Region already treat it separately. English names follow common courier and UN
  usage: Basra, Nineveh, Sulaymaniyah, Duhok, Babil, Dhi Qar, Qadisiyyah, Saladin.
- **Cities are kept in the address; the governorate name is removed.** For "بغداد الكرادة قرب
  جامع براثا" you get governorate `Baghdad` and address `الكرادة قرب جامع براثا`. For
  "الموصل حي الزهور" the city stays in the address and the governorate becomes `Nineveh`.
- **Place names that double as names or common words need the article.** المنصور is a
  district but منصور is a person. The same goes for الزبير/زبير, الكوت/كوت ("coat" in shop
  DMs), العمارة/عمارة ("building"), الحلة, الشعلة and البياع. A few places are left out
  entirely because they are too ambiguous, e.g. الحي (Wasit), بلد, الدور, "Hit" in English.
  Neighbourhood names that exist in many cities (اليرموك, حي الجامعة) are not used to work out a
  governorate.
- **A governorate name right after a street or landmark word is not the governorate.**
  "البصرة شارع بغداد" is Basra (Baghdad Street). The same applies to "فندق بابل" and
  "Baghdad Mall".
- **The delivery destination wins.** "I'm from Basra but deliver to Baghdad" gives Baghdad.
- **An address with only a city or area is flagged** (`address_vague`). Iraqi couriers expect
  an area plus the nearest landmark (أقرب نقطة دالة).
- **Names are kept as written** (no transliteration). Arabic stays in Arabic, Latin is
  Title-Cased, and kunyas (ام علي، ابو حسين) are valid names. An unlabelled line starting with
  "ال" is not taken as a name, because first names don't start with the article but unknown
  place names do (البنوك، الضباط). Such lines are treated as part of the address.
- **Greetings are removed** (السلام عليكم، هلا، مرحبا، hi). Words that are both greetings and
  names (هلا/Hala, Salam) are removed but flagged.
- **Rule-based, not an LLM.** It is deterministic, fast, free to run, works offline and can be
  tested. The `needs_review` flag marks the cases where a human or an LLM fallback should look.
- **Standard library only, and tests use `unittest`,** so they run anywhere (`pytest` also
  works).

## Known limitations

- If a name comes *after* the address on the same line with no separator ("بغداد الكرادة علي
  حسين"), the parser can't tell which words are the name. It ends up in the address and the
  order is flagged as missing a name.
- The city and district list covers each governorate's main towns and well-known Baghdad and
  Basra neighbourhoods. It is not complete. An unknown place in a message with no governorate
  gives `missing: ["governorate"]`, never a guess. To add places, edit `_CITY_ALIASES` in
  `dallal_parser/gazetteer.py` and add a test.
- Product names the parser doesn't know can look like a name. If there are two name-like
  lines it flags `name_ambiguous`. The product-word list is in `vocab.py` (`COMMERCE`) and is
  worth extending with your shops' catalogue terms.
- Arabizi support covers the common markers and city spellings, not free-form Arabizi
  sentences.

## Layout

```
dallal_parser/
  parser.py      parse_order(): segmentation, classification, governorate and address assembly
  phones.py      Iraqi mobile extraction and normalization
  gazetteer.py   governorates, cities/districts, place matching
  vocab.py       labels, greetings/filler, order words, address keywords
  normalize.py   text cleanup and the 1:1 matching key
tests/           unittest suites (phones, gazetteer, end-to-end messages)
```
