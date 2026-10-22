# dallal_parser

`dallal_parser` turns a customer's Instagram DM, written in Iraqi Arabic, English, Arabizi or a mix, into a cash-on-delivery order record. The record holds a callable Iraqi mobile number, one of the 19 governorates, an address (area and landmark) and the customer's name. When something needed for delivery is missing, wrong or ambiguous, the record says so and includes a ready-made Arabic follow-up message for the customer.

It is rule-based and deterministic. It uses only the standard library (Python 3.9 or later), makes no network or LLM calls, and takes about 1–5 ms for a typical message (under 200 ms for 10 KB of adversarial input).

## Quick start

```python
from dallal_parser import parse_order

r = parse_order("الاسم: علي حسين\nالرقم: 07701234567\nبغداد الكرادة قرب جامع الرحمن")
# {'name': 'علي حسين', 'phone': '+9647701234567', 'governorate': 'Baghdad',
#  'address': 'الكرادة قرب جامع الرحمن', 'alt_phone': None, 'needs_review': False,
#  'missing': [], 'warnings': [], 'followup_ar': None}
```

Run the tests from this directory:

```
python3 -m unittest discover -s tests       # 64 tests, about 2 s
```

Evaluate a cases file:

```
python3 eval_cases.py cases.json            # raw mode if any case lacks "expected"
python3 eval_cases.py --raw cases.json      # always raw mode
```

The two modes:
- **Raw mode** prints only a JSON list `[{"id": ..., "output": <parse_order result>}]` to stdout.
- **Scored mode** is used when every case has `expected`. It prints a diff for each failing case and a summary, and exits with status 1 if any case fails.

Matching rules (in `dallal_parser/evalcases.py`):
- Values are compared after NFKC, casefolding and collapsing whitespace.
- `"~text"` means the field must contain `text`.
- `null` means the field must be None.

## Output schema

`parse_order(text: str) -> dict` always returns all of the keys below and never raises. Non-str input is coerced (`None` becomes `""`).

| key | type | meaning |
|---|---|---|
| `name` | str / None | Customer name as typed, with labels, emoji and edge punctuation removed. Arabic or Latin script. |
| `phone` | str / None | First valid Iraqi mobile, in the form `+9647[3-9]XXXXXXXX` (13 characters). |
| `governorate` | str / None | One of: Baghdad, Basra, Nineveh, Erbil, Sulaymaniyah, Duhok, Kirkuk, Diyala, Anbar, Babylon, Karbala, Najaf, Wasit, Maysan, Dhi Qar, Muthanna, Qadisiyyah, Saladin, Halabja. |
| `address` | str / None | Area, street and landmark as typed. Labels, the phone, the name and the governorate word itself are removed. Pieces from different lines or segments are joined with `، ` (or `, ` if there is no Arabic). |
| `alt_phone` | str / None | Second distinct valid mobile. |
| `needs_review` | bool | True if any core field is missing or there is a blocking warning. |
| `missing` | list | The core fields that are None, in the order name, phone, governorate, address. |
| `warnings` | list | Machine-readable flags (see the table below). |
| `followup_ar` | str / None | Arabic message to send to the customer. It is None exactly when `needs_review` is False. |
| `notes` | str / None | **[review 2, F43]** A recipient/courier note kept out of the address, e.g. `اخوي اسمه حيدر هو يستلم`. Informational only; never affects `needs_review`. |

### Warnings

| warning | meaning | blocking? | what to tell the customer (part of `followup_ar`) |
|---|---|---|---|
| `phone_invalid_length` | A phone-like digit run (9 or more digits) does not fit any valid form. | yes | الرقم ناقص أو غلط، ممكن ترسله مرة ثانية (11 رقم يبدي بـ 07)؟ |
| `phone_invalid_prefix` | An 11-digit number starts with 070, 071 or 072, which are not mobile prefixes. | yes | الرقم ناقص أو غلط، ممكن ترسله مرة ثانية (11 رقم يبدي بـ 07)؟ |
| `phone_foreign` | A number starting with `+` or `00` has a country code other than 964. | yes | نحتاج رقم عراقي يبدي بـ 07 حتى المندوب يتصل بيك |
| `phone_ambiguous_prefix` | A bare 10-digit number could be formed only by dropping a leading digit group (for example `44 7700 900123`). `phone` is left None. | yes | الرقم ناقص أو غلط، ممكن ترسله مرة ثانية (11 رقم يبدي بـ 07)؟ |
| `phone_ambiguous_join` | A valid number could be formed only by joining a long group (9 or more digits) with a 1–2 digit group (`0770123456 4`). `phone` is left None. | yes | الرقم ناقص أو غلط، ممكن ترسله مرة ثانية (11 رقم يبدي بـ 07)؟ |
| `phone_invalid_chars` | A phone attempt contains letter look-alikes (`077O1234567`, `0770l234567`). It is never repaired. | yes | الرقم ناقص أو غلط، ممكن ترسله مرة ثانية (11 رقم يبدي بـ 07)؟ |
| `multiple_governorates` | Two governorates (or governorate capitals) are named and there is no single delivery cue. | yes | نوصل الطلب لـ A لو B؟ |
| `governorate_conflict` | A governorate is named together with a city or district of another governorate. | yes | نوصل الطلب لـ A لو B؟ |
| `internal_error` | An unexpected exception happened and an empty record was returned. | yes | the "missing" questions |
| `governorate_inferred_from_city` | The governorate was deduced from a city or district name. | no | – |
| `phone_trunk_zero_removed` | The customer wrote `+964 0 7XX…`; the redundant 0 was removed. | no | – |
| `extra_phones` | There were more than two distinct valid mobiles; only two were kept. | no | – |
| `input_truncated` | The input was longer than 20,000 characters and was cut. | no | – |
| `phone_corrected` | The customer corrected their number (`غلط`, `الصحيح`, `اقصد`, `بالخطأ`, `sorry wrong`…). The number after the correction is used; the retracted one is discarded (not even `alt_phone`). | no | – |
| `landline_ignored` | An Iraqi landline (area code 01–06, 9–10 digits) was written. Only mobiles are used. | no | – (if there is no mobile, phone is missing and the customer is asked for one) |

When a field is simply missing, `followup_ar` asks for it. The questions always come in this order: phone, governorate, address, name.

| missing field | question |
|---|---|
| phone | ممكن رقم موبايلك؟ |
| governorate | بيا محافظة حضرتك؟ |
| address | ممكن العنوان بالتفصيل: المنطقة وأقرب نقطة دالة؟ |
| name | ممكن الاسم الكامل؟ |

The message opens with `هلا بيك 🌹` and ends with `وشكراً`. All templates live in `dallal_parser/followup.py`.

## Integrating in Dallal

```python
r = parse_order(dm_text)
if r["needs_review"]:
    reply_to_customer(r["followup_ar"])      # or show it to the shop owner to send
else:
    create_courier_order(name=r["name"], phone=r["phone"], alt_phone=r["alt_phone"],
                         governorate=r["governorate"], address=r["address"])
```

Two things to know when integrating:
- **`governorate_inferred_from_city`** does not block delivery. You can show the governorate it chose in the order summary so the shop can glance at it.
- **Conversation history is not tracked.** Each DM is parsed on its own. If a customer sends their details across several messages, join those messages and pass the combined text in.

## Package layout

```
dallal_parser/
  __init__.py     public API: parse_order, GOVERNORATES
  normalize.py    matching-only folding + index map back to the original text
  phones.py       strict phone grammar (linear scanner, group-boundary segmentation)
  gazetteer.py    ALL data tables: governorates, cities, districts, labels, stop lists
  segment.py      tokeniser, label detection, segmentation
  places.py       gazetteer matching, false-friend rules, governorate resolution
  core.py         pipeline: name selection, address assembly, flags
  followup.py     closed template table for followup_ar
  evalcases.py    shared case matcher (tests + CLI)
eval_cases.py     eval CLI
tests/            unittest suite; tests/data/{dev_cases,regression_cases}.json
```

## Decisions & assumptions

These decisions come from the council's DECISIONS.md (D1–D12). Every judgement call is listed here because the user is unavailable. Places where this build refines or departs from the council text are marked **[builder]**.

### Phone numbers (D3)
- **Only Iraqi mobiles are accepted.** Couriers call mobiles, so landlines and foreign numbers never fill `phone`.
- **Accepted forms.** After removing separators, these are accepted: `07[3-9]XXXXXXXX`, `7[3-9]XXXXXXXX` (10 digits), and `9647[3-9]XXXXXXXX`, optionally preceded by `+` or `00`. All are normalised to `+9647…`.
  - Prefixes 073–079 cover every current operator (Zain, Asiacell, Korek and others). 070, 071 and 072 are rejected with `phone_invalid_prefix`.
- **Trunk zero.** `+964 0770…` is accepted, because dropping the redundant 0 invents nothing. It is flagged `phone_trunk_zero_removed`, which does not block.
- **No repair, ever.** A number is never trimmed, padded, or reinterpreted digit by digit.
  - `077012345678` (12 digits) is rejected whole.
  - `0770123456` (10 digits starting with 0) is rejected.
  - A 9-digit number is rejected.
  - Each of these gives `phone_invalid_length`, which blocks. A wrong digit causes a failed delivery; asking again costs one message.
- **Digits and separators.**
  - Arabic-Indic (٠-٩) and Persian (۰-۹) digits are accepted.
  - Digit groups join across up to 3 separator characters (space, `-`, `.`, `(`, `)`, `/`) on the same line.
  - Invisible bidi or zero-width marks inside a number are ignored.
  - A number glued to a word is accepted (`رقمي07801112233`).
- **Splitting a run of digits.** A run is only ever split where the customer put a separator. This means:
  - `07712345678 07501234567` gives two numbers.
  - `قطاع 10 07711112222` is accepted cleanly, and `قطاع 10` stays in the address.
  - A bare 10-digit number reached only by dropping a leading group (`44 7700 900123`, `دار 7 7712345678`) is flagged `phone_ambiguous_prefix`, which blocks. **[review 2, F46]** The guessed number is *not* put in `phone` (charter: no digit guessing); `phone` is None and the follow-up asks for the number again. This overrides D3's "kept but flagged".
    - **[builder]** The dropped group is also removed from the address.
  - The council rejected the proposal to flag 3-3-4 grouping (`770 123 4567`), because Iraqis commonly write numbers that way.
- **Foreign numbers.** `+` or `00` followed by a country code other than 964 gives `phone_foreign`, and the whole number is consumed so none of it leaks into the address.
- **[review 2, F32] Corrections.** If a correction word (غلط، الغلط، بالخطأ، الصحيح، الصح، اقصد، قصدي، sorry، wrong، correct…) appears between two numbers, the later number replaces the earlier ones. The retracted number is discarded, `phone_corrected` (non-blocking, the intent is explicit) is added, and the correction words never reach the name or address.
- **[review 2, F34] Ranking.** A number introduced by رقمي/موبايلي/my outranks an unmarked one, which outranks a number marked secondary (رقم ثاني، رقم البيت، رقم اخوي، احتياط، بديل، ارضي، second, backup, alternative, or `0771… هذا رقم اخوي`). The best becomes `phone`, the next `alt_phone`, and order breaks ties. Labels like بديل/البديل/alternative/ارضي are phone-introduction words, so they never leak into the address (F45, F39).
- **Several numbers.**
  - The first valid number becomes `phone` and the second distinct one becomes `alt_phone`.
  - Duplicates are merged.
  - More than two distinct numbers gives `extra_phones`.
  - Digit runs shorter than 9 digits (prices, quantities, house and sector numbers) are ignored and stay as address text.
  - Any phone-like run of 9 or more digits that fails validation gives a blocking warning, even if another valid phone exists.
  - **[review 1, F9]** Exception: an Iraqi landline (`0[1-6]` + 7–8 digits, e.g. Baghdad `01 718 1234`) gives the non-blocking `landline_ignored`.
- **[review 1, F23] Odd joins.** A number that could only be formed by joining a group of 9+ digits with a 1–2 digit group (`0770123456 4`, `0 7701234567`) is flagged `phone_ambiguous_join` (blocking) and, since review 2 (F46), `phone` stays None: nobody groups a number like that, so a digit may belong to something else. Normal groupings (4-3-4, 3-3-4, 4-3-2-2) are never flagged.
- **[review 1, F19] Letter look-alikes.** `077O1234567` or `0770l234567` gives phone None plus `phone_invalid_chars` (blocking), so the follow-up says the number looks wrong instead of asking for a number the customer already sent. The attempt never leaks into the address.
- **[review 1, F15/F26] Phone-introduction words.** A word such as رقم/الرقم/رقمي/ورقم/رقمها/تلفون/هاتف/number within the 3 words before a phone starts a phone label. So `هذا رقم اخوي 0770…`, `رقم المستلم: 0780…` and `تلفون البيت 01…` never reach the name or the address.
- **No inference from the phone.** The governorate is never guessed from the phone prefix.

### Normalisation (D2)
- **Folding is for matching only.** Before matching, text is folded: hamza forms become ا, ة becomes ه, ى becomes ي, and گ/ک, Persian ی and Kurdish ە ێ ۆ ڵ ڕ are mapped to their Arabic equivalents. Latin text is lowercased and accents are stripped.
- **Ignorable characters are dropped.** Tashkeel, tatweel and zero-width/bidi marks are removed, not turned into spaces. That is why `بـغـداد` and `البَصْرة` match.
- **Emoji and symbols act as word boundaries.**
- **Output is always as typed.** `name` and `address` are sliced from the original text through an index map, with whitespace squeezed. For example, `حي الأمير` keeps its hamza.

### Gazetteer tiers (D4)
All data is in `gazetteer.py`.
- **Tier 1: the 19 governorates.** Includes Arabic dialect spellings (`كربله`, `كربلا`, `دياله`, `حلبجه`, `اربل`), English and transliterated forms (Basrah, Hawler, Slemani, Dohuk, Kerbala, Thi Qar, Salahaddin…), and Kurdish script (`هەولێر`, `سلێمانی`, `دهۆک`, `کەرکووک`, `هەڵەبجە`).
- **Halabja is the 19th governorate.** It has been a KRG governorate since 2014 and was approved federally in 2025. It is never mapped to Sulaymaniyah.
- **Canonical names.** The canonical English names are the Wikipedia-style common names listed in the schema. Consistency matters more than which variant is chosen.
- **Tier 2: governorate capitals and district towns** (Mosul, Hilla, Kut, Amarah, Nasiriyah, Samawah, Diwaniyah, Ramadi, Tikrit, Baqubah, Zakho, Ankawa, Zubair, Shatra…), about 200 aliases in total.
  - Diwaniyah is tier 2, so `الديوانية` stays in the address. The city is not the same thing as the governorate.
- **Tier 3: well-known neighbourhoods that exist in only one city** (mainly Baghdad: الكرادة، المنصور، زيونة، مدينة الصدر، الدورة، البياع، الاعظمية… plus Basra's العشار, Erbil's Dream City, Mosul's الدواسة, Najaf's الحنانة).
- **[review 1, F4/F12/F5] Audit rule for tier 2.** No generic Arabic word is a district key: الحي ("the neighbourhood", formerly Al-Hay/Wasit), النصر, الاصلاح, الفهود, الحر, الرياض, العلم, بلد, الدير, الحيرة and يثرب were removed. Neither are common surnames/nisbas that equal town names: البغدادي, الرفاعي, السلمان, القاسم, الخضر and Arabic القائم were removed. These districts still resolve through their governorate or English names. `الحي الصناعي` therefore gives no governorate (and is asked), and `النجف الحي الصناعي` gives Najaf with no conflict.
- **Generic names are deliberately excluded.** Names that exist in many cities never decide a governorate: حي الحسين، حي العسكري، الجمهورية، الحسينية، العامرية، اليرموك، الثورة (bare)، الشعب، الامين، البلديات، حي اور، الزهراء، الاندلس، الجزائر، المعلمين، الشهداء، الشرطة، الزهور. A message that gives only one of these gets `governorate=None` and is flagged.
- **Spelling tolerance.** Arabic aliases match with or without ال and with one attached prefix (و ب ل لل بال وال …, and **[review 1, F6]** the dialect contraction عال/وعال = على+ال, e.g. `عالبصرة`; a separate `ع` before a city is treated as a preposition). Fixed religious epithets are part of the alias (`كربلاء المقدسة`, `النجف الاشرف`, `najaf al ashraf`, `الكاظمية المقدسة`), so they leave the address together with the governorate (F7). Latin aliases match through a spelling-tolerant skeleton (karrada = karada, mansoor = mansour, basrah = basra), and a leading `al`/`el` is optional.
- **Whole tokens only, longest match first.** This is why the pronoun `عنه` never matches the town Anah. English "Hit" is not an alias.
- **Collision aliases.** Some place names are also everyday words or personal names: الرمادي (grey), الكوت (coat), الهندية (Indian), الشامية, المنصور, الزبير, البياع, رانية, الامين, and others listed in `COLLISION_ALIASES`.
  - **[builder]** I added more to the list: الدورة, الشعلة, الخالص, الدبس, السعدية, الكرمة, الرطبة…
  - These must be written with ال (if the alias has it).
  - They are never evidence inside a product segment or a name.
  - They count only in an address context: a labelled address or governorate, a line that contains another place or a street/landmark word, an attached ب/ل, or a preceding من/في.
  - **[builder]** They also count when the whole message contains no product talk and the segment consists only of place names. This lets a bare `المنصور` resolve to Baghdad, as AT8 requires.

### Governorate resolution and false friends (D5)
- **Landmark nouns demote a place.** If a city name directly follows a landmark noun (شارع، كراج، جامعة، مطعم، مدرسة، مستشفى، سوق، حي، جسر, and about 60 more), it is landmark evidence only. Examples: `شارع بغداد` inside a Maysan address, `مطعم الموصل`, `جامعة صلاح الدين`, `حي القادسية`, `حي بابل`. The same applies to English nouns that come after the place (`Baghdad street`, `Mosul hotel`).
- **Landmark phrases.** A place inside a landmark phrase (after قرب/يم/گرب/جنب/مقابل/خلف/near…) is demoted when there is a plain place elsewhere in the message.
- **Landmark-only evidence never decides a governorate.**
- **Nisba surnames are not aliases.** البصري، الموصلي، النجفي… do not match.
- **عمارة (building) versus العمارة (Amarah).**
  - Bare `عمارة` means "building" and never matches.
  - `العمارة` followed by a number, رقم, شقة or طابق means a building.
  - `العمارة` after قرب/جنب/يم/مجمع, in a segment that already names a place, also means a building.
  - Otherwise `العمارة` is Amarah, in Maysan.
- **Governorate names that are also personal names** (ميسان، مثنى، صلاح الدين). In the leading name position (the first 3 words, or the 3 words just before the phone), they are treated as part of the name when the message mentions another place.
  - **[builder]** "Another place" can also be a place in the *same* governorate. For example, in `المثنى السماوة… / مثنى عباس 0770…` the name is مثنى عباس.
  - A labelled name (`اسمي صلاح الدين خليل`) is never used as place evidence.
- **District-named governorates.** `القادسية`, `بابل` and `واسط` that come after a place in another governorate, in the same segment, are treated as districts. For example, `تكريت القادسية` resolves to Saladin.
- **Resolution order.**
  1. Non-landmark hits beat landmark hits.
  2. If all remaining evidence points to one governorate, that governorate wins. If no tier-1 name was used, it adds `governorate_inferred_from_city`, which does not block.
  3. Capitals count as tier 1 for conflict checks.
     - Two governorates at tier-1 level give `multiple_governorates`, which blocks. The governorate is filled only when exactly one of them follows a delivery cue (ابعثوه/ارسلوه/وصلوه/دزوه/التوصيل… + ل/على/الى; send/deliver/ship to). Otherwise it is None. **There is no first-mention guessing** (chair ruling).
     - A tier-1 governorate against a tier-2 town of another governorate keeps the tier-1 governorate and adds `governorate_conflict`, which blocks.
  4. **[review 1, F28/F8] A tier-3 neighbourhood never conflicts.** Many neighbourhood names (حي الجهاد, الدورة, الشعلة) also exist outside the city they are best known in. So when any tier-1/tier-2 place is present, tier-3 hits of other governorates are dropped silently. `الكوت حي الجهاد` gives Wasit with no review. A tier-3 neighbourhood on its own still infers its governorate.
- **Product segments.** Lines with order words (اريد، اطلب، قياس، لون، سعر، قطعة، order, size, price…) never supply a name. Collision aliases in them are ignored.
  - **[builder]** Unambiguous place names in a product segment (tier 1 or 2, non-collision) still count, and the text from the first such place onward is kept as address. This handles `اريد اطلب بغداد الكرادة`. D5 excluded product segments entirely; that loses the governorate whenever a customer writes the order and the address on one line without a comma. Garment and colour words cannot trigger this, because they are all collision aliases.

### Labels and segmentation (D6)
- **What labels are recognised.** Labels in Arabic dialect, English and Arabizi are recognised for name, phone, governorate and address. The full lists are in `gazetteer.py`.
  - A label can carry an attached و (`واسمي`) and can be glued to digits.
  - It can be followed by `:`, `:-`, `/` or `=`.
  - A label ends the previous field.
- **When a phone label counts.** A phone label in the middle of a line, and the generic words رقم/الرقم/no/num/number/tel anywhere, count as labels only when a phone-like run of 9 or more digits follows. This keeps `زقاق رقم 5` and `street no 5` as address text.
- **City labels.** `المدينة`/`city` count as a label only at the start of a line or before a `:`. Labels are never matched on a word that is itself a place, so `مدينة الصدر` stays a place.
- **Name intro.** `انا`/`اني`/`ana`/`ani` introduce a name only when the next word looks like a name: not من, not ساكن, not a place, not an order verb. So `اني من البصرة` gives no name, while `انا علي من بغداد` gives `علي`.
- **Empty labels.** A label with an empty value at the end of a line carries over to the next line (`الاسم:` then `زينب علي` on the next line).
- **How text is split into segments.**
  - By line.
  - At `، , / | ; ؛ ! ? ؟`.
  - At ` - ` (a dash with spaces around it).
  - At `.` followed by a space, except after st/rd/no and between digits.
  - At phone numbers and at labels.

### Name (D7)
Candidates are tried in this order:
1. A labelled value, cut at the next label, digit, place, landmark word or stopword, with at most 5 words.
2. The `اسمي` / `my name is` / `انا X` phrase.
3. An unlabelled segment of 1–4 words. It is checked in this order: just before the phone (**[review 2, F36]** also across a comma/dash: `العنوان، حيدر علي، 0770…`), then alone on its own line, then just after the phone, then **[builder]** the first segment of a line (for `مريم كريم، ديالى …`). The segment must contain no landmark or street word, greeting, order word, question mark, or place (except a bare collision alias or a person-name governorate).
4. On the same line as the phone: the run of words just before the phone, stopping at a place or a number, and not inside a landmark phrase. Failing that, the leading run of words up to the first place.

Other name rules:
- **Arabizi.** Words such as `3li` count, provided they have 2 or more letters and fewer than 3 digits.
- **Kunyas.** `ابو X` / `ام X` are names. **[review 1, F29]** A kunya directly before the phone is the name even when it follows a landmark phrase (`قرب مستشفى الزهراء ام علي 0781…`), unless it directly follows a landmark noun (`قرب بيت ابو علي`).
- **[review 1, F22] Greeting words that are also given names** (سلام, هلا, رجاء, زين, نعم, امل) are stripped only when they are a whole segment (`هلا` on its own line) or are followed by another greeting. They are never stripped inside a name: `سلام حسن 0770…` gives `سلام حسن`, and `الاسم: سلام عبد الله` is kept whole.
- **[review 1, F24] Religious and polite formulae** (ان شاء الله, ما شاء الله, الله يحفظك, الحمد لله, تسلم ايدك…) are greeting phrases. Among own-line candidates, the one closest to the phone line wins.
- **[review 1, F25] Helper words are never names.** These include label words with an attached و/ل/لل (ورقم, والثاني, للزبونة) and relation/recipient words (اخوي, اختي, زوجي, الثاني, رقمها, اسمه, المستلم…). A run before the phone may stop at such a word (`للزبونة سارة رقمها 0771…` gives سارة).
- **[review 1, F5] Surnames in labelled names.** In a labelled name, an ال-word right after a name word that matches a town (not a governorate or capital) is a surname: `الاسم: علي الزبير`.
- **[review 1, F30]** `ali from najaf` / `علي من بغداد`: a word run directly before من/from + place is the name.
- **[review 1, F3/F31] Plausibility caps.** A name word has at most 25 characters and no letter repeated 3 times in a row, and the whole name has at most 60 characters. So `xxxxxxxxxx` or a 10 KB blob is never a name.
- **[builder]** **ال rule.** An unlabelled candidate whose first word starts with ال is rejected (for example `الجزائر`, `الزهور`). Iraqi given names almost never start with the article, while area names very often do. Exceptions are listed in `_AL_NAMES` (الاء، الهام، الياس، الحاج…). Labelled names are never rejected by this rule.
- If nothing qualifies, `name` is None. **A missing name alone sets `needs_review`** (chair ruling).

### Address (D8)
- **[builder]** **Which segments are included.** The address is built from everything that is left, in the original order. That means every segment except: the name, phone values, greeting-only or chatter-only segments, product talk, and questions with no place in them. D8 phrased this as "address-bearing segments". Taking what is left is more inclusive, so an unknown area name ("حي الامير", "Malta quarter") is not lost. Tests check addresses with "contains", so a little extra text is cheap, while a missing area costs a failed delivery.
- **What is removed.** Labels, phones, the name, and only the tier-1 governorate mention that won. Capitals and district towns stay (`الديوانيه شارع الجمهوري`, `الزبير`). Landmark mentions of cities stay word for word (`شارع بغداد`), and so do numbers (`قطاع ٤٤`, `زقاق رقم 5`).
- **Edges are trimmed.** Connectors, filler and helper words are removed from the ends: و، او، من، في، ساكن، على، ممكن، عندكم، اخوي، to, from… **[review 1, F21]** `على`/`الى` are recognised on the original spelling only, because folding turns `على` into `علي`, Iraq's most common name (`قرب جامع الامام علي` keeps `علي`).
- **[review 1 F13/F14/F27, reworked in review 2 F40/F41/F48/F49] Chatter cut.** Losing real address text is worse than keeping some chatter, so cuts are conservative:
  - Only clear clause starters cut the rest of a segment: payment/timing/call/thanks words (الدفع، كاش، باجر، الصبح، اتصلوا، ان شاء الله، شكرا، please، call، tomorrow…) and strong product words (قياس، مقاس، سعر، اريد، size، price…).
  - Words that also appear in landmark names are *not* cut words: اليوم، رجاء، before، when، model.
  - **Weak product words are judged in context.** `قطعة/القطعة` followed by a number is a plot/block number and part of the address (`حي الجامعة قطعة 12 دار 5`). `الف` is a price only after a number (`25 الف`, not `مكتبة الف باء`). `لون` is product only before a colour (`لون اسود`, not `لون البيت ابيض`). `طلب` after ابو or a landmark noun is a name (`معرض ابو طلب`).
  - Nothing is ever cut or trimmed right after a landmark noun or trigger, so a landmark keeps its proper name (`قرب مطعم اليوم`, `صيدلية رجاء`).
  - A quantity directly before a cut product word goes with it (`… 2 قطعة`).
  - A segment that opens with a chatter clause and names no place is dropped whole (`please call before coming`). A question made only of chatter (`عندكم توصيل للبصرة؟`) contributes nothing.
  - Phone talk without a place (`هذا رقم اخوي`, `عفوا الرقم غلط`) is dropped.
- **[review 2, F43] Recipient notes** without a place (`اخوي اسمه حيدر هو يستلم`) stay out of the address but are returned in `notes`.
- **[review 2, F37] One delivery cue.** When a delivery cue decides between two governorates (`انا بالحلة بس ابعثوه للناصرية حي اريدو`), the address keeps only the delivery side (`حي اريدو`). The other governorate and the text before the cued city are dropped. The record still carries `multiple_governorates`, which blocks as D5 requires, so the shop confirms once.
- **When the address is None.** If nothing is left, or what is left is only governorate names, capitals and filler words (`فاطمة 0780… كركوك`, `… الناصرية`, `عندكم توصيل للبصرة؟`), the address is None and `needs_review` is set. A courier cannot deliver to "Kirkuk". **[review 1, F17]** To be precise about capitals: a capital *with* more detail stays in the address (`الديوانيه شارع الجمهوري`), but a capital *alone* counts as no address.

### Flags (D9) and robustness (D10)
- **needs_review.** It is set when `missing` is non-empty or there is any blocking warning (see the table above).
- **followup_ar.** Built from the closed template table. It is None exactly when `needs_review` is False.
- **Never raises.** The whole body is wrapped in a try/except. On failure it logs the traceback via `logging.getLogger("dallal_parser").exception(...)` and returns an empty record with `internal_error` (tested by forcing the path) **[review 1, F16]**.
- **Eval matching [review 1, F18].** The matcher uses exact string match after stripping/collapsing whitespace (plus NFKC). Case is significant, as in the charter. `eval_cases.py` prints a one-line error and exits with code 2 on an unreadable file, bad JSON or a wrong shape, and warns about an empty list or cases without `input`.
- **Long input.** Input over 20,000 characters is truncated (`input_truncated`).
- **Speed.** Every stage is linear: there are no backtracking regexes, phone segmentation windows are capped at 17 digits, and lookups are indexed by first token. A 10 KB adversarial input runs in under 200 ms (this is tested). A typical message takes about 1–5 ms.

### Out of scope
- Extracting product, quantity or price.
- State across separate DMs.
- Geocoding or courier API calls.
- Full Sorani Kurdish (only city names are covered).

## Known limitations
- **Names inside long chatter.** `Order for Zainab` / `… باسم زينب` inside a product segment gives the name **[review 2, F44]**. Other names buried in product sentences are not extracted, so they come back as None and are flagged.
- **A name right after a landmark phrase** on one line (`بغداد الكرادة قرب جامع الرحمن علي حسين 0770…`) cannot be told apart from the landmark's own name, so name is None and the order is flagged (F1). Kunyas are the exception (see Name).
- **A trailing name after the address with no phone next to it** (`+44 … بغداد الكرادة علي`) is not extracted (F2). It is always flagged, because the phone is missing or bad.
- **Unknown area on its own line.** An unknown area name with no ال on its own line can be taken as the name when there is no better candidate, for example `07701234567\nسبع قصور`.
- **Generic neighbourhoods are never inferred.** A customer who writes only `حي الحسين`, `الحي العسكري` or `الجمهورية` gets governorate None and is asked. This is intentional. Baghdad-specific names (`حي الجهاد`, `حي العامل`, `الكرادة`…) do infer Baghdad when nothing else is given.
- **Collision aliases on their own.** An alias such as `الرمادي` alone in a message that also talks about products is ignored, so the customer is asked for their governorate.
- **Over-flagging from stray numbers.** Any 9- or more-digit run that is not a valid mobile or a landline, such as an order or tracking number, sets a blocking phone warning.
- **Dev and regression cases.** No dev or regression case is a known failure (`KNOWN_FAILURES` is empty).

## Extending
- **Add a city, district or neighbourhood.** Append it to `TIER2` or `TIER3` in `gazetteer.py`. Arabic spellings with or without ال, ه/ة and hamza variants are handled for you. Add the English spellings you see.
- **Mark everyday words and personal names.** If a place name is also a common word or personal name, add it to `COLLISION_ALIASES`.
- **Generic neighbourhoods.** Never add a neighbourhood name that exists in more than one city to `TIER3`, and never add a generic Arabic word or a common surname as a `TIER2` key (see the audit rule).
- **Given names among greetings.** If a greeting word is also a given name, put it in `AMBIGUOUS_GREETING_NAMES`.
- **Other lists.** Labels, landmark nouns, greetings, order words and delivery cues are all plain lists in the same file.
- **After any change,** run `python3 -m unittest discover -s tests`.
