"""Word lists: labels, greetings, order chatter, address keywords.

Pure data, written in natural spelling; folded at import (see
``normalize.fold``).  Multi-word entries are matched as whole phrases.
"""

# --- field labels -----------------------------------------------------------
# Order matters only for readability; the matcher always prefers the longest.

LABELS = {
    "name": [
        "الاسم الثلاثي", "الاسم الكامل", "الاسم الرباعي", "الاسم الثنائي", "اسم الزبون", "اسم المستلم",
        "اسم الزبونة", "اسمي", "اسمى", "اسمها", "اسمه", "الاسم", "اسم", "name", "full name", "customer name",
        "ناو", "ناوی", "ناوم", "ناوەکەم", "nawm", "nawim", "naw",
        "انا اسمي", "اني اسمي", "my name is", "my name's", "my name", "name is", "esmi", "ismi", "ana esmi",
    ],
    "phone": [
        "رقم الهاتف", "رقم الموبايل", "رقم التلفون", "رقم التليفون", "رقم الجوال", "رقم الموبايل الاساسي",
        "الرقم", "رقم", "رقمي", "رقمها", "رقمه", "الهاتف", "هاتف", "الموبايل", "موبايل", "تلفون", "تليفون", "الجوال",
        "phone", "phone number", "number", "mobile", "mobile number", "mob", "tel", "no", "num",
        "raqmi", "raqm", "rqm", "rakmi", "ra8mi", "ra8m", "raqam", "el raqam", "al raqam",
        "ژمارە", "ژمارەی مۆبایل", "مۆبایل",
    ],
    "phone2": [
        "رقم ثاني", "رقم الثاني", "الرقم الثاني", "رقم احتياط", "رقم احتياطي", "الرقم الاحتياطي",
        "رقم بديل", "رقم اخر", "او", "أو", "واتساب", "whatsapp", "second number", "another number",
        "or", "واذا مغلق", "اذا مغلق", "واذا مسدود",
        # someone else's number: 'رقم ابني', 'رقم اخوي'
        "رقم ابني", "رقم ابنتي", "رقم اخوي", "رقم اخي", "رقم اختي", "رقم زوجي", "رقم زوجتي", "رقم ابوي",
        "رقم امي", "رقم بنتي", "رقم صديقي", "my son", "my brother", "my husband", "my wife",
    ],
    # 'I am ...' - weak: the value is only a name *candidate* ('اني مستعجل' is
    # "I'm in a hurry"), never an authoritative label
    "intro": ["انا", "اني", "آني", "ana", "ani", "im", "i'm", "i am", "this is"],
    "governorate": ["المحافظة", "محافظة", "governorate", "province", "پارێزگا"],
    # 'city' words bind only with an explicit ':' ('مدينة العامرية' is a place)
    "city": ["المدينة", "city", "gov", "شار"],
    "governorate_area": [
        "المحافظة والمنطقة", "المحافظة و المنطقة", "المنطقة والمحافظة", "المحافظة والعنوان",
        "المحافظة و العنوان", "المدينة والمنطقة", "city and area", "city & area",
    ],
    "area": ["المنطقة", "منطقة", "المحلة", "القضاء", "الناحية", "area", "district", "region"],
    "address": [
        "العنوان", "عنوان", "عنواني", "العنوان الكامل", "السكن", "مكان السكن", "address", "location",
        "addr", "ناونیشان",
    ],
    "landmark": [
        "اقرب نقطة دالة", "أقرب نقطة دالة", "اقرب نقطه داله", "نقطة دالة", "اقرب نقطة", "اقرب معلم",
        "اقرب شي", "اقرب مكان", "landmark", "nearest point", "nearest landmark", "near point",
    ],
}

# Labels whose value may follow after a plain space (no ':' or '-').  For the
# rest a space-separated "label" is just ordinary text (e.g. 'منطقة الجزائر'
# is kept whole as address text).
SPACE_OK_LABELS = {"name", "intro", "city", "phone", "phone2", "governorate", "governorate_area", "address", "landmark"}

# Words that mark the number after them as a correction ('الرقم الصحيح ...').
PHONE_CORRECTION = ["الصحيح", "الصح", "صحيح", "الجديد", "correct", "corrected", "right", "new"]

# --- noise ----------------------------------------------------------------
# Stripped at the start/end of a segment (repeatedly).
EDGE_NOISE = [
    "السلام عليكم ورحمة الله وبركاته", "السلام عليكم ورحمة الله", "السلام عليكم", "سلام عليكم",
    "وعليكم السلام", "مرحبا", "مرحبه", "مرحباً", "هلو", "هلاو", "اهلا", "أهلا", "اهلين", "هلا والله",
    "حياك", "حياكم", "حياك الله", "صباح الخير", "صباح النور", "مساء الخير", "مساء النور", "شلونك",
    "شلونكم", "شكرا", "شكراً", "شكرا جزيلا", "مشكورين", "مشكور", "مشكورة", "تسلم", "تسلمين", "تسلمون",
    "الله يخليك", "الله يخليكم", "الله يسلمك", "الله يعافيك", "يعطيك العافية", "يعطيكم العافية",
    "عاشت ايدك", "عاشت ايدكم", "لو سمحت", "لو سمحتي", "رجاءا", "رجاء", "من فضلك", "حبيبي", "حبيبتي",
    "عيوني", "عيني", "اخي", "اختي", "اخوية", "هاي معلوماتي", "هذه معلوماتي", "هذي معلوماتي",
    "معلوماتي", "المعلومات", "البيانات", "تفضل", "تفضلي", "hi", "hello", "hey", "slm",
    "عليكم السلام", "عليكم السلام ورحمة الله", "جزاك الله خير", "جزاك الله خيرا", "الحمد لله", "الحمدلله",
    "فدوه الك", "فدوة الك", "فدوه", "فدوة", "ممنون", "سباس", "inshallah", "insha allah", "bal3afya",
    "ان شاء الله", "انشاء الله", "انشالله", "ان شاء الله تعالى", "مو مشكلة", "الله يحفظك", "الله يحفظكم",
    "بالله", "يا الله", "تمام اخي", "salam alaikum", "salam alykum", "salam 3likum", "slm 3likum", "3likm", "3leekum", "alaikum",
    "marhaba", "shukran", "thanks", "thank you", "thx", "plz", "please", "dear", "bro", "habibi",
    # Kurdish
    "سلاو", "سڵاو", "چۆنی", "سوپاس", "زۆر سوپاس", "slaw", "silaw", "chony", "choni", "supas", "spas",
]

# Greetings that are also given names (Hala, Zain, Salam ...): stripped only
# when the segment is just the word, or the next token is punctuation/emoji
# or a courtesy word ('هلا اخي', 'سلام عليكم') - never before a name.
NAME_LIKE_GREETINGS = ["هلا", "زين", "سلام", "رجاء", "تمام", "نعم", "salam", "hala", "zain"]
COURTESY_TAILS = [
    "اخي", "اختي", "حبيبي", "حبيبتي", "عيوني", "عيني", "بيك", "بيكم", "عليكم", "والله", "شلونك",
    "شلونكم", "حجي", "خالة", "خالو", "عمو", "اخوية", "3likum", "alaikum", "bro", "habibi",
]

# Words left at the end of a name after a single-line split ('انا علي من بغداد').
NAME_TRAILERS = ["من", "في", "ب", "ساكن", "ساكنة", "اسكن", "سكنة", "from", "in", "at", "lives", "mn", "min", "b"]
# Only noise when they are the whole segment (they are also names: هلا, زين,
# سلام, or ordinary words that could start a real line).
WHOLE_NOISE = [
    "هلا", "سلام", "تمام", "اوك", "اوكي", "زين", "ماشي", "نعم", "اي", "ايي", "اي نعم", "حاضر",
    "ممكن", "ok", "okay", "yes", "yep", "done", "تم", "هاي", "هذا", "هذا هو", "طيب",
]

# Words that make a segment order chatter (goes to notes).
PRODUCT_WORDS = [
    "اريد", "أريد", "اريده", "اريدها", "ابي", "ابغى", "اطلب", "اطلبه", "احتاج", "اشتري", "قياس",
    "القياس", "مقاس", "المقاس", "لون", "اللون", "عدد", "العدد", "قطعة", "قطعتين", "القطعة", "حبة",
    "حبتين", "سعر", "السعر", "بكم", "شكد", "شگد", "الف", "دينار", "د.ع", "iqd", "size", "color",
    "colour", "qty", "quantity", "price", "order", "طلب", "الطلب", "طلبية", "طلبيتي", "موديل",
    "التوصيل", "توصيل", "ديليفري", "delivery", "xl", "xxl", "xxxl",
    # payment, timing, redirects, questions
    "الدفع", "الاستلام", "الكاش", "كاش", "الساعة", "ساعة", "اتصل", "اتصلوا", "اتصلو", "سؤال", "السابق",
    "ابعثوه", "ابعثوها", "ابعثولي", "لبيت", "اهلي", "هدية", "ضروري", "بسرعة", "call", "cash", "payment",
    "hour", "gift", "urgent",
    "متى", "شوكت", "يوصل", "توصل", "يوصلني", "توصلون", "متوفر", "متوفرة", "موجود", "how much", "cost",
]

# Words that never appear in a customer's name: delivery instructions ('send
# to my sister', 'دزوه لاختي') and chatter ('باجر', 'متى يوصل').  A line with
# them is not a name candidate, so the bot asks instead of confirming it.
NOT_NAME_WORDS = [
    "دزوه", "دزوها", "دزولي", "دزلي", "دزوا", "ارسلوه", "ارسلوها", "وصلوه", "وصلوها", "لاختي", "لاخوي",
    "لاخي", "لامي", "لابوي", "لزوجتي", "لزوجي", "لصديقي", "لصديقتي", "باسم", "send", "deliver", "ship",
    "to", "for", "my", "sister", "brother", "mother", "mom", "wife", "husband", "friend", "please",
    "نفس", "اللي", "الي", "بالصورة", "صار", "طلبي", "الطلب", "شاء", "انشاء", "مستعجل", "مستعجلة",
    "busy", "same", "picture", "photo", "اسود", "احمر", "ابيض", "ازرق", "اخضر", "لونين", "خصم", "انطيني",
    "احجزلي", "حجزلي", "وينكم", "بيش", "بغيت", "وصلني", "خوش", "عليك", "باجر", "بكرة", "اليوم", "هسه", "هسة", "بعدين", "الصبح", "العصر", "المساء", "tomorrow", "today",
    "متى", "شوكت", "يوصل", "توصل", "يوصلني", "توصلون", "يجي", "وين", "ليش", "شنو", "هل", "when", "how",
]

# Order words that, next to a place, introduce a delivery address.
DELIVERY_WORDS = ["توصيل", "التوصيل", "ابعثوه", "ابعثوها", "دزوه", "دزوها", "يوصل", "لبيت", "delivery", "deliver"]

# Words that make a segment location text.
ADDRESS_KEYWORDS = [
    "قرب", "قريب", "مقابل", "خلف", "جنب", "يم", "بجانب", "جانب", "شارع", "الشارع", "حي", "محلة",
    "محله", "زقاق", "زقاك", "دار", "الدار", "منطقة", "منطقه", "مجمع", "ساحة", "عمارة", "طابق", "شقة",
    "قضاء", "ناحية", "قرية", "سوق", "جامع", "مسجد", "مستشفى", "مدرسة", "فلكة", "تقاطع", "سيطرة",
    "كراج", "مول", "بناية", "نزال", "near", "street", "st", "road", "rd", "mall", "district",
    "apartment", "building", "floor", "opposite", "behind", "beside", "next", "block", "alley",
    "neighborhood", "neighbourhood", "village", "town", "city",
    # Arabizi
    "7ay", "7ai", "hay", "mahalla", "mahala", "m7la", "shari3", "share3", "sharee3", "qurb", "9urb", "grb",
    "jamb", "zuqaq", "zgag", "mantaqa", "mantiqa",
    # Kurdish
    "شەقام", "شەقامی", "گەڕەک", "گەڕەکی", "نزیک", "بەرامبەر", "تەنیشت", "کۆڵان",
]

# Markers that start the landmark part of an address.
LANDMARK_MARKERS = [
    "قرب", "قريب من", "قريب", "مقابل", "خلف", "جنب", "يم", "بجانب", "جانب", "near", "opposite",
    "behind", "next to", "beside", "close to", "نزیک",
]

# Name particles that glue to the next token (count as one token).
NAME_GLUE = ["عبد", "ابو", "أبو", "ام", "أم", "بن", "بنت", "آل"]
