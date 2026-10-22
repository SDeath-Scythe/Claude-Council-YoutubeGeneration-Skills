"""Iraq's governorates and the place names that identify them.

Each governorate has three alias tiers:

``gov``
    Names of the governorate itself, including capitals that share the
    governorate's name (بغداد, البصرة, أربيل...). These are *removed* from the
    returned ``address`` because they are already in ``governorate``.
``city``
    Other major cities / district (qadha) centres (الموصل, الحلة, الزبير...).
    They identify the governorate and are *kept* in the address because the
    courier needs to know which city inside the governorate.
``district``
    Well-known neighbourhoods, mostly Baghdad (الكرادة, زيونة...). Lowest
    priority, kept in the address.

Deliberately left out: place names that are also common personal names,
surnames or everyday words (e.g. الرفاعي, القاسم, الحمزة, الدبس, حديثة, الحي,
بلد, عنة, الحسينية, الجمهورية) because matching them would mis-route orders
or corrupt the customer name. A leading ``!`` means "only with the article"
(see ``matcher.py``).

Halabja is included: it became Iraq's 19th governorate by law published in
May 2025 (separated from Sulaymaniyah).
"""

from __future__ import annotations

from dataclasses import dataclass

from .matcher import PhraseMatcher, key_set, token_in
from .normalize import edit_distance_le1, is_latin, norm_token, strip_article

GOVERNORATES: dict[str, dict] = {
    "Baghdad": {
        "ar": "بغداد",
        "gov": ["بغداد", "بغدات", "baghdad", "bagdad"],
        "city": ["المحمودية", "ابو غريب", "التاجي", "الطارمية", "المدائن",
                 "mahmudiyah", "abu ghraib", "taji", "tarmiyah", "madain"],
        "district": [
            "الكرادة", "!المنصور", "الكاظمية", "الاعظمية", "مدينة الصدر", "الشعلة",
            "!الدورة", "!البياع", "زيونة", "بغداد الجديدة", "العامرية", "الغزالية",
            "اليرموك", "الجادرية", "السيدية", "حي الجهاد", "حي العدل", "حي العامل",
            "الراشدية", "الحبيبية", "الزعفرانية", "الوزيرية", "باب الشيخ",
            "باب المعظم", "الباب الشرقي", "الكرخ", "الرصافة", "الصليخ", "المشتل",
            "الطالبية", "حي اور", "الكسرة", "بسماية", "شارع فلسطين", "الكريعات",
            "الكمالية", "الفضيلية", "الحارثية", "الداودي",
            "karrada", "karada", "kadhimiya", "kadhimiyah", "kazimiyah", "kadhimiyya",
            "adhamiya", "adhamiyah", "azamiyah", "sadr city", "zayouna", "zayuna",
            "jadriya", "jadriyah", "new baghdad", "yarmouk", "amiriya", "amiriyah",
            "ghazaliya", "ghazaliyah", "saydiya", "seidiya", "bismayah", "bismaya",
            "palestine street", "dora", "shula", "bayaa", "harthiya", "karkh", "rusafa",
        ],
    },
    "Basra": {
        "ar": "البصرة",
        "gov": ["البصرة", "basra", "basrah", "albasra", "albasrah"],
        "city": ["الزبير", "ابو الخصيب", "القرنة", "شط العرب", "الفاو", "ام قصر",
                 "خور الزبير",
                 "zubair", "zubayr", "abu al-khasib", "abu alkhasib", "qurna", "qurnah",
                 "shatt al-arab", "faw", "fao", "umm qasr"],
        "district": ["العشار", "الهارثة", "الجبيلة", "التنومة", "البراضعية", "المعقل",
                     "الاصمعي", "ashar", "tannuma", "hartha"],
    },
    "Nineveh": {
        "ar": "نينوى",
        "gov": ["نينوى", "نينوا", "nineveh", "ninawa", "ninewa", "ninava"],
        "city": ["الموصل", "تلعفر", "تل عفر", "سنجار", "الحمدانية", "قرقوش", "بخديدا",
                 "بعشيقة", "تلكيف", "القيارة", "حمام العليل", "برطلة",
                 "mosul", "mousel", "tal afar", "tel afar", "tal-afar", "sinjar", "hamdaniya",
                 "qaraqosh", "bakhdida", "bashiqa", "tel keppe", "tilkaif", "qayyarah"],
        "district": [],
    },
    "Erbil": {
        "ar": "أربيل",
        "gov": ["اربيل", "اربل", "هولير", "ههولير", "erbil", "arbil", "irbil", "hawler", "hewler", "hawlir"],
        "city": ["عنكاوا", "عينكاوا", "شقلاوة", "كويسنجق", "سوران", "رواندوز", "خبات",
                 "ankawa", "einkawa", "shaqlawa", "koya", "koysinjaq", "soran", "rawanduz"],
        "district": [],
    },
    "Sulaymaniyah": {
        "ar": "السليمانية",
        "gov": ["السليمانية", "سليمانية", "سليماني", "سلێمانی",
                "sulaymaniyah", "sulaymaniya", "sulaimaniyah", "sulaimaniya", "sulaymaniyya",
                "sulaimani", "sulaymani", "slemani", "slemany", "silemani", "suli"],
        "city": ["رانية", "جمجمال", "چمچمال", "دوكان", "بنجوين", "پێنجوێن", "قلعة دزة",
                 "دربندخان", "كلار", "كەلار", "سيد صادق",
                 "ranya", "rania", "chamchamal", "dukan", "dokan", "penjwen", "qaladiza",
                 "darbandikhan", "kalar", "said sadiq", "sayid sadiq"],
        "district": [],
    },
    "Duhok": {
        "ar": "دهوك",
        "gov": ["دهوك", "دهۆک", "duhok", "dohuk", "dahuk", "dihok"],
        "city": ["زاخو", "العمادية", "ئامێدی", "سميل", "سيميل", "سرسنك",
                 "zakho", "amadiya", "amedi", "amadiyah", "simele", "sumel", "sarsing"],
        "district": [],
    },
    "Halabja": {
        "ar": "حلبجة",
        "gov": ["حلبجة", "ههلهبجه", "هەڵەبجە", "halabja", "halabjah", "helebce"],
        "city": [],
        "district": [],
    },
    "Kirkuk": {
        "ar": "كركوك",
        "gov": ["كركوك", "كهركووك", "کەرکووک", "kirkuk", "karkuk", "kerkuk"],
        "city": ["الحويجة", "داقوق", "hawija", "hawijah", "daquq"],
        "district": [],
    },
    "Diyala": {
        "ar": "ديالى",
        "gov": ["ديالى", "ديالا", "diyala", "diala", "dyala"],
        "city": ["بعقوبة", "المقدادية", "الخالص", "بلدروز", "خانقين", "جلولاء", "مندلي",
                 "baqubah", "baquba", "baqouba", "baaqubah", "muqdadiya", "muqdadiyah",
                 "khalis", "baladrooz", "khanaqin", "jalawla", "mandali"],
        "district": [],
    },
    "Anbar": {
        "ar": "الأنبار",
        "gov": ["الانبار", "anbar", "alanbar"],
        "city": ["الرمادي", "الفلوجة", "هيت", "راوة", "الرطبة", "الخالدية",
                 "الحبانية", "الكرمة", "عامرية الفلوجة",
                 "ramadi", "fallujah", "falluja", "faluja", "hit city", "haditha", "qaim",
                 "rawa", "rutba", "rutbah", "khalidiya", "habbaniyah", "karmah"],
        "district": [],
    },
    "Babil": {
        "ar": "بابل",
        "gov": ["بابل", "babil", "babylon", "babel"],
        "city": ["الحلة", "المسيب", "المحاويل", "الاسكندرية", "hilla", "hillah", "al-hilla",
                 "musayyib", "mahawil", "iskandariya", "iskandariyah"],
        "district": [],
    },
    "Karbala": {
        "ar": "كربلاء",
        "gov": ["كربلاء", "كربلا", "كربلاء المقدسة", "karbala", "kerbala", "karbalaa", "karbela"],
        "city": ["الهندية", "طويريج", "عين التمر", "hindiya", "hindiyah", "twairij", "ain al-tamur"],
        "district": [],
    },
    "Najaf": {
        "ar": "النجف",
        "gov": ["!النجف", "النجف الاشرف", "najaf", "al-najaf", "alnajaf"],
        "city": ["الكوفة", "المناذرة", "المشخاب", "ابو صخير", "kufa", "kufah", "manathera",
                 "mishkhab", "abu sukhair"],
        "district": [],
    },
    "Wasit": {
        "ar": "واسط",
        "gov": ["واسط", "wasit", "wassit"],
        "city": ["الكوت", "الصويرة", "النعمانية", "بدرة", "العزيزية", "kut", "al-kut", "suwaira",
                 "suwayrah", "numaniyah", "badra", "aziziyah"],
        "district": [],
    },
    "Maysan": {
        "ar": "ميسان",
        "gov": ["ميسان", "maysan", "missan", "misan", "maysaan"],
        "city": ["!العمارة", "المجر الكبير", "قلعة صالح", "الميمونة", "الكحلاء",
                 "amarah", "amara", "al-amarah", "majar al-kabir", "qalat salih", "maimouna"],
        "district": [],
    },
    "Dhi Qar": {
        "ar": "ذي قار",
        "gov": ["ذي قار", "ذيقار", "ذي كار", "dhi qar", "thi qar", "dhiqar", "thiqar", "zi qar",
                "dhi-qar", "thi-qar"],
        "city": ["الناصرية", "ناصرية", "الشطرة", "سوق الشيوخ", "الجبايش", "قلعة سكر", "الغراف",
                 "nasiriyah", "nasiriya", "nasriya", "nasiriyya", "nassiriya", "shatra", "shatrah",
                 "suq al-shuyukh", "chibayish", "qalat sukkar"],
        "district": [],
    },
    "Muthanna": {
        "ar": "المثنى",
        "gov": ["!المثنى", "muthanna", "al-muthanna", "muthana"],
        "city": ["السماوة", "الرميثة", "samawah", "samawa", "al-samawah", "rumaitha", "rumaythah"],
        "district": [],
    },
    "Qadisiyyah": {
        "ar": "القادسية",
        "gov": ["القادسية", "qadisiyyah", "qadisiyah", "qadisiya", "qadissiya", "al-qadisiyyah"],
        "city": ["الديوانية", "ديوانية", "عفك", "الشامية", "diwaniyah", "diwaniya", "diwania",
                 "diwaniyya", "afak", "shamiya", "shamiyah"],
        "district": [],
    },
    "Saladin": {
        "ar": "صلاح الدين",
        "gov": ["صلاح الدين", "saladin", "salahuddin", "salah al-din", "salah ad-din", "salahaddin",
                "salah aldin", "salaheddine"],
        "city": ["تكريت", "سامراء", "سامرا", "بيجي", "الشرقاط", "طوزخورماتو", "طوز خورماتو",
                 "الطوز", "الضلوعية", "الدجيل",
                 "tikrit", "samarra", "baiji", "bayji", "shirqat", "sharqat",
                 "tuz khurmatu", "tuz khurmato", "tuz", "dhuluiya", "dujail"],
        "district": [],
    },
}

KIND_PRIORITY = {"gov": 1, "city": 2, "district": 3}


@dataclass(frozen=True)
class Location:
    start: int
    end: int
    governorate: str
    kind: str  # "gov" | "city" | "district" | "fuzzy-gov" | "fuzzy-city"


def _build_matcher() -> PhraseMatcher:
    m = PhraseMatcher()
    for gov, data in GOVERNORATES.items():
        for kind in ("gov", "city", "district"):
            for alias in data[kind]:
                m.add(alias, (gov, kind))
    return m


_MATCHER = _build_matcher()

# A governorate/city name right after one of these words is the name of a
# street, market, garage... ("شارع بغداد" in Basra, "كراج النجف" in Baghdad,
# "حي القادسية" in many cities), not the customer's governorate.
_PLACE_OF = key_set([
    "شارع", "طريق", "حي", "ساحة", "سوق", "جسر", "جامع", "مسجد", "مجمع", "فلكة", "تقاطع",
    "مستشفى", "مدرسة", "جامعة", "كلية", "كراج", "مطعم", "فندق", "مول", "معرض", "بنك", "مصرف",
    "فرع", "عكد", "دربونة",
    "street", "st", "road", "rd", "hospital", "university", "college", "garage", "square",
    "hotel", "mall", "school", "bank", "market",
])

# English puts the generic word after the name: "Al-Muthanna neighborhood"
# (a neighbourhood of Mosul), "Baghdad street".
_PLACE_AFTER = key_set([
    "street", "st", "road", "rd", "neighborhood", "neighbourhood", "district", "hospital", "school",
    "mall", "garage", "square", "university", "college", "market", "bridge", "hotel", "restaurant",
])

# Gov-level aliases that are too short or generic for fuzzy matching.
_FUZZY_MIN_LEN = 5


def find_locations(tokens: list[str]) -> list[Location]:
    out = []
    for m in _MATCHER.find_all(tokens):
        gov, kind = m.payload
        if kind in ("gov", "city") and _is_place_of(tokens, m.start, m.end):
            continue
        out.append(Location(m.start, m.end, gov, kind))
    return out


def _is_place_of(tokens: list[str], start: int, end: int) -> bool:
    if start > 0 and token_in(tokens[start - 1], _PLACE_OF):
        return True
    return (end < len(tokens) and is_latin(tokens[end - 1])
            and token_in(tokens[end], _PLACE_AFTER))


def strip_proclitic(token: str) -> str:
    """"بالديوانية" -> "الديوانية", "ببغداد" -> "بغداد" (for display in the address)."""
    candidates = [token]
    if token.startswith("لل"):
        candidates.append("ال" + token[2:])
    candidates += [token[1:], token[2:]]
    for cand in candidates:
        if len(cand) > 2 and _MATCHER.match_at([cand], 0, proclitics=False):
            return cand
    return token


def _fuzzy_keys() -> list[tuple[str, str, str]]:
    out = []
    for gov, data in GOVERNORATES.items():
        for kind in ("gov", "city"):
            for alias in data[kind]:
                alias = alias.lstrip("!")
                if " " in alias:
                    continue
                key = strip_article(norm_token(alias))[0]
                if len(key) >= _FUZZY_MIN_LEN:
                    out.append((key, gov, kind))
    return out


_FUZZY = _fuzzy_keys()


def fuzzy_find(tokens: list[str]) -> list[Location]:
    """Single-typo matches for governorate / city names (e.g. "بغدااد", "Baghdat").

    Exact spellings are skipped (``find_locations`` already decided about
    them, e.g. rejected "شارع بغداد"), as are tokens after شارع/حي/... and
    known name + one extra letter at the end ("بغدادي" = the surname
    Baghdadi). Kind is ``fuzzy-gov`` or ``fuzzy-city``.
    """
    out = []
    for i, tok in enumerate(tokens):
        key = strip_article(norm_token(tok))[0]
        if len(key) < _FUZZY_MIN_LEN - 1 or _is_place_of(tokens, i, i + 1):
            continue
        for alias_key, gov, kind in _FUZZY:
            if key == alias_key or not edit_distance_le1(key, alias_key):
                continue
            if key.startswith(alias_key) and len(key) == len(alias_key) + 1:
                # nisba adjective / surname: بغدادي، بصراوي-like forms
                continue
            if is_latin(key) != is_latin(alias_key):
                continue
            out.append(Location(i, i + 1, gov, "fuzzy-" + kind))
            break
    return out


def arabic_name(governorate: str) -> str:
    return GOVERNORATES[governorate]["ar"]
