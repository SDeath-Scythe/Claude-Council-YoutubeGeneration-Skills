# dallal_parser

Turns a customer's Instagram DM into a clean cash-on-delivery order record for **Dallal**: name, Iraqi mobile number, governorate and address. It handles Iraqi Arabic, English, Arabizi, Kurdish script and mixtures of them.

The guiding rule: **a wrong but confident record costs a failed delivery, so the parser never guesses.** If a field isn't reliably in the message, it comes back `None` or flagged, and `needs_followup` tells the bot to ask the customer.

- Pure Python ≥ 3.9, standard library only. No network calls, no model, deterministic.
- About 1 ms per typical message.

## Install and use

```bash
pip install ./output          # or just put output/ on PYTHONPATH
```

```python
from dallal_parser import parse_order

order = parse_order("السلام عليكم 🌹\nاريد القطعة السودة قياس L\nفاطمة جاسم\n"
                    "الناصرية الشطرة قرب المستشفى\n٠٧٨٠١٢٣٤٥٦٧\nشكرا")
```

```json
{
  "schema_version": "1",
  "name": "فاطمة جاسم",
  "phone": "+9647801234567",
  "phones": ["+9647801234567"],
  "invalid_phones": [],
  "governorate": "Dhi Qar",
  "governorate_source": "city",
  "governorate_raw": "الناصرية",
  "address": "الناصرية الشطرة قرب المستشفى",
  "landmark": "المستشفى",
  "notes": ["اريد القطعة السودة قياس L"],
  "missing": [],
  "warnings": [],
  "confidence": {"name": "high", "phone": "high", "governorate": "high", "address": "high"},
  "needs_followup": false
}
```

Here is a message that needs a follow-up: `"مرحبا\nالكرادة داخل قرب ساحة الحرية\n0770123456"`. The result is:

- `name`: `None`.
- `phone`: `None`. `invalid_phones` holds `{"raw": "0770123456", "reason": "too_short"}`.
- `governorate`: `"Baghdad"` with confidence `"low"`, inferred from the district.
- warnings: `invalid_phone` and `governorate_inferred`.
- `missing` is `["name", "phone"]` and `needs_followup` is `true`.

**Customers often send their details over several DMs.** `parse_order` is stateless, so pass every customer message since the order prompt, joined with `"\n"`.

Other public helpers:

| function | purpose |
|---|---|
| `normalize_phone(s)` | Validates one phone string. Returns `+9647XXXXXXXXX` or `None`. |
| `resolve_governorate(s)` | Maps one place string to a governorate (`"هولير"` → `"Erbil"`). Returns `None` when nothing matches or the string is ambiguous. |
| `clean_text(s)` | Removes invisible characters and emoji and converts Arabic-Indic/Persian digits to ASCII. Letters are left as typed. |
| `GOVERNORATES`, `SCHEMA_KEYS`, `WARNING_CODES`, `INVALID_PHONE_REASONS` | Constants for integration code. |

These helpers also let a future LLM fallback reuse the same phone and governorate checks.

## Output schema

Every call returns exactly these keys, in this order, on every path, including empty input. Every value is JSON-serialisable.

| key | type | meaning |
|---|---|---|
| `schema_version` | str | `"1"` |
| `name` | str \| None | The customer's name as typed. Greetings, labels and intro words (`اسمي`, `I'm`) are removed; emoji and invisible characters are dropped. |
| `phone` | str \| None | The primary Iraqi mobile number in E.164 form, `+9647XXXXXXXXX`. |
| `phones` | list[str] | All valid distinct mobile numbers, with the primary first. |
| `invalid_phones` | list[{raw, reason}] | Things that looked like phone numbers but failed validation, with a reason (see below). |
| `governorate` | str \| None | One of the 19 English names below. |
| `governorate_source` | str \| None | `label` (after المحافظة:/city:), `explicit` (the governorate's own name), `city` (a city or qadha such as الناصرية or الزبير), `district` (a Baghdad district), or `reference` (only a street or landmark name mentions it). |
| `governorate_raw` | str \| None | The text that decided the governorate. |
| `address` | str \| None | The area and landmark text in the customer's script, with digits as ASCII. Parts are joined with ` - `. A leading governorate name is removed; city and qadha words are kept. |
| `landmark` | str \| None | The text after اقرب نقطة دالة, قرب, مقابل, خلف, يم, near, opposite and similar words. It also stays in `address`. |
| `notes` | list[str] | Leftover text: product, size and price chatter, and extra lines that might have been the name. |
| `missing` | list[str] | The core fields that are `None`, from `["name","phone","governorate","address"]`, in that fixed order. |
| `warnings` | list[{code, detail}] | `code` comes from the closed set below. `detail` is human-readable text for logs only, so don't branch on it. |
| `confidence` | {name, phone, governorate, address} | Each value is `high`, `medium`, `low`, or `None` when the field is missing. |
| `needs_followup` | bool | True if any core field is missing, any core confidence is `low`, or `governorate_inferred` is present. |

**Suggested bot logic:**
- If `needs_followup` is false, confirm the order.
- Otherwise, ask about the fields in `missing` and the low-confidence fields, using the warning codes below.

### Warning codes

| code | meaning | suggested follow-up (Iraqi dialect) |
|---|---|---|
| `empty_input` | No letters or digits (an emoji-only message, a voice note, `None`). | دزلي الاسم والرقم والمحافظة والعنوان رجاءً |
| `input_truncated` | The message was over 4,000 characters; only the start was parsed. | — |
| `multiple_phones` | More than one valid number. The primary comes first (labelled number, otherwise the first one). | Informational; couriers like backup numbers. |
| `invalid_phone` | A number-like string failed validation. See `invalid_phones[].reason`. | الرقم ناقص/زايد رقم، تأكد منه ودزه مرة لخ |
| `uncommon_prefix` | A valid but rare 076 number. Phone confidence is medium. | — |
| `phone_adjacent_digits` | Extra digits were written next to the number, e.g. `07701234567 2`. Phone confidence is medium. | رقمك 0770…؟ |
| `multiple_governorates` | Different governorates were mentioned. The documented rule picked one; confidence is low. | انت بأي محافظة بالضبط؟ |
| `governorate_inferred` | Guessed from a Baghdad district, a word that is also a personal name, a place next to the name, or only a street or landmark name. | بغداد صح؟ / شنو محافظتك؟ |
| `name_uncertain` | Several lines could be the name. The one nearest before the address was chosen; confidence is low. | الاسم الكامل شنو؟ |
| `name_single_word` | Only one word was given as the name. Confidence is medium. | (optional) الاسم الثلاثي رجاءً |
| `name_unverified` | An unlabelled line was taken as the name but contains no common given name (see `names.py`). Confidence is low. | اسمك الكامل شنو؟ |
| `address_short` | The address is a single word with no landmark. Confidence is low. | شنو اقرب نقطة دالة؟ |

`invalid_phones[].reason` is one of the following:
- `too_short`
- `too_long`
- `not_mobile`: a landline such as `01…` or `040…`
- `foreign`: a `+`/`00` number that isn't Iraqi
- `unknown_prefix`: `070` to `074`
- `ambiguous_grouping`: e.g. `0770123456 7` or `0770 123 4567 8`, where you can't tell which digit is the stray one

## Decisions and assumptions

A council of five reviewers (skeptic, user advocate, builder, Iraqi COD/dialect domain expert, quality engineer) designed and debated these decisions. The full trail is in `../.council/` (`DECISIONS.md`, `plan_v3.md`, the debate digests). The user wasn't available to answer questions, so each choice below is documented and can be overturned.

**Phones**
- Only Iraqi mobiles are accepted.
  - Valid prefixes: 075 (Korek), 077 (Asiacell), 078/079 (Zain).
  - 076 is accepted with a warning.
  - 070–074, landlines and foreign numbers are rejected.
- Accepted shapes: `07XXXXXXXXX`, `7XXXXXXXXX`, `9647…`, `+9647…`, `009647…`, and the common `+964 0770…` with a redundant trunk 0.
- Arabic-Indic and Persian digits are accepted, and so are mixes of the two. Invisible RTL marks inside the number are ignored, as is a trailing `+`.
- **Never fabricate.** Digit groups are joined only across spaces, `-`, `.`, `/` and brackets on the same line.
  - A group that already holds 8 or more digits is never glued to its neighbours.
  - A 1-digit group is never part of a multi-group number.
  - Nothing is ever trimmed, padded or "corrected".
- House and alley numbers after دار/زقاق/محلة, and quantities after عدد/قياس, are not phone digits.
- Arabizi digits such as `3li` and `7sen` are not phone digits.
- The governorate is never inferred from the phone operator: Iraqi mobile numbers aren't tied to a region.

**Governorates**
- There are 19 governorates. **Halabja** counts as its own governorate (Iraq's parliament approved it as the 19th in 2025). If your courier still files it under Sulaymaniyah, map it there downstream.
- English spellings used: Baghdad, Basra, Nineveh, Erbil, Sulaymaniyah, Duhok, Halabja, Kirkuk, Diyala, Anbar, Babil, Karbala, Najaf, Wasit, Maysan, Dhi Qar, Muthanna, Qadisiyah, Saladin.
- **Matching** works on whole words, after harmonising spelling variants: hamza forms, ة/ه, ى/ي, Kurdish letters, harakat and tatweel.
  - One proclitic is understood: ببغداد, بالبصرة, للنجف.
  - `ال` is never dropped automatically. Because of that, nisba surnames (البصري, النجفي, البغدادي) never match.
- **Cities and qadhas count with high confidence**, because customers name their city: الناصرية→Dhi Qar, الحلة→Babil, الكوت→Wasit, الديوانية→Qadisiyah, العمارة→Maysan, السماوة→Muthanna, الزبير→Basra, زاخو→Duhok, and so on.
- **Distinctive Baghdad districts** imply Baghdad with low confidence plus `governorate_inferred`: الكرادة, زيونة, الدورة, الشعلة, مدينة الصدر, الكاظمية, الأعظمية and others.
  - اليرموك and المنصور are deliberately excluded, because both are also west-Mosul districts.
  - Neighbourhood names found in many cities (حي العسكري, الجمهورية, حي الحسين, الجزائر…) never decide the governorate.
- **Resolution order:**
  1. a labelled value
  2. a governorate or city name, preferring one at the start of a line, then the first one
  3. a Baghdad district
  4. a street or landmark reference

  A mention right after شارع/كراج/مول/حي/جسر/مستشفى… is a *reference* and is ignored when there is other evidence: `بغداد … قرب كراج النجف` → Baghdad. A real conflict gives `multiple_governorates` with low confidence.
- **Words that are also personal names or ordinary words count only in a strong position.**
  - Personal names: مثنى, ميسان, حمزة, ديالا, الرفاعي…
  - Ordinary words: رمادي = grey, الكوت = the coat, عمارة = building, حلة = outfit.
  - Strong positions: after a governorate label, alone on a line, directly before an address word or another place, or (for ordinary words) at the start of a non-product line.
  - So `مثنى حسين` is a name and `اريد الكوت الاسود` is a coat.
  - A word that follows عبد/ابو/ام is part of a name (عبد الخضر, ابو القاسم).
- Disputed towns (عقرة, مخمور, طوزخورماتو, الشيخان) are left out, so the bot asks.

**Name and address**
- **Labels come first**, in Arabic, English and Kurdish: الاسم الثلاثي, الرقم, المحافظة, المنطقة, اقرب نقطة دالة, name:, ناوم… A label's value can be on the next line.
  - A label binds only if its value fits the field. `رقم الدار 12` is address text, not a phone.
  - Text after `المحافظة:` that isn't the governorate goes to the address (`المحافظة: البصرة الجزائر`).
- **Greetings, thanks and acknowledgements are stripped**: السلام عليكم, هلا اخي, صباح الخير, تمام, شكرا, emoji…
  - Greetings that are also names (هلا, زين, سلام) are kept when a name follows: `هلا محمد كاظم` stays a name.
- **Product, size and price lines go to `notes`.**
- **An unlabelled name needs positive evidence.** A line is accepted as the name with high confidence only if it contains a common given name from `names.py`. Otherwise the name is still returned, but with low confidence and `name_unverified`, so the bot confirms it. A list of chatter can never be complete (`عليكم السلام`, `جزاك الله خير`, colours, sizes); a list of names covers most customers. On the test data, no real name was downgraded and 0 of 34 tested chatter lines were accepted. Labelled names (`الاسم: …`) don't need this.
- **Choosing the name.** It is never simply "the first line". The name candidate is a short, letters-only line with no place or address words. If several lines qualify, the one nearest before the address is chosen with `name_uncertain`.
- **Single-line messages** (`علي حسين بغداد الكرادة 0770…`) are split at the first place word.
- **Address text stays in the customer's script.** Couriers navigate by landmark, so `landmark` is also extracted separately.
  - An address that is only a governorate name (`بغداد`) counts as missing, so the bot asks for the area and nearest landmark.
- **Input handling:** `None` is treated as an empty message. Any other non-string input raises `TypeError`. Input over 4,000 characters is truncated with a warning.

## How it works

`clean_text` → phones extracted per line and removed → split into segments (newline, `،`, `,`, `؛`, spaced ` / ` and ` - `, sentence-ending `.`/`؟`) → strip greetings → labels → classify each remaining segment as name, address, notes or unclassified → resolve the governorate → assemble the address and landmark → set `missing`, `confidence` and `needs_followup`.

| module | contents |
|---|---|
| `normalize.py` | Display cleaning and the matching key (`fold`). |
| `phones.py` | Phone extraction, grouping rules and validation. |
| `gazetteer.py` | Place data (governorates, cities, Baghdad districts, gated words, reference words). Pure data. |
| `lexicon.py` | Labels, greetings, product and address words. Pure data. |
| `names.py` | Common Iraqi given names (Arabic, Kurdish, Arabizi): positive evidence for unlabelled names. Pure data. |
| `governorate.py` | Place mentions, gating and resolution. |
| `parser.py` | Segmentation, roles and assembly. |
| `schema.py` | Keys, warning codes and reasons. |

To support a new spelling or town, add it to `gazetteer.py` or `lexicon.py`; no code change is needed. A test checks that every alias is reachable.

## Tests

```bash
cd output
python3 -m unittest discover -s tests -v        # pytest also works if installed
python3 tests/test_holdout.py --report          # per-field holdout scores
```

There are 90 tests, all standard-library `unittest`. pytest wasn't installable in the build environment.

| file | covers |
|---|---|
| `test_acceptance.py` | Charter acceptance tests AT1–AT9, council tests AT10–AT26, and AT27–AT29: regression tests for every finding fixed after the council's two reviews of the built package. These cover phone formats, labelled, unlabelled, English and Arabizi messages, aliases, invalid numbers, robustness, speed, ambiguity, nisba surnames, street references, coat/grey/building collisions, name collisions, greetings that are names, phone grouping, labels with area, and joined DMs. |
| `test_units.py` | Normalisation, phone canonicalisation, alias reachability, excluded words, `resolve_governorate`. |
| `test_corpus.py` | The 65-message development corpus (`tests/data/corpus.json`). It also runs 500 seeded decorated/shuffled variants and 1,000 random strings, asserting invariants: schema keys, valid JSON, phone format, governorate in the list, `missing` consistent with the fields, no invented or greeting/label words in the name, phone digits not leaking into the address, and shuffle stability where it applies. |
| `test_holdout.py` | Gates on two holdout sets written by separate agents that never saw the code: zero confident-wrong phones and governorates, at most one confident-wrong name, plus floors. |

### Holdout results (honest numbers)

| set | phone | governorate | name | address |
|---|---|---|---|---|
| `holdout.json`: 30 DMs, written before the build | 30/30 | 30/30 | 30/30 | 30/30 |
| `holdout_blind.json`: 40 DMs, written after the build. **First run, before any change** | **40/40** | **40/40** | **34/40** (4 confidently wrong) | **37/40** |
| `holdout_blind.json` after generic fixes and the review fixes | 40/40 | 40/40 | 40/40 | 40/40 |

Caveats:
- One council seat read `holdout.json` during debate, so that set is only partly unseen.
- The fixes made after the blind run were general lexicon and rule changes, not edits for specific cases:
  - labels with و and pronoun suffixes (واسمي, اسمها, ورقمها)
  - Kurdish ناوم/nawm
  - Arabizi address words (7ay)
  - sentence punctuation and `…على: name` treated as separators
  - greeting tails (هلا بيكم)

  Since those fixes, the blind set is no longer blind. **The blind first-run row is the best estimate of accuracy on new messages:** phone and governorate were never wrong; the name was the weakest field.

**The holdout sets are saturated, so don't read 100% as the real accuracy.** In review, five reviewers spent a short adversarial session trying to break the built package. Within minutes they found inputs that came out confidently wrong:
- a labelled name that swallowed the address
- dialect chatter (`اني مستعجل`, `ان شاء الله`) taken as the name
- `Babil hotel` read as the governorate
- a corrected phone number ignored

Across two review passes, every blocker and major finding the reviewers reported was reproduced and fixed, each with a regression test (AT27–AT29). Expect more of this kind of failure on real traffic.

## Known limitations

- **All test data is synthetic.** It was written by agents who know Iraqi usage, not taken from real DMs. Accuracy on real traffic is unmeasured. The biggest single improvement would be to log 50–100 real, anonymised DMs from a pilot shop and add the failures to `corpus.json`.
- **The name is the least reliable field**, especially in long chatty single-line messages. The parser flags uncertainty (`name_uncertain`, low confidence) rather than guessing, but it can still be confidently wrong on unusual phrasings.
- **Gazetteer coverage is limited.** It covers all 19 governorates, roughly 120 cities and qadhas and about 45 Baghdad districts. Districts of other cities (e.g. حي الجزائر in Basra) don't imply a governorate.
- **Kurdish (Sorani) support** covers place names, common labels and greetings, not general Kurdish text. Kurmanji in Latin script is barely covered.
- **No spelling correction** (fuzzy matching) for places: `بغدددد` isn't recognised. This is deliberate, to avoid false matches.
- **No product, size or quantity extraction.** That text is left in `notes`.
- **Unknown neighbourhoods go to `notes`.** A neighbourhood line that isn't in the gazetteer and has no address word (e.g. `الشعب` on its own line) is put in `notes` instead of the address, so the bot asks for the address again.
- **Chatty lines can still end up in the address.** Short chatter right after an address line is joined to it when it isn't in the chatter lexicon.
- **Other low-impact issues still open from review** (they fail safe or only add a follow-up):
  - hometown vs. residence (`اني من الناصرية بس ساكن ببغداد` picks the first)
  - the old name of Sadr City (`الثورة`)
  - spelling variants such as `بغدا`
  - a phone number split across lines, or typed with the letter O
  - a number the customer called wrong stays in `phones` as a backup
  - recipient text that shares a line with the place stays in the address
- **Orders placed for a relative** (`الطلب باسم اختي فاطمة`) return no name, so the bot asks.
- **Chatty single-line messages** can produce several name candidates. The parser then picks one with low confidence and `name_uncertain`.
- **`pip install ./output`** couldn't be run end-to-end in the build sandbox. Its Debian-patched setuptools/wheel fails with `install_layout` for every package, not just this one. The sdist builds correctly, and importing from the source folder works.
- **Couriers that still treat Halabja as part of Sulaymaniyah** need a one-line mapping downstream.
