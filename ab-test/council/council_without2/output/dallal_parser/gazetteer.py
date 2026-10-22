"""Iraqi governorates and the cities/districts used to infer them.

Arabic alias notation:
    "بغداد"      -> matched as written; Arabic clitics و/ب/ل/ف may be attached.
    "(ال)بصرة"   -> the article is optional: matches "بصرة", "البصرة", "بالبصرة", "للبصرة".
    "الزبير"     -> the article is REQUIRED. Used for places whose bare form is
                    also a common word or personal name (الزبير/زبير, المنصور/منصور).

English aliases are lowercase; an "al-"/"al "/"el-" prefix is always allowed.

The city lists deliberately leave out place names that are also common words
or names (e.g. "الحي" in Wasit, "بلد" in Saladin, "الدور", "القاسم", "الحمزة",
"الرفاعي", "دبس" in Arabic, "Hit" in English) and neighbourhood names that exist in
several governorates (اليرموك, الحسينية, حي الجامعة ...). Missing a city only
costs an inference; a wrong match puts the parcel in the wrong governorate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import norm

# English name -> Arabic name (canonical forms returned to callers).
GOVERNORATES: dict[str, str] = {
    "Baghdad": "بغداد",
    "Basra": "البصرة",
    "Nineveh": "نينوى",
    "Erbil": "أربيل",
    "Sulaymaniyah": "السليمانية",
    "Duhok": "دهوك",
    "Halabja": "حلبجة",
    "Kirkuk": "كركوك",
    "Anbar": "الأنبار",
    "Babil": "بابل",
    "Karbala": "كربلاء",
    "Najaf": "النجف",
    "Wasit": "واسط",
    "Maysan": "ميسان",
    "Dhi Qar": "ذي قار",
    "Muthanna": "المثنى",
    "Qadisiyyah": "القادسية",
    "Diyala": "ديالى",
    "Saladin": "صلاح الدين",
}

# Names that identify the governorate itself (including capital cities that
# share or commonly stand for the governorate's name).
_GOVERNORATE_ALIASES: dict[str, tuple[list[str], list[str]]] = {
    "Baghdad": (["بغداد"], ["baghdad", "bagdad", "baghdaad", "bghdad"]),
    "Basra": (["(ال)بصرة", "(ال)بصره"], ["basra", "basrah", "basara"]),
    "Nineveh": (["نينوى", "نينوه", "نينوا"], ["nineveh", "ninawa", "ninewa", "nineva", "ninevah", "neineva"]),
    "Erbil": (["اربيل", "أربيل", "هولير", "هەولێر"], ["erbil", "arbil", "irbil", "hawler", "hewler", "hawlir"]),
    "Sulaymaniyah": (
        ["(ال)سليمانية", "(ال)سليمانيه", "سليماني", "السلیمانیة"],
        ["sulaymaniyah", "sulaimaniyah", "sulaymaniya", "sulaimaniya", "sulaimani", "sulaymani",
         "slemani", "slimani", "suleimaniyah", "sulaimania", "suli"],
    ),
    "Duhok": (["دهوك", "دهۆک"], ["duhok", "dohuk", "dahuk", "dihok", "dohok"]),
    "Halabja": (["حلبجة", "حلبجه", "هەڵەبجە"], ["halabja", "halabjah", "helebce"]),
    "Kirkuk": (["كركوك"], ["kirkuk", "karkuk", "kerkuk"]),
    "Anbar": (["(ال)انبار", "(ال)أنبار"], ["anbar"]),
    "Babil": (["بابل"], ["babil", "babylon", "babel"]),
    "Karbala": (["كربلاء", "كربلا", "كربلائ"], ["karbala", "kerbala", "karbalaa", "karbalah"]),
    "Najaf": (["(ال)نجف"], ["najaf", "nejef", "najef"]),
    "Wasit": (["واسط"], ["wasit", "wassit"]),
    "Maysan": (["ميسان"], ["maysan", "missan", "misan", "maysaan"]),
    "Dhi Qar": (["ذي قار", "ذيقار", "ذى قار", "ذي كار"], ["dhi qar", "thi qar", "dhiqar", "thiqar", "zi qar", "dhi-qar", "thi-qar", "di qar"]),
    "Muthanna": (["(ال)مثنى", "(ال)مثنا"], ["muthanna", "muthana", "al muthanna", "mothana"]),
    "Qadisiyyah": (["(ال)قادسية", "(ال)قادسيه"], ["qadisiyyah", "qadisiyah", "qadisiya", "qadisiyya", "diwaniyah province"]),
    "Diyala": (["ديالى", "ديالا", "ديالي"], ["diyala", "diyalah", "diala"]),
    "Saladin": (["صلاح الدين", "صلاحالدين"], ["saladin", "salahuddin", "salah ad din", "salah al din", "salah al-din", "salaheddine", "salah aldeen", "salahaddin"]),
}

# Cities / districts / well-known neighbourhoods -> governorate.
_CITY_ALIASES: dict[str, tuple[list[str], list[str]]] = {
    "Baghdad": (
        ["(ال)كرادة", "(ال)كراده", "المنصور", "(ال)اعظمية", "(ال)اعظميه", "(ال)كاظمية", "(ال)كاظميه",
         "مدينة الصدر", "مدينه الصدر", "(ال)زعفرانية", "(ال)زعفرانيه", "الدورة", "الدوره",
         "(ال)غزالية", "(ال)غزاليه", "العامرية", "العامريه", "زيونة", "زيونه", "(ال)جادرية", "(ال)جادريه",
         "بغداد الجديدة", "بغداد الجديده", "الشعلة", "الشعله", "ابو غريب", "أبو غريب", "(ال)تاجي",
         "(ال)محمودية", "(ال)محموديه", "(ال)طارمية", "(ال)طارميه", "(ال)مدائن", "(ال)كرخ", "(ال)رصافة",
         "(ال)رصافه", "البياع", "(ال)سيدية", "(ال)سيديه", "(ال)حارثية", "(ال)حارثيه", "(ال)وزيرية",
         "(ال)وزيريه", "(ال)صليخ", "(ال)كمالية", "(ال)كماليه", "(ال)نهروان", "(ال)حبيبية", "(ال)حبيبيه",
         "(ال)عطيفية", "(ال)عطيفيه", "(ال)يوسفية", "(ال)يوسفيه", "(ال)لطيفية", "(ال)لطيفيه",
         "(ال)رضوانية", "(ال)رضوانيه", "شارع فلسطين"],
        ["karrada", "karada", "al mansour", "al mansur", "adhamiya", "adhamiyah", "azamiya", "kadhimiya",
         "kadhimiyah", "kadhimiyya", "kazimiya", "sadr city", "zafaraniya", "zafaraniyah", "dora", "doura",
         "ghazaliya", "ghazaliyah", "amiriya", "amiriyah", "zayouna", "zayuna", "jadriya", "jadriyah",
         "new baghdad", "baghdad al jadida", "shula", "shuala", "abu ghraib", "abu ghuraib", "taji",
         "mahmudiya", "mahmudiyah", "tarmiyah", "tarmiya", "madain", "karkh", "rusafa", "rasafa", "bayaa",
         "saydiya", "saidiya", "harthiya", "harthiyah", "waziriya", "waziriyah", "sulaikh", "kamaliya",
         "nahrawan", "habibiya", "palestine street", "palestine st"],
    ),
    "Basra": (
        ["الزبير", "ابو الخصيب", "أبو الخصيب", "ابي الخصيب", "القرنة", "القرنه", "(ال)فاو",
         "شط العرب", "(ال)عشار", "(ال)تنومة", "(ال)تنومه", "(ال)جبيلة", "(ال)جبيله",
         "(ال)براضعية", "(ال)براضعيه", "(ال)هارثة", "(ال)هارثه", "(ال)طويسة", "(ال)طويسه",
         "ام قصر", "أم قصر", "سفوان"],
        ["al zubair", "al zubayr", "al zubeir", "abu al khaseeb", "abu al-khasib", "abul khaseeb", "abu alkhasib",
         "qurna", "qurnah", "faw", "fao", "shatt al arab", "shatt al-arab", "ashar", "tanuma", "tannumah",
         "jubaila", "jubaylah", "baradiyah", "baradhiya", "hartha", "umm qasr", "um qasr", "safwan"],
    ),
    "Nineveh": (
        ["(ال)موصل", "تلعفر", "تل عفر", "سنجار", "(ال)حمدانية", "(ال)حمدانيه", "بعشيقة", "بعشيقه",
         "برطلة", "برطله", "قرقوش", "بخديدا", "(ال)قيارة", "(ال)قياره", "حمام العليل", "تلكيف", "تل كيف", "زمار"],
        ["mosul", "mousel", "mosel", "mawsil", "tal afar", "tal afar", "tel afar", "talafar", "sinjar", "shingal",
         "hamdaniya", "hamdaniyah", "bashiqa", "bartella", "qaraqosh", "bakhdida", "qayyarah", "qayara",
         "hammam al alil", "tel keppe", "tilkaif", "tel kaif", "zummar"],
    ),
    "Erbil": (
        ["عنكاوة", "عنكاوه", "شقلاوة", "شقلاوه", "سوران", "كويسنجق", "راوندوز", "خبات"],
        ["ankawa", "ainkawa", "shaqlawa", "soran", "koya", "koysinjaq", "rawanduz", "rwanduz", "khabat"],
    ),
    "Sulaymaniyah": (
        ["رانية", "رانيه", "جمجمال", "چمچمال", "كلار", "كەلار", "بنجوين", "پێنجوێن", "دوكان", "قلعة دزة",
         "قلعه دزه", "دربندخان"],
        ["ranya", "rania", "chamchamal", "kalar", "penjwen", "penjwin", "dukan", "dokan", "qaladiza",
         "qaladze", "darbandikhan", "derbendikhan"],
    ),
    "Duhok": (
        ["زاخو", "(ال)عمادية", "(ال)عماديه", "ئامێدی", "سميل", "سێمێل", "عقرة", "عقره", "ئاکرێ", "سرسنك"],
        ["zakho", "zaxo", "amadiya", "amedi", "amadiyah", "semel", "simele", "sumel", "akre", "aqrah", "aqra",
         "sarsang"],
    ),
    "Kirkuk": (
        ["(ال)حويجة", "(ال)حويجه", "داقوق"],
        ["hawija", "hawijah", "huwaija", "daquq", "dibis"],
    ),
    "Anbar": (
        ["(ال)رمادي", "(ال)فلوجة", "(ال)فلوجه", "هيت", "حديثة", "حديثه", "القائم", "(ال)رطبة", "(ال)رطبه",
         "عانة", "عانه", "راوة", "راوه", "(ال)خالدية", "(ال)خالديه", "(ال)حبانية", "(ال)حبانيه"],
        ["ramadi", "fallujah", "falluja", "faluja", "haditha", "hadithah", "al qaim", "al-qaim", "qaim",
         "rutba", "rutbah", "rawah", "khalidiya", "khalidiyah", "habbaniyah", "habbaniya"],
    ),
    "Babil": (
        ["الحلة", "الحله", "(ال)مسيب", "(ال)محاويل", "الهاشمية", "الهاشميه", "الاسكندرية",
         "الإسكندرية", "الاسكندريه", "(ال)كفل"],
        ["hilla", "hillah", "hila", "musayyib", "musaiyib", "mussayab", "mahawil", "al hashimiya", "al hashimiyah",
         "iskandariya", "iskandariyah", "kifl"],
    ),
    "Karbala": (
        ["عين التمر", "طويريج"],
        ["ain al tamr", "ain tamr", "ayn al-tamr", "tuwairij"],
    ),
    "Najaf": (
        ["(ال)كوفة", "(ال)كوفه", "(ال)مناذرة", "(ال)مناذره", "(ال)مشخاب"],
        ["kufa", "kufah", "manathera", "manadhira", "mishkhab", "mushkhab"],
    ),
    "Wasit": (
        ["الكوت", "(ال)صويرة", "(ال)صويره", "(ال)نعمانية", "(ال)نعمانيه", "(ال)عزيزية", "(ال)عزيزيه",
         "جصان"],
        ["kut", "kut al amara", "suwaira", "suwayrah", "numaniyah", "numaniya", "aziziyah", "aziziya",
         "badrah", "jassan"],
    ),
    "Maysan": (
        ["العمارة", "العماره", "(ال)مجر الكبير", "قلعة صالح", "قلعه صالح", "علي الغربي", "(ال)كحلاء", "الميمونة", "الميمونه"],
        ["amarah", "al amarah", "majar al kabir", "majar al-kabir", "qalat salih", "qal'at salih",
         "ali al gharbi", "kahla", "maimouna", "maimuna"],
    ),
    "Dhi Qar": (
        ["(ال)ناصرية", "(ال)ناصريه", "(ال)شطرة", "(ال)شطره", "سوق الشيوخ", "(ال)جبايش", "قلعة سكر",
         "قلعه سكر", "(ال)غراف"],
        ["nasiriyah", "nasiriya", "nasriya", "nasriyah", "nassiriya", "nasseriya", "shatra", "shatrah",
         "suq al shuyukh", "souq al shuyukh", "chibayish", "chibaish", "qalat sukkar", "gharraf"],
    ),
    "Muthanna": (
        ["(ال)سماوة", "(ال)سماوه", "(ال)رميثة", "(ال)رميثه", "(ال)وركاء"],
        ["samawah", "samawa", "samaawa", "rumaitha", "rumaythah"],
    ),
    "Qadisiyyah": (
        ["(ال)ديوانية", "(ال)ديوانيه", "عفك", "(ال)دغارة", "(ال)دغاره",
         "غماس", "(ال)شنافية", "(ال)شنافيه"],
        ["diwaniyah", "diwaniya", "diwanieh", "dewaniya", "afak", "daghara",
         "ghammas", "shinafiya"],
    ),
    "Diyala": (
        ["بعقوبة", "بعقوبه", "(ال)مقدادية", "(ال)مقداديه", "(ال)خالص", "خانقين", "بلدروز", "جلولاء",
         "جلولا", "السعدية", "السعديه", "بني سعد"],
        ["baqubah", "baquba", "baqouba", "bakuba", "muqdadiya", "muqdadiyah", "khalis", "khanaqin",
         "khanaqeen", "balad ruz", "baladrooz", "jalawla", "jalula", "al saadiya", "bani saad"],
    ),
    "Saladin": (
        ["تكريت", "سامراء", "سامرا", "بيجي", "(ال)دجيل", "طوز خورماتو", "طوزخورماتو", "(ال)طوز",
         "(ال)شرقاط", "(ال)ضلوعية", "(ال)ضلوعيه", "(ال)اسحاقي"],
        ["tikrit", "samarra", "baiji", "beiji", "bayji", "dujail", "dujayl", "tuz khurmatu",
         "tuz khormato", "tuz", "shirqat", "sharqat", "dhuluiya", "duluiyah", "ishaqi"],
    ),
}

GOVERNORATE_KIND = "governorate"
CITY_KIND = "city"


@dataclass(frozen=True)
class GazetteerHit:
    start: int
    end: int
    governorate: str
    kind: str  # GOVERNORATE_KIND or CITY_KIND


_AR_CLITIC = "[وبفل]"


def _arabic_pattern(alias: str) -> str:
    if alias.startswith("(ال)"):
        core, article = alias[4:], "optional"
    elif alias.startswith("ال") and not alias.startswith("الله"):
        core, article = alias[2:], "required"
    else:
        core, article = alias, "none"
    core_key = norm(core)
    body = r"\s*".join(re.escape(w) for w in core_key.split())
    if article == "required":
        prefix = f"(?:{_AR_CLITIC}?ال|لل)"
    elif article == "optional":
        prefix = f"(?:{_AR_CLITIC}?ال|لل|{_AR_CLITIC})?"
    else:
        prefix = f"{_AR_CLITIC}?"
    return rf"(?<!\w){prefix}{body}(?!\w)"


def _latin_pattern(alias: str) -> str:
    words = re.split(r"[\s\-]+", norm(alias))
    # A leading "al" in the alias makes the article mandatory (al-Mansour is a
    # district, Mansour alone is usually a person).
    article = "required" if words[0] == "al" and len(words) > 1 else "optional"
    if article == "required":
        words = words[1:]
    body = r"[\s\-]*".join(re.escape(w) for w in words)
    prefix = r"(?:al|el)[\s\-]?" if article == "required" else r"(?:(?:al|el)[\s\-]?)?"
    return rf"(?<![a-z0-9]){prefix}{body}(?![a-z0-9])"


def _compile(table: dict[str, tuple[list[str], list[str]]], kind: str):
    compiled = []
    for gov, (arabic, latin) in table.items():
        for alias in arabic:
            compiled.append((re.compile(_arabic_pattern(alias)), gov, kind))
        for alias in latin:
            compiled.append((re.compile(_latin_pattern(alias)), gov, kind))
    return compiled


_PATTERNS = _compile(_GOVERNORATE_ALIASES, GOVERNORATE_KIND) + _compile(_CITY_ALIASES, CITY_KIND)


def find_places(key: str) -> list[GazetteerHit]:
    """All non-overlapping place mentions in ``key`` text, in order.

    Overlaps are resolved in favour of the longer match, so "بغداد الجديدة"
    (a Baghdad district) wins over the bare governorate name inside it.
    """
    raw: list[GazetteerHit] = []
    for pattern, gov, kind in _PATTERNS:
        for m in pattern.finditer(key):
            raw.append(GazetteerHit(m.start(), m.end(), gov, kind))
    raw.sort(key=lambda h: (-(h.end - h.start), h.start, h.kind != GOVERNORATE_KIND))
    chosen: list[GazetteerHit] = []
    for hit in raw:
        if all(hit.end <= c.start or hit.start >= c.end for c in chosen):
            chosen.append(hit)
    chosen.sort(key=lambda h: h.start)
    return chosen


def governorate_alias_keys() -> dict[str, str]:
    """Normalized governorate alias -> English name (used for fuzzy matching)."""
    out: dict[str, str] = {}
    for gov, (arabic, latin) in _GOVERNORATE_ALIASES.items():
        for alias in arabic:
            core = alias[4:] if alias.startswith("(ال)") else alias
            out[norm(core)] = gov
            out[norm("ال" + core)] = gov
        for alias in latin:
            out[norm(alias)] = gov
    # Capital cities are a very common way to write the governorate.
    for alias, gov in _CAPITALS.items():
        out.setdefault(norm(alias), gov)
        out.setdefault(norm("ال" + alias), gov)
    return out


_CAPITALS = {
    "موصل": "Nineveh", "رمادي": "Anbar", "حلة": "Babil", "كوت": "Wasit", "عمارة": "Maysan",
    "ناصرية": "Dhi Qar", "سماوة": "Muthanna", "ديوانية": "Qadisiyyah", "بعقوبة": "Diyala",
    "تكريت": "Saladin", "mosul": "Nineveh", "ramadi": "Anbar", "hilla": "Babil", "kut": "Wasit",
    "amarah": "Maysan", "nasiriyah": "Dhi Qar", "samawah": "Muthanna", "diwaniyah": "Qadisiyyah",
    "baqubah": "Diyala", "tikrit": "Saladin",
}
