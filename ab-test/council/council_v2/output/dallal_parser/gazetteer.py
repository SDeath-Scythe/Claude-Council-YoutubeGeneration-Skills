"""Plain data tables (D1, D4).  Edit this file to extend the parser.

All strings are written naturally; they are folded (hamza/ta-marbuta/ya,
Persian/Kurdish letters, case) when the lookup tables are built, so you do not
need to add every spelling variant by hand.  Arabic aliases match with or
without the article ال and with one attached prefix (و ب ل لل بال وال وب ول)
unless they are listed in COLLISION_ALIASES.  Latin aliases are matched through
a spelling-tolerant skeleton (karrada = karada, mansoor = mansour,
basrah = basra) and a leading "al"/"el" is optional.
"""

# --------------------------------------------------------------------------
# Tier 1: the 19 governorates.  canonical English name -> data
#   ar:       Arabic display name (used in follow-up messages)
#   aliases:  Arabic, Kurdish-script and Latin spellings of the governorate name
# --------------------------------------------------------------------------
GOVERNORATES = {
    "Baghdad": {"ar": "بغداد", "aliases": [
        "بغداد", "baghdad", "bagdad", "baghdaad"]},
    "Basra": {"ar": "البصرة", "aliases": [
        "البصرة", "البصره", "بصرة", "basra", "basrah", "busra", "al-basra"]},
    "Nineveh": {"ar": "نينوى", "aliases": [
        "نينوى", "نينوا", "نينوه", "nineveh", "ninawa", "ninewa", "ninava", "nineva", "ninawah"]},
    "Erbil": {"ar": "أربيل", "aliases": [
        "اربيل", "أربيل", "اربل", "هولير", "هەولێر", "erbil", "arbil", "irbil", "hawler",
        "hewler", "hawlêr", "hawleer", "arbeel"]},
    "Sulaymaniyah": {"ar": "السليمانية", "aliases": [
        "السليمانية", "سليمانية", "سليماني", "السليماني", "سلێمانی", "سلیمانی",
        "sulaymaniyah", "sulaymaniya", "sulaimaniyah", "sulaimaniya", "sulaimani",
        "slemani", "slemany", "silemani", "slimani", "sulemani", "suli", "slêmanî",
        "sulaymani", "sulaimany"]},
    "Duhok": {"ar": "دهوك", "aliases": [
        "دهوك", "دهۆک", "دهوگ", "duhok", "dohuk", "dahuk", "dihok", "dhok", "duhuk", "dohok"]},
    "Kirkuk": {"ar": "كركوك", "aliases": [
        "كركوك", "کەرکووک", "كەركووك", "کرکوک", "kirkuk", "kerkuk", "karkuk", "kirkook"]},
    "Diyala": {"ar": "ديالى", "aliases": [
        "ديالى", "ديالا", "دياله", "diyala", "diala", "diyalah"]},
    "Anbar": {"ar": "الأنبار", "aliases": [
        "الانبار", "الأنبار", "انبار", "anbar", "al anbar", "alanbar"]},
    "Babylon": {"ar": "بابل", "aliases": [
        "بابل", "babylon", "babil", "babel", "baabil"]},
    "Karbala": {"ar": "كربلاء", "aliases": [
        "كربلاء", "كربلا", "كربله", "كربلاء المقدسة", "كربلا المقدسة", "كربلاء المقدسه",
        "karbala al muqaddasa", "karbala al muqadasa", "karbala muqadasa", "karbala", "kerbala", "karbalaa", "karballa", "karbalā"]},
    "Najaf": {"ar": "النجف", "aliases": [
        "النجف", "نجف", "النجف الاشرف", "النجف الأشرف", "najaf al ashraf", "najaf ashraf", "najaf", "nadjaf", "an najaf"]},
    "Wasit": {"ar": "واسط", "aliases": [
        "واسط", "wasit", "wassit", "waset"]},
    "Maysan": {"ar": "ميسان", "aliases": [
        "ميسان", "maysan", "misan", "maisan", "meysan"]},
    "Dhi Qar": {"ar": "ذي قار", "aliases": [
        "ذي قار", "ذيقار", "ذى قار", "dhi qar", "thi qar", "dhiqar", "thiqar", "zi qar",
        "dhi-qar", "di qar", "zeqar"]},
    "Muthanna": {"ar": "المثنى", "aliases": [
        "المثنى", "مثنى", "muthanna", "muthana", "al muthanna"]},
    "Qadisiyyah": {"ar": "القادسية", "aliases": [
        "القادسية", "قادسية", "qadisiyyah", "qadisiya", "qadisiyah", "qadisiyya", "qadissiya",
        "al qadisiyah", "kadisiya"]},
    "Saladin": {"ar": "صلاح الدين", "aliases": [
        "صلاح الدين", "صلاحالدين", "saladin", "salahaddin", "salah al din", "salah ad din",
        "salahuddin", "salah aldin", "salaheddin", "salah el din", "salahadin"]},
    "Halabja": {"ar": "حلبجة", "aliases": [
        "حلبجة", "حلبجه", "هەڵەبجە", "halabja", "helebce", "halabcha", "halabjah", "helebje"]},
}

CANONICAL = tuple(GOVERNORATES)

# Governorate names that are also common personal names (D5(e)).  In the
# leading name position they are treated as name tokens when another
# governorate is mentioned.
PERSON_NAME_GOVS = ["ميسان", "مثنى", "المثنى", "صلاح الدين", "maysan", "muthanna", "salahaddin"]

# Tier-1 names that are also district names inside other cities (D5(e)):
# after a place of another governorate in the same segment they are districts.
DISTRICT_NAMED_GOVS = ["القادسية", "بابل", "واسط", "الاندلس"]

# --------------------------------------------------------------------------
# Tier 2: governorate capitals and district towns -> governorate.
#   (governorate, is_capital, [aliases])
# --------------------------------------------------------------------------
TIER2 = [
    # Audit rule (review 1, F4/F12/F5): no generic Arabic words (الحي، النصر، الاصلاح،
    # الحر، الرياض، العلم، بلد، الدير، الحيرة، يثرب ...) and no common surnames/nisbas
    # (البغدادي، الرفاعي، السلمان، القاسم، الخضر، القائم ...) as Arabic keys: they
    # appear as neighbourhood names or surnames all over Iraq.
    ("Nineveh", True, ["الموصل", "mosul", "mosel", "mousel", "mawsil", "al mosul"]),
    ("Nineveh", False, ["تلعفر", "تل عفر", "tal afar", "tel afar", "talafar", "سنجار", "sinjar",
                        "بعشيقة", "bashiqa", "قرقوش", "قره قوش", "قرة قوش", "بخديدا", "qaraqosh",
                        "bakhdida", "الحمدانية", "hamdaniya", "القيارة", "qayyarah", "تلكيف",
                        "tel keppe", "tilkaif", "حمام العليل"]),
    ("Babylon", True, ["الحلة", "hilla", "hillah", "al hillah"]),
    ("Babylon", False, ["المحاويل", "mahawil", "المسيب", "musayyib", "الهاشمية", "hashimiya",
                        "الاسكندرية", "iskandariya", "المدحتية", "الكفل"]),
    ("Wasit", True, ["الكوت", "kut", "al kut"]),
    ("Wasit", False, ["الصويرة", "suwaira", "العزيزية", "aziziyah", "النعمانية", "numaniyah",
                      "بدرة", "badra"]),
    ("Maysan", True, ["العمارة", "amarah", "amara", "al amarah"]),
    ("Maysan", False, ["علي الغربي", "المجر الكبير", "majar al kabir", "قلعة صالح", "qalat salih",
                       "الكحلاء", "الميمونة", "المشرح"]),
    ("Dhi Qar", True, ["الناصرية", "nasiriyah", "nasiriya", "nasriya", "nassiriya", "nasiriyya",
                       "nasriyah"]),
    ("Dhi Qar", False, ["الشطرة", "shatra", "shatrah", "سوق الشيوخ", "suq al shuyukh",
                        "قلعة سكر", "الغراف", "gharraf", "الجبايش", "chibayish",
                        "سيد دخيل", "الدواية", "البطحاء"]),
    ("Muthanna", True, ["السماوة", "samawah", "samawa", "al samawah"]),
    ("Muthanna", False, ["الرميثة", "rumaytha", "rumaitha", "الوركاء", "warka", "بصية"]),
    ("Qadisiyyah", True, ["الديوانية", "diwaniyah", "diwaniya", "diwaniyya", "al diwaniyah",
                          "dewaniya"]),
    ("Qadisiyyah", False, ["الشامية", "shamiya", "عفك", "afak", "الحمزة الشرقي", "الدغارة",
                           "daghara", "غماس"]),
    ("Anbar", True, ["الرمادي", "ramadi", "al ramadi"]),
    ("Anbar", False, ["الفلوجة", "fallujah", "falluja", "faluja", "هيت", "حديثة", "haditha",
                      "القائم", "qaim", "al qaim", "عانة", "راوة", "rawa", "الرطبة", "rutba",
                      "الكرمة", "الحبانية", "habbaniyah", "عامرية الفلوجة", "الصقلاوية"]),
    ("Saladin", True, ["تكريت", "tikrit", "tekrit", "takrit"]),
    ("Saladin", False, ["سامراء", "سامرا", "samarra", "samara", "بيجي", "baiji", "bayji", "beiji",
                        "الشرقاط", "shirqat", "sharqat", "طوزخورماتو", "طوز خورماتو", "طوز",
                        "tuz khurmatu", "tuz", "الضلوعية", "dhuluiya", "الدجيل", "dujail",
                        "سليمان بيك"]),
    ("Diyala", True, ["بعقوبة", "baqubah", "baquba", "bakuba", "baaquba"]),
    ("Diyala", False, ["المقدادية", "muqdadiya", "خانقين", "khanaqin", "khanaqeen", "بلدروز",
                       "baladrooz", "الخالص", "khalis", "جلولاء", "jalawla", "مندلي", "mandali",
                       "السعدية", "كفري", "kifri", "هبهب", "شهربان"]),
    ("Najaf", False, ["الكوفة", "kufa", "kufah", "المناذرة", "manathera", "المشخاب", "mishkhab"]),
    ("Karbala", False, ["الهندية", "طويريج", "tuwairij", "hindiya", "عين التمر", "ain al tamur"]),
    ("Basra", False, ["الزبير", "zubair", "zubayr", "ابو الخصيب", "abu al khaseeb", "abu al khasib",
                      "القرنة", "qurna", "qurnah", "الفاو", "faw", "fao", "شط العرب", "shatt al arab",
                      "الهارثة", "سفوان", "safwan", "ام قصر", "umm qasr"]),
    ("Duhok", False, ["زاخو", "zakho", "zaxo", "zakhu", "العمادية", "amedi", "amadiya", "amadiyah",
                      "سميل", "semel", "sumel", "simele", "عقرة", "akre", "aqra", "akra", "باطوفة",
                      "سرسنك", "sarsink", "بردرش"]),
    ("Erbil", False, ["عنكاوا", "عنكاوة", "عين كاوة", "عينكاوة", "ankawa", "ainkawa", "einkawa",
                      "سوران", "soran", "شقلاوة", "shaqlawa", "kopi", "كويسنجق", "koya", "koysinjaq",
                      "راوندوز", "rawanduz", "خبات", "khabat"]),
    ("Sulaymaniyah", False, ["رانية", "ranya", "rania", "كلار", "kalar", "جمجمال", "chamchamal",
                             "دوكان", "dukan", "dokan", "بنجوين", "penjwen", "دربندخان",
                             "darbandikhan", "قلعة دزة", "qaladze", "سيد صادق", "said sadiq", "بشدر"]),
    ("Kirkuk", False, ["الحويجة", "hawija", "hawijah", "داقوق", "daquq", "الدبس", "dibis",
                       "التون كوبري", "altun kupri"]),
    ("Halabja", False, ["خورمال", "khurmal", "بيارة", "byara"]),
]

# --------------------------------------------------------------------------
# Tier 3: unambiguous well-known neighbourhoods -> governorate (D4).
# Generic names that exist in many cities (حي الحسين، العسكري، الجمهورية،
# الحسينية، العامرية، اليرموك، الثورة، الشعب، الامين، البلديات، حي اور، الزهراء،
# الاندلس، الجزائر، المعلمين، الشهداء، الشرطة ...) are deliberately NOT here:
# they must never decide a governorate on their own.
# --------------------------------------------------------------------------
TIER3 = [
    ("Baghdad", ["الكرادة", "كرادة مريم", "المنصور", "زيونة", "مدينة الصدر", "مدينة الثورة",
                 "الشعلة", "الدورة", "البياع", "الاعظمية", "الكاظمية", "الغزالية", "حي الجهاد",
                 "السيدية", "بغداد الجديدة", "الزعفرانية", "الجادرية", "الحبيبية", "شارع فلسطين",
                 "الكمالية", "ابو غريب", "المحمودية", "التاجي", "الصليخ", "الوزيرية", "الشورجة",
                 "الكرخ", "الرصافة", "العطيفية", "الطالبية", "الكريعات", "الوشاش", "حي العامل",
                 "باب المعظم", "باب الشيخ", "الباب الشرقي", "الحارثية", "الراشدية", "الطارمية",
                 "اليوسفية", "المدائن", "الرضوانية", "سبع ابكار", "الدولعي", "العلاوي",
                 "الكسرة وعطش", "شارع السعدون", "الكاظمية المقدسة",
                 "الشالجية",
                 "karrada", "karada", "mansour", "mansur", "zayouna", "ziouna", "zayuna",
                 "sadr city", "madinat al sadr", "madinat alsadr", "medinat al sadr", "madinat sadr", "adhamiya", "adhamiyah", "aadhamiya", "kadhimiya", "kadhimiyah",
                 "kazimiyah", "kazimiya", "dora", "dawra", "jadriya", "jadiriya", "zafaraniya",
                 "ghazaliya", "ghazaliyah", "saydiya", "saidiya", "shula", "shuala", "bayaa",
                 "palestine street", "abu ghraib", "mahmudiya", "mahmudiyah", "taji", "karkh",
                 "rusafa", "waziriya", "harthiya", "new baghdad", "baghdad al jadida"]),
    ("Basra", ["العشار", "البراضعية", "الطويسة", "ashar", "al ashar"]),
    ("Erbil", ["dream city", "دريم سيتي", "english village", "italian village", "empire world",
               "ايمباير", ]),
    ("Nineveh", ["الدواسة", "dawasa"]),
    ("Najaf", ["حي الحنانة", "الحنانة"]),
]

# Aliases that are also ordinary words or personal names (D4 collision aliases).
# They match only when written with ال (no bare form), never inside a product
# segment or a name span, and only as place evidence in an address context
# (address-bearing segment/line, after ب/ل/من/في or an address label), or when
# the message has no product talk at all and the segment holds only places.
# Latin entries are matched without "al" but need the same context.
COLLISION_ALIASES = [
    "الرمادي",   # grey
    "الكوت",     # coat
    "الهندية",   # Indian
    "حديثة",     # new (fem.)
    "الشامية",   # Levantine
    "المنصور",   # personal name Mansour
    "الزبير",    # personal name Zubair
    "البياع",    # seller
    "رانية",     # female name
    "الامين",    # personal name / trustworthy
    "الدورة",    # course / turn
    "الشعلة",    # flame
    "الخالص",    # pure
    "الكرمة",    # vine / for the sake of
    "الرطبة",    # humid
    "الدبس",     # date syrup
    "السعدية",   # female name
    "الميمونة",  # female name
    "طوز",       # short form, also a word
    "القائم",    # standing / surname
    "الاسكندرية",  # Alexandria
    "الكفل",
    "mansour", "mansur", "dora", "kut", "tuz", "faw", "fao", "rania", "samara", "kopi",
]

# العمارة = Amarah (Maysan) but also "the building" (D5(d)).  Bare عمارة never
# matches; العمارة followed by a number/رقم/شقة/طابق, or preceded by these
# words in a segment that already has a place, is a building.
BUILDING_AMBIGUOUS = ["العمارة"]
BUILDING_NEXT_WORDS = ["رقم", "شقة", "طابق", "الطابق", "شقه", "no", "بلوك", "عمارة", "ط"]
BUILDING_PREV_WORDS = ["قرب", "جنب", "يم", "مجمع", "كرب", "عند", "مقابل", "خلف", "داخل", "بناية"]

# --------------------------------------------------------------------------
# Words that demote a following place name to a landmark (D5(a)): "شارع بغداد",
# "كراج النجف", "جامعة صلاح الدين", "مطعم الموصل" ...
# --------------------------------------------------------------------------
LANDMARK_NOUNS = [
    "شارع", "طريق", "باب", "سيطرة", "سيطره", "كراج", "گراج", "جامعة", "جامع", "مسجد", "مستشفى",
    "مستوصف", "مول", "فندق", "ساحة", "مجمع", "حي", "مطعم", "مدرسة", "صيدلية", "محل", "معرض",
    "مكتبة", "شركة", "مصرف", "بنك", "جسر", "نادي", "كلية", "ملعب", "فرن", "مخبز", "عيادة", "مطار",
    "محطة", "علوة", "سوق", "قاعة", "مركز", "دائرة", "مديرية", "بناية", "عمارة", "فلكة", "دوار",
    "تقاطع", "مفرق", "حسينية", "كنيسة", "مقهى", "كافيه", "قيصرية",
    "اسواق", "مولات", "معمل", "مصنع", "بوابة", "شقق", "عمارات", "مجمعات",
    "ابراج", "برج", "حديقة", "متنزه", "جادة", "زقاق", "فرع", "دربونة", "دربونه", "مخيم", "مكتب",
    "street", "st", "road", "rd", "hay", "university", "hospital", "mall", "hotel", "square",
    "restaurant", "school", "pharmacy", "shop", "market", "bridge", "bank", "times", "garage",
    "mosque", "church", "college", "station", "airport", "cafe", "company", "tower", "park",
    "center", "centre", "office", "bazaar", "gate", "complex",
]
# English nouns that demote a PRECEDING Latin place: "Baghdad street", "Mosul hotel".
LATIN_FOLLOW_NOUNS = [
    "street", "st", "road", "rd", "mall", "hospital", "university", "school", "hotel",
    "restaurant", "square", "market", "bridge", "bank", "station", "garage", "mosque", "church",
    "tower", "center", "centre", "park", "college", "airport", "cafe", "company", "office",
    "bazaar", "gate", "times", "pharmacy", "shop", "uni",
]

# Landmark phrase triggers: everything after them (to the end of the segment)
# is a landmark description.
LANDMARK_TRIGGERS = [
    "قرب", "يم", "گرب", "كرب", "جنب", "مقابل", "خلف", "قريب", "بجانب", "جانب", "ورا", "وره",
    "عند", "مجاور", "بالقرب", "قبال", "گبال", "كبال", "مقابيل", "بعد", "قبل", "اقرب",
    "near", "opposite", "behind", "beside", "next", "nearby", "across", "facing", "after",
    "before", "by",
]

# Street/landmark words: a segment containing one is address text, never a name (D7).
STREET_WORDS = [
    "قرب", "يم", "گرب", "كرب", "جنب", "مقابل", "خلف", "شارع", "حي", "قطاع", "محلة", "محله",
    "زقاق", "دار", "دربونة", "دربونه", "منطقة", "منطقه", "مجمع", "عمارة", "بناية", "شقة", "طابق",
    "فرع", "جادة", "قضاء", "ناحية", "قرية", "مدينة", "سيطرة", "ساحة", "جامع", "مسجد", "مستشفى",
    "مدرسة", "سوق", "مول", "جسر", "كراج", "مطعم", "صيدلية", "بيت", "بلوك", "عند", "بجانب",
    "قريب", "مقابيل", "ورا", "مفرق", "تقاطع", "دوار", "فلكة", "حسينية", "كنيسة", "بنك", "مصرف",
    "near", "street", "st", "road", "rd", "mall", "hay", "opposite", "behind", "beside",
    "quarter", "district", "sector", "alley", "block", "house", "building", "apt", "apartment",
    "floor", "villa", "village", "mosque", "hospital", "school", "market", "bridge", "square",
    "city", "town", "area", "neighborhood", "neighbourhood", "compound", "complex", "tower",
    "hotel", "restaurant", "pharmacy", "university", "church", "garage", "park", "next",
]

# --------------------------------------------------------------------------
# Labels (D6).  Matched on whole tokens; an attached و is tolerated.
# --------------------------------------------------------------------------
NAME_LABELS = [
    "الاسم الثلاثي", "الاسم الكامل", "الاسم الرباعي", "اسم الزبون", "اسم المستلم", "اسم الزبونة",
    "الاسم", "اسمي", "اسم", "اسمج", "اسمك", "الأسم",
    "full name", "my name is", "my name", "name", "customer name", "esmi", "ismi", "isme", "esme",
    "asmi", "el esm", "al ism", "alism", "el ism",
]
# Name intro words: only when followed by a plausible name (D6/D7).
NAME_INTRO = ["انا", "اني", "آني", "ana", "ani", "i am", "im", "i'm", "this is"]

PHONE_LABELS = [
    "رقم الهاتف", "رقم الموبايل", "رقم التلفون", "رقم الجوال", "رقم الواتساب", "رقم الواتس",
    "الرقم الثاني", "رقم ثاني", "رقم اخر", "رقم احتياط", "رقم التواصل", "رقمي", "الرقم", "رقم",
    "الهاتف", "هاتف", "هاتفي", "الموبايل", "موبايل", "موبايلي", "تلفون", "التلفون", "تلفوني",
    "الجوال", "جوال", "واتساب", "الواتساب", "واتس", "نمبر",
    "phone number", "phone no", "mobile number", "phone", "mobile", "number", "num", "tel",
    "telephone", "whatsapp", "contact", "raqmi", "rakmi", "ra8mi", "no", "nb", "mob", "ph",
]
# Generic phone labels: labels only when a phone-like digit run follows.
GENERIC_PHONE_LABELS = ["رقم", "الرقم", "no", "num", "number", "tel", "nb", "ph", "mob", "contact"]

GOV_LABELS = ["المحافظة", "محافظة", "محافظه", "governorate", "province", "gov"]
CITY_LABELS = ["المدينة", "city", "town"]  # only at line start or before ":"

ADDRESS_LABELS = [
    "اقرب نقطة دالة", "أقرب نقطة دالة", "نقطة دالة", "اقرب نقطة", "اقرب نقطه دالة",
    "العنوان الكامل", "العنوان بالتفصيل", "العنوان", "عنواني", "عنوان", "المنطقة", "منطقتي",
    "المحلة", "ساكن", "ساكنة", "ساكنين", "سكني", "السكن", "اسكن",
    "full address", "address", "area", "landmark", "location", "nearest point", "addr",
    "el3nwan", "al3nwan", "3nwan", "3nwani",
]

# --------------------------------------------------------------------------
# Stop lists.
# --------------------------------------------------------------------------
# Greeting / politeness phrases (stripped from segment edges; a segment made
# only of these is dropped).
GREETING_PHRASES = [
    "السلام عليكم ورحمة الله وبركاته", "السلام عليكم ورحمة الله", "السلام عليكم", "سلام عليكم",
    "عليكم السلام", "وعليكم السلام", "سلام", "مرحبا", "مرحبه", "مراحب", "هلو", "هلا", "هلاو",
    "اهلا", "أهلين", "اهلين", "هاي", "شلونكم", "شلونك", "شلونج", "صباح الخير", "مساء الخير",
    "صباح النور", "مساء النور", "يعطيكم العافية", "يعطيك العافية", "الله يعطيك العافية",
    "شكرا", "شكراً", "شكرا جزيلا", "مشكورين", "مشكور", "تسلم", "تسلمون", "تسلمين", "الله يخليك",
    "الله يخليكم", "الله يسلمك", "حياكم", "حياك", "عاشت ايدكم", "عاشت ايدك", "ممنون", "رجاءا",
    "رجاء", "لطفا", "من فضلك", "بليز", "اخي", "اخوي", "اختي", "حبيبي", "حبيبتي", "عيني", "عيوني",
    "خالة", "عمو", "استاذ", "ست", "hi", "hello", "hey", "salam", "salaam", "thanks", "thank you",
    "thx", "please", "pls", "plz", "good morning", "good evening", "dear", "bro", "sis",
    "تمام", "اوكي", "اوك", "ok", "okay", "ايه", "اي", "اكيد", "تم",
    "لو سمحت", "لو سمحتي", "لو سمحتو", "لو تسمح", "لو تسمحون", "من فضلكم", "رجاءً",
    "ان شاء الله", "انشاء الله", "انشالله", "ان شاءالله", "إن شاء الله", "ما شاء الله",
    "ماشاء الله", "ماشالله", "الله يحفظك", "الله يحفظكم", "الله يوفقك", "الله يوفقكم",
    "الحمد لله", "الحمدلله", "جزاك الله خير", "جزاكم الله خير", "بارك الله فيك",
    "بارك الله فيكم", "الله يرضى عليك", "الله يرضى عليكم", "في امان الله", "تسلم ايدك",
    "تسلم ايدكم", "يعطيك العافيه", "الله يبارك", "الله يبارك بيكم", "بالتوفيق", "عافية",
    "inshallah", "insha allah", "mashallah", "habibi",
]

# Greeting words that are ALSO common given names (review 1, F22).  They are
# stripped only when they form a whole segment ("هلا" alone, "سلام،"), never
# inside a name run or a labelled name.
AMBIGUOUS_GREETING_NAMES = ["سلام", "هلا", "رجاء", "زين", "نعم", "امل", "عافية", "هاي"]

# Helper words around names/phones: never a name (F25).
HELPER_WORDS = [
    "اخوي", "اخويه", "اختي", "ابوي", "امي", "زوجي", "زوجتي", "مرتي", "رجلي", "ابني", "بنتي",
    "عمي", "خالي", "صديقي", "جاري", "الثاني", "ثاني", "الاول", "رقمه", "رقمها", "رقمهم", "اسمه",
    "اسمها", "الزبون", "الزبونة", "زبون", "زبونة", "المستلم", "المستلمة", "مستلم", "صاحب",
    "صاحبة", "الاستلام", "يستلم", "تستلم", "يستلمه", "يستلمها", "brother", "sister", "wife",
    "husband", "receiver", "recipient", "second", "other",
]
# Phone-introduction words: when one of these is within the 3 words before a
# phone number it is treated as a phone label ("هذا رقم اخوي 0770...",
# "رقم المستلم: 0780...", "تلفون البيت 01...") (F15/F26).
PHONE_INTRO_WORDS = [
    "رقم", "الرقم", "رقمي", "ورقم", "رقمه", "رقمها", "هاتف", "الهاتف", "تلفون", "التلفون",
    "موبايل", "الموبايل", "جوال", "واتساب", "بديل", "البديل", "احتياط", "احتياطي", "ارضي",
    "الارضي", "number", "phone", "mobile", "num", "tel", "whatsapp", "alternative", "alt", "backup",
    "landline",
]
# Words after which the rest of an address segment is chatter, not address
# (payment, timing, requests) (F13/F27).
ADDRESS_CUT_WORDS = [
    # Clear clause starters only (review 2, F40/F41/F49): payment, timing,
    # call requests and thanks.  Ambiguous words that also occur in landmark
    # names (اليوم، رجاء، طلب، before، when، model، لون) are NOT here.  A cut is
    # never made right after a landmark noun or trigger ("مطعم اليوم").
    "الدفع", "دفع", "كاش", "باجر", "بكرة", "بكره", "عقب", "الصبح", "العصر", "بالليل", "المسا",
    "اتصلوا", "اتصلو", "اتصل", "اتصلولي", "رنو", "رنولي", "انشاء", "انشالله", "شكرا", "ضروري",
    "عاجل", "يستلم", "تستلم", "يستلمه", "يستلمها",
    "please", "pls", "call", "payment", "cash", "tomorrow", "asap", "thanks", "urgent",
]
# Weak product words: product only in context (review 2, F41/F48/F49):
#   قطعة/القطعة followed by a number = plot/block number (address);
#   الف only after a number (25 الف = price);
#   لون/اللون only before a colour word (لون اسود), not "لون البيت ابيض";
#   طلب only when not part of a name ("معرض ابو طلب").
WEAK_ORDER_WORDS = ["قطعة", "القطعة", "قطعه", "الف", "لون", "اللون", "طلب", "الطلب"]
COLOUR_WORDS = ["اسود", "سوده", "سودة", "السوداء", "ابيض", "بيضه", "احمر", "حمره", "ازرق", "زرقه",
                "اخضر", "خضره", "اصفر", "رصاصي", "رمادي", "بني", "وردي", "بنفسجي", "ذهبي", "فضي",
                "سمائي", "نيلي", "black", "white", "red", "blue", "green", "grey", "gray", "pink"]
# Phone corrections (review 2, F32): a number after one of these replaces the
# number before it ("الرقم غلط الصحيح 0780...").
CORRECTION_WORDS = ["غلط", "الغلط", "بالغلط", "خطأ", "بالخطأ", "الخطأ", "غلطان", "الصحيح", "صحيح",
                    "الصح", "اقصد", "قصدي", "تصحيح", "sorry", "wrong", "correct", "correction",
                    "mistake", "mean"]
# Markers of a secondary number (review 2, F34): near a phone they rank it
# below a number introduced by رقمي/الرقم/phone.
SECONDARY_PHONE_WORDS = ["ثاني", "الثاني", "البيت", "اخوي", "اختي", "ابوي", "زوجي", "احتياط",
                         "احتياطي", "بديل", "البديل", "اخر", "الاخر", "ارضي", "الارضي", "second",
                         "backup", "alternative", "alt", "other", "home", "brother", "sister"]
PRIMARY_PHONE_WORDS = ["رقمي", "موبايلي", "تلفوني", "هاتفي", "my", "mine"]

# Order / product words (D5): a segment containing one is product talk.
ORDER_WORDS = [
    "اريد", "اريده", "اريدها", "اريدهن", "ابي", "ابيه", "ابيها", "ابغى", "اطلب", "اطلبه", "اطلبها",
    "طلب", "طلبية", "الطلبية", "قياس", "القياس", "مقاس", "المقاس", "لون", "اللون", "سعر", "السعر",
    "سعره", "سعرها", "بكم", "شكد", "حجم", "الحجم", "قطعة", "القطعة", "قطعتين", "حبة", "حبات",
    "كمية", "الكمية", "الف", "دينار", "موديل", "الموديل", "منتج", "المنتج", "طقم", "الطقم",
    "حذاء", "قميص", "فستان", "عباية", "تيشيرت", "بنطرون", "جاكيت", "شنطة", "متوفر", "متوفرة",
    "تخفيض", "خصم", "ستوري", "منشور", "البوست",
    "order", "size", "color", "colour", "price", "qty", "quantity", "pcs", "piece", "pieces",
    "want", "item", "product", "iqd", "dinar", "available",
]

# Delivery cues (D5): "ابعثوه للناصرية" decides between two governorates.
DELIVERY_CUES = [
    "ابعثوه", "ابعثوها", "ابعثولي", "ابعثوا", "ابعثو", "ابعث", "ابعثه", "ارسلوه", "ارسلوها",
    "ارسلولي", "ارسلوا", "ارسل", "وصلوه", "وصلوها", "وصلولي", "وصلوا", "دزوه", "دزوها", "دزولي",
    "دزوا", "دز", "التوصيل", "توصيل", "الشحن", "شحن", "يوصل", "توصله", "توصلوه",
    "send", "deliver", "ship", "delivery", "shipping", "sent",
]
DELIVERY_PREPS = ["على", "الى", "إلى", "ل", "لل", "to", "for", "in"]

# Words that are never part of a name and are trimmed from address edges.
CONNECTORS = [
    "و", "او", "أو", "من", "في", "ب", "ع", "عل", "بس", "هم", "هو", "هي", "انا", "اني", "آني", "احنا",
    "نحن", "ساكن", "ساكنة", "ساكنين", "عدنا", "عدني", "يكون", "يصير", "لو", "مال", "مالتي",
    "and", "or", "from", "in", "at", "live", "living", "i", "the", "my", "is", "to", "for", "im",
    # Arabizi
    "men", "min", "mn", "fi", "fe", "w", "aw", "b", "bel", "sakin", "saken", "sakna", "ani", "ana",
]
# Chatter words: never a name; segments made only of these are dropped.
CHATTER = [
    "ضروري", "عاجل", "بسرعة", "بسرعه", "اليوم", "باجر", "بكرة", "بكره", "هسه", "هسة", "الحين",
    "وين", "متى", "شوكت", "ممكن", "عندكم", "عدكم", "عدكوم", "تكدرون", "تقدرون", "هل",
    "نسيت", "اسف", "عفوا", "هذا", "هاذا", "وهذا", "كتبته", "كتبت", "الصح", "اقصد", "قصدي", "اكدر", "نكدر", "توصلون", "توصلوها", "تبعثون",
    "تبعثوه", "تبعثوها", "ترسلون", "ترسلوه", "تدزون", "تدزوه", "اريد", "كيف", "شلون", "ليش", "شنو", "اشوكت", "منو", "كم", "يوصل", "توصلون",
    "اتصل", "اتصلو", "اتصلوا", "اتصلولي", "اتصال", "راسلني", "راسلوني", "واتساب", "واتس",
    "الى", "مع", "عن", "هذا", "هذه", "هاي", "هذاك", "اللي", "الي", "يعني", "شي", "جاي", "محتاج",
    "حاب", "ودي", "عايز", "راح", "رح", "اوصل", "التوصيل", "توصيل", "مجاني", "الدفع", "دفع",
    "عند", "الاستلام", "استلام", "كاش", "واصل", "صار", "خوش", "حلو", "حلوة", "جدا", "كلش",
    "المندوب", "مندوب", "الدليفري", "دليفري", "الطلب", "طلبي", "نفس", "الرقم", "ثاني", "الثاني",
    "اخر", "احتياط", "احتياطي", "بعدين", "لاحقا", "فقط", "بس", "لا", "ما", "مو", "مب",
    "when", "where", "how", "what", "asap", "today", "tomorrow", "now", "urgent", "cash",
    "delivery", "call", "me", "you", "your", "this", "that", "yes", "no", "not", "new", "number",
    "phone", "mobile", "send", "please", "pls", "but", "also", "just", "here", "there",
]
