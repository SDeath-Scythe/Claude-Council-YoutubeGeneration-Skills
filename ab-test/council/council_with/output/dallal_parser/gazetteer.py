"""Place-name data.  Pure data — edit freely, no logic here.

Spellings are written as customers type them; they are folded with
``normalize.fold`` at import time, so 'البصرة' and 'البصره', 'أربيل' and
'اربيل', 'هەولێر' and 'هولير' are the same key.  List bare forms explicitly
(e.g. 'نجف' next to 'النجف'): the matcher does not strip 'ال' on its own,
because that would turn surnames and first names (منصور, حمزة) into places.
It does strip one proclitic (و ب ل ف, and بال/وال/لل -> ال), so 'ببغداد' and
'بالبصرة' work.

Words that collide with ordinary vocabulary or common names are left out on
purpose (see EXCLUDED_NOTES); the parser abstains rather than guess.
"""

# Canonical English names (19 governorates incl. Halabja).
GOVERNORATES = (
    "Baghdad",
    "Basra",
    "Nineveh",
    "Erbil",
    "Sulaymaniyah",
    "Duhok",
    "Halabja",
    "Kirkuk",
    "Diyala",
    "Anbar",
    "Babil",
    "Karbala",
    "Najaf",
    "Wasit",
    "Maysan",
    "Dhi Qar",
    "Muthanna",
    "Qadisiyah",
    "Saladin",
)

# Tier A — the governorate's own name in Arabic, Kurdish script, English and
# Arabizi spellings.  A leading Tier A word is stripped from the address.
TIER_A = {
    "Baghdad": ["بغداد", "بغدات", "baghdad", "bagdad", "bghdad", "baghdaad"],
    "Basra": ["البصرة", "بصرة", "البصرا", "basra", "basrah", "al-basra", "albasra"],
    "Nineveh": ["نينوى", "نينوا", "نينوة", "ninawa", "nineveh", "ninewa", "ninevah", "nenawa"],
    "Erbil": ["اربيل", "أربيل", "اربل", "هولير", "هەولێر", "هەولیر", "ھەولێر", "erbil", "arbil", "irbil", "hawler", "hewler", "hawlir"],
    "Sulaymaniyah": [
        "السليمانية", "سليمانية", "السليمانيه", "سليماني", "السليماني", "سلێمانی",
        "sulaymaniyah", "sulaymaniya", "sulaimaniya", "sulaimaniyah", "sulaimani",
        "slemani", "slimani", "silemani", "suli",
    ],
    "Duhok": ["دهوك", "دهۆک", "دهۆك", "دهوگ", "duhok", "dohuk", "dahuk", "dihok", "dohok"],
    "Halabja": ["حلبجة", "حلبجه", "هەڵەبجە", "halabja", "halabjah", "halabcha"],
    "Kirkuk": ["كركوك", "کەرکووک", "كەركوك", "کەرکوک", "کرکوک", "kirkuk", "kerkuk", "karkuk"],
    "Diyala": ["ديالى", "ديالا", "ديالة", "diyala", "diala", "dyala"],
    "Anbar": ["الانبار", "الأنبار", "انبار", "anbar", "al-anbar", "alanbar"],
    "Babil": ["بابل", "babil", "babylon", "babel"],
    "Karbala": ["كربلاء", "كربلا", "كربله", "karbala", "kerbala", "karbalaa"],
    "Najaf": ["النجف", "نجف", "najaf", "al-najaf", "alnajaf"],
    "Wasit": ["واسط", "wasit", "wassit"],
    "Maysan": ["ميسان", "maysan", "misan", "maisan"],
    "Dhi Qar": ["ذي قار", "ذيقار", "ذى قار", "dhi qar", "thi qar", "zi qar", "dhiqar", "thiqar", "dhi-qar", "thi-qar"],
    "Muthanna": ["المثنى", "المثنا", "مثنى", "muthanna", "al-muthanna", "almuthanna"],
    "Qadisiyah": ["القادسية", "قادسية", "القادسيه", "qadisiyah", "qadisiya", "qadissiya", "al-qadisiyah"],
    "Saladin": ["صلاح الدين", "saladin", "salahaddin", "salah al-din", "salah aldin", "salahuddin", "salah al din"],
}

# Tier B — cities and districts (qadhas/nahiyas) that people write instead of
# the governorate.  Capitals are here too: Iraqis say الناصرية, not ذي قار.
TIER_B = {
    "Baghdad": ["ابو غريب", "أبو غريب", "المحمودية", "التاجي", "الطارمية", "abu ghraib", "mahmudiya"],
    "Basra": [
        "الزبير", "زبير", "ابو الخصيب", "أبو الخصيب", "القرنة", "الفاو", "فاو", "شط العرب",
        "ام قصر", "أم قصر", "الهارثة", "سفوان", "ابي الخصيب", "أبي الخصيب", "zubair", "zubayr", "qurna", "faw", "umm qasr", "abu al-khasib",
    ],
    "Nineveh": [
        "الموصل", "موصل", "تلعفر", "تل عفر", "سنجار", "الحمدانية", "قرقوش", "بغديدا", "بعشيقة",
        "تلكيف", "برطلة", "mosul", "mousl", "mosel", "tal afar", "tel afar", "sinjar", "qaraqosh", "bartella",
    ],
    "Erbil": [
        "عنكاوة", "عينكاوة", "شقلاوة", "سوران", "كويه", "كوية", "رواندوز", "ankawa", "ainkawa",
        "shaqlawa", "soran", "koya", "rawanduz",
    ],
    "Sulaymaniyah": [
        "رانية", "رانيه", "جمجمال", "چمچمال", "كلار", "دوكان", "دربندخان", "قلعة دزة", "ranya", "rania",
        "chamchamal", "kalar", "dukan", "darbandikhan",
    ],
    "Duhok": ["زاخو", "زاخۆ", "سميل", "العمادية", "ئامێدی", "zakho", "zaxo", "simele", "amedi", "amadiya"],
    "Halabja": [],
    "Kirkuk": ["الحويجة", "داقوق", "دبس", "hawija", "hawijah", "daquq"],
    "Diyala": [
        "بعقوبة", "بعقوبه", "المقدادية", "الخالص", "خانقين", "بلدروز", "جلولاء", "baquba", "baqubah", "baqouba",
        "muqdadiya", "khanaqin",
    ],
    "Anbar": [
        "الرمادي", "رمادي", "الفلوجة", "فلوجة", "الفلوجه", "هيت", "القائم", "قائم", "الرطبة", "عانة", "راوة",
        "الحبانية", "عامرية الفلوجة", "عامرية الصمود", "ramadi", "fallujah", "falluja", "heet", "qaim", "al-qaim", "rutba", "anah",
    ],
    "Babil": [
        "الحلة", "حلة", "الحله", "المسيب", "المحاويل", "الهاشمية", "الاسكندرية", "hilla", "hillah", "al-hilla",
        "musayyib", "mahawil",
    ],
    "Karbala": ["عين التمر", "الهندية", "طويريج", "hindiya", "ain al-tamur"],
    "Najaf": ["الكوفة", "كوفة", "المناذرة", "المشخاب", "kufa", "kufah"],
    "Wasit": ["الكوت", "كوت", "الصويرة", "العزيزية", "النعمانية", "بدرة", "kut", "al-kut", "alkut", "suwaira"],
    "Maysan": [
        "العمارة", "المجر الكبير", "قلعة صالح", "الميمونة", "amarah", "amara", "al-amarah", "alamarah",
    ],
    "Dhi Qar": [
        "الناصرية", "ناصرية", "الناصريه", "الشطرة", "شطرة", "سوق الشيوخ", "الغراف", "الجبايش", "قلعة سكر",
        "nasiriyah", "nasiriya", "nasriya", "nasiriyeh", "nasria", "shatra", "chibayish",
    ],
    "Muthanna": ["السماوة", "سماوة", "السماوه", "الرميثة", "samawah", "samawa", "samawa", "rumaitha"],
    "Qadisiyah": ["الديوانية", "ديوانية", "الديوانيه", "الشامية", "عفك", "diwaniyah", "diwaniya", "diwaniyeh", "afak"],
    "Saladin": [
        "تكريت", "سامراء", "سامرا", "بيجي", "الدجيل", "الشرقاط", "الضلوعية", "tikrit", "samarra", "baiji",
        "beiji", "shirqat",
    ],
}

# Tier C — Baghdad neighbourhoods (اليرموك and المنصور are deliberately absent:
# both are also districts of west Mosul). distinctive enough to imply Baghdad when the
# customer did not write a governorate.  Result is flagged
# governorate_inferred.  Names that exist in many cities (الجمهورية, حي الحسين,
# العسكري, الجزائر, الشرطة, الحرية, الشعب, الغدير, الحسينية ...) are NOT here.
TIER_C_BAGHDAD = [
    "الكرادة", "كرادة", "زيونة", "زيونه", "الدورة", "الشعلة", "مدينة الصدر", "الكاظمية",
    "كاظمية", "الاعظمية", "الأعظمية", "اعظمية", "البياع", "الغزالية", "الجادرية", "السيدية",
    "الزعفرانية", "باب المعظم", "الكرخ", "الرصافة", "الباب الشرقي", "الصليخ", "الوزيرية", "العطيفية",
    "الحارثية", "الطالبية", "البلديات", "الشالجية", "العلاوي", "ابو دشير", "شارع فلسطين", "شارع حيفا",
    "شارع السعدون", "الكسرة", "الاعلام", "حي الاعلام", "البتاويين", "الشورجة",
    "karrada", "karada", "zayouna", "zayona", "zayuna", "dora",
    "doura", "sadr city", "kadhimiya", "kadhimiyah", "kadhumiya", "adhamiya", "adhamiyah", "aadhamiya",
    "jadriya", "jadiriya", "saydiya", "amiriya", "ghazaliya", "bayaa", "shula", "palestine street",
]

# Phrases that contain a governorate name but must not be stripped from the
# start of the address (they *are* the neighbourhood).
EXPLICIT_PHRASES = {
    "Baghdad": ["بغداد الجديدة", "new baghdad"],
}

# Words that only count as a place in a strong position (start of a
# location segment, a line of their own, or after a governorate label):
# 'عمارة 5' is a building, 'الكوت الاسود' is a black coat.
GATED = [
    "العمارة", "الكوت", "كوت", "kut", "amara",
    # ordinary words: 'grey', 'outfit', 'standing' - and الرمادي is a surname
    "رمادي", "الرمادي", "حلة", "حله", "قائم", "القائم", "الرطبة", "الخالص",
]

# Place words that are also common personal names or surnames (مثنى, ميسان,
# حمزة, الرفاعي ...).  They count as a place only as a governorate/area label
# value, as a segment of their own, or as the first word of a segment that
# also has an address keyword or another place; they never disqualify a name.
# Listing a word here does not make it a place - it must also be an alias above
# (several are added just below as bare/ال forms).
NAME_COLLISIONS = [
    "مثنى", "مثنا", "المثنى", "ميسان", "نينوى", "نجف", "حمزة", "الحمزة", "خضر", "الخضر", "القاسم",
    "منصور", "المنصور", "امين", "الامين", "غدير", "الغدير", "رانية", "رانيه", "سوران", "زبير", "الزبير",
    "الرفاعي", "الشامية", "بدرة", "الهاشمية", "المسيب", "ديالى", "ديالا",
    "muthanna", "maysan", "mansour", "hamza", "soran", "zubair", "diala", "dyala",
]

EXCLUDED_NOTES = {
    "الحي": "Al-Hay (Wasit) — but means 'the neighbourhood'",
    "بلد": "Balad (Saladin) — but means 'country'",
    "حديثة": "Haditha (Anbar) — but means 'modern'",
    "علي الغربي": "Ali al-Gharbi (Maysan) — starts with a first name",
    "الرفاعي": "Rifai (Dhi Qar) — very common surname",
    "الخضر": "Khidr (Muthanna) — personal name",
    "الحمزة": "Hamza (Qadisiyah) — personal name",
    "القاسم": "Al-Qasim (Babil) — personal name",
    "اليرموك / المنصور": "Baghdad districts, but also west-Mosul districts — not used to infer Baghdad",
    "ana / hit / balad": "Latin spellings that are ordinary words (Arabizi 'ana' = 'I')",
    "عقرة / مخمور / طوزخورماتو / الشيخان": "disputed or split administration — left out, the bot asks",
    "المدينة": "Al-Midaina (Basra) — means 'the city'",
}

# Words that, right before a place name, make it a reference (street, garage,
# mall ...) rather than where the customer lives: 'كراج النجف' in Baghdad.
REFERENCE_WORDS = [
    "شارع", "طريق", "كراج", "گراج", "مول", "حي", "سوق", "جامع", "مسجد", "مطعم", "مستشفى", "مستشفي",
    "فندق", "ساحة", "سيطرة", "جامعة", "مدرسة", "معرض", "مجمع", "جسر", "فلكة", "تقاطع", "محطة", "كلية",
    "مستوصف", "صيدلية", "صيدليه", "نهر", "سريع", "مطار", "مصرف", "بنك", "شركة", "دائرة", "ملعب", "نادي",
    "قاعة", "حديقة", "فرع", "قرية", "street", "st", "road", "rd", "garage", "mall", "hospital", "hotel",
    "square", "university", "bridge", "airport",
]

# English puts the noun after the place: 'Babil hotel', 'Basra street'.
REFERENCE_WORDS_AFTER = [
    "street", "st", "road", "rd", "hotel", "mall", "hospital", "garage", "school", "university", "college",
    "restaurant", "bridge", "square", "market", "tower", "center", "centre", "park", "company", "bank",
    "station", "airport", "gate", "highway",
]

# A word right after one of these is part of a personal name (عبد الخضر,
# ابو القاسم, ام علي), never a place, unless it completes a listed multi-word
# alias such as ابو الخصيب / ابو غريب / ام قصر.
NAME_PARTICLES = ["عبد", "ابو", "أبو", "ام", "أم", "بن", "بنت", "ال", "آل"]
