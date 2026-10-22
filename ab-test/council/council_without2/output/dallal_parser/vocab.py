"""Vocabulary: field labels, filler words, address keywords.

All entries are written naturally and normalized at import time with the same
``norm`` function applied to message text, so spelling variants such as
ة/ه, أ/ا, ى/ي do not need to be listed twice.
"""

from __future__ import annotations

import re

from .normalize import norm

NAME, SURNAME, PHONE, PHONE_ALT, GOVERNORATE, ADDRESS, LANDMARK, DELIVERY = (
    "name", "surname", "phone", "phone_alt", "governorate", "address", "landmark", "delivery",
)

# Label strength:
#   STRONG    - recognised anywhere in the text ("اسمي علي", "my name is Ali").
#   START     - recognised at the start of a line/segment, or anywhere when
#               followed by a colon ("الاسم علي", "phone: 0770...").
#   COLON     - recognised only when followed by a colon ("city: Basra"); these
#               words are too common to treat as labels otherwise.
#   WEAK_NAME - "انا"/"I'm": start of segment only, and the value must pass the
#               name checks or it is treated as ordinary text.
STRONG, START, COLON, WEAK_NAME = "strong", "start", "colon", "weak_name"

_LABELS: list[tuple[str, str, list[str]]] = [
    (NAME, STRONG, [
        "اسمي", "اسمي هو", "الاسم الكامل", "الاسم الثلاثي", "الاسم الرباعي", "اسم الزبون", "اسم المستلم",
        "اسم الشخص", "اسم المستلمة", "my name is", "my name's", "my name", "full name", "customer name",
        "receiver name", "recipient name", "esmi", "ismi", "asmi", "isme", "esme", "الطلب باسم",
        "الطلب على اسم", "على اسم", "الاستلام باسم", "the order is for", "order is for", "order for",
        "it's for", "receiver", "recipient",
    ]),
    (NAME, START, ["الاسم", "اسم", "الإسم", "name", "esm", "ism", "first name", "الاسم الاول"]),
    (SURNAME, START, ["اللقب", "لقب", "الكنية", "surname", "last name", "family name"]),
    (NAME, WEAK_NAME, ["انا", "اني", "آني", "this is", "i am", "i'm", "im", "ana"]),

    (PHONE_ALT, STRONG, [
        "رقم ثاني", "الرقم الثاني", "رقم اخر", "رقم آخر", "رقم احتياط", "رقم احتياطي", "رقم بديل",
        "رقم البديل", "الرقم البديل", "رقم ثاني للتواصل", "another number", "second number", "alt number",
        "alternative number", "other number", "phone 2", "backup number",
    ]),
    (PHONE, STRONG, [
        "رقمي", "رقمي هو", "رقم هاتفي", "رقم موبايلي", "رقم تلفوني", "رقم الهاتف", "رقم الموبايل",
        "رقم التلفون", "رقم الجوال", "رقم الواتساب", "رقم الواتس", "رقم التواصل", "رقم الزبون",
        "رقم المستلم", "my number is", "my number", "my phone is", "my phone number is", "phone number",
        "mobile number", "raqmi", "ra8mi", "rakmi", "ragmi", "rqmi",
    ]),
    (PHONE, START, [
        "الرقم", "رقم", "الهاتف", "هاتف", "الموبايل", "موبايل", "التلفون", "تلفون", "جوال", "واتساب",
        "الواتساب", "واتس", "phone", "mobile", "number", "tel", "whatsapp", "mob", "num", "contact", "ra8m",
    ]),
    (PHONE, COLON, ["no", "ph"]),

    (GOVERNORATE, STRONG, ["المحافظة", "محافظة", "محافظتي", "governorate", "province"]),
    (GOVERNORATE, START, ["gov"]),
    (GOVERNORATE, COLON, ["city", "المدينة", "مدينة", "المدينه", "town"]),

    (LANDMARK, STRONG, [
        "اقرب نقطة دالة", "أقرب نقطة دالة", "اقرب نقطه داله", "نقطة دالة", "النقطة الدالة",
        "اقرب نقطة", "اقرب معلم", "nearest landmark", "nearest point", "landmark",
    ]),
    # "Deliver to ..." overrides where the customer says they are from.
    (DELIVERY, STRONG, [
        "التوصيل الى", "التوصيل إلى", "التوصيل على", "التوصيل", "توصيل الى", "يوصل الى", "يوصل على",
        "توصلوه الى", "توصلوها الى", "وصلوه الى", "وصلوها الى", "وصلوه", "وصلوها", "ارسلوه الى", "ارسلوها الى",
        "ابعثوه الى", "دزوه الى", "دزوه على", "دزوها", "دزوه", "deliver to", "delivery to", "deliver it to",
        "send it to", "send to", "ship to", "deliver at",
    ]),
    (ADDRESS, STRONG, [
        "عنواني", "عنواني هو", "العنوان الكامل", "العنوان بالتفصيل", "العنوان التفصيلي", "عنوان السكن",
        "عنوان التوصيل", "انا من", "اني من", "آني من", "انا ساكن", "انا ساكنة", "اني ساكن", "اني ساكنة",
        "ساكن", "ساكنة", "ساكنين", "اسكن", "اسكن في", "من سكنة", "سكنة", "اسم المنطقة", "اسم الحي",
        "my address is", "my address", "address is", "delivery address", "i live in", "i live at",
        "i'm from", "i am from", "im from", "living in", "located in", "3nwani", "3inwani",
        "enwani", "sakin", "sakna", "saken", "ana mn", "ana min",
    ]),
    (ADDRESS, START, [
        "العنوان", "عنوان", "address", "addr", "location", "الموقع", "المنطقة", "منطقة", "الحي",
        "area", "district", "neighborhood", "neighbourhood", "3nwan",
    ]),
]


def _label_pattern(phrase: str) -> str:
    key = norm(phrase)
    body = r"\s+".join(re.escape(w) for w in key.split())
    if re.search("[a-z]", key):
        return rf"(?<![a-z0-9']){body}(?![a-z0-9'])"
    # Arabic labels may carry a leading و ("ورقمي", "والعنوان").
    return rf"(?<!\w)(?P<waw>و)?{body}(?!\w)"


LABEL_WORDS = frozenset(
    w for _, _, phrases in _LABELS for p in phrases for w in (norm(p), "و" + norm(p)) if " " not in w
)

LABEL_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(_label_pattern(p)), field, strength)
    for field, strength, phrases in _LABELS
    for p in phrases
]


def _key_set(words: list[str]) -> frozenset[str]:
    return frozenset(norm(w) for w in words)


GREETING_PHRASES = [
    "السلام عليكم ورحمة الله وبركاته", "السلام عليكم ورحمة الله", "السلام عليكم", "سلام عليكم",
    "وعليكم السلام", "صباح الخير", "مساء الخير", "صباح النور", "مساء النور", "الله يخليك", "الله يسلمك",
    "الله يحفظك", "الله يعطيك العافية", "يعطيك العافية", "من فضلك", "لو سمحت", "جزاك الله خير",
    "assalamu alaikum", "assalamualaikum", "salam alaikum", "salamu alaykum", "good morning",
    "good evening", "thank you", "thanks a lot", "thank u",
]
GREETING_PATTERNS = [
    re.compile(rf"(?<!\w){r'\s+'.join(re.escape(w) for w in norm(p).split())}(?!\w)")
    for p in sorted(GREETING_PHRASES, key=len, reverse=True)
]

# Single tokens with no order information; stripped from segment edges.
FILLER = _key_set([
    "مرحبا", "مرحبه", "مرحباً", "هلو", "هلا", "هلاو", "اهلا", "أهلين", "هاي", "شلونك", "شلونكم",
    "شكرا", "شكراً", "مشكور", "مشكورة", "تسلم", "تسلمين", "تسلمون", "ممنون", "رجاءا", "لطفا",
    "انا", "اني", "آني", "تمام", "اوكي", "اوك", "نعم", "اي", "ايي", "اخي", "اختي", "اخوي",
    "حبيبي", "حبيبتي", "عيني", "عيوني", "حجي", "خالة", "عمي", "او", "أو", "هذا", "هذه", "هاي", "هذني",
    "التفاصيل", "تفاصيلي", "معلوماتي", "بياناتي", "المعلومات", "البيانات", "كالتالي", "يلا",
    "hi", "hello", "hey", "salam", "slm", "thanks", "thx", "ty", "pls", "plz", "please", "ok", "okay",
    "yes", "yeah", "here", "are", "my", "details", "detail", "info", "information", "is", "this", "the",
    "bro", "sis", "dear", "or", "and", "sir", "also", "plus", "for", "a", "an", "it", "its", "it's", "of",
    "that", "these", "those", "me", "we", "our", "your", "you", "please", "send", "sent", "again", "number",
    "phone", "name", "address", "location", "done", "sure", "good", "great", "fine", "sorry", "welcome",
    "interested", "looking", "ordering", "ready", "waiting", "available", "new", "customer", "back", "habibi", "shukran", "mrhba", "marhaba", "hala", "hlaw",
])

# Greetings that are also first names ("هلا محمد" may be "Hala Mohammed").
NAME_LIKE_GREETINGS = _key_set(["هلا", "hala", "salam"])

# Words that show a segment is about the product / order, not the customer.
COMMERCE = _key_set([
    "اريد", "اريده", "اريدها", "ابي", "ابغى", "احتاج", "اطلب", "اطلبه", "اطلبها", "طلب", "طلبي",
    "طلبية", "الطلب", "الطلبية", "قطعة", "قطعتين", "قطع", "حبة", "حبتين", "قياس", "مقاس", "القياس",
    "المقاس", "لون", "اللون", "حجم", "الحجم", "عدد", "العدد", "سعر", "السعر", "بكم", "شكد", "شكثر",
    "دينار", "الف", "آلاف", "توصيل", "التوصيل", "اجور", "كود", "الكود", "موديل", "المنتج", "منتج",
    "اوردر", "الاوردر", "جوز", "زوج", "متى", "شنو", "وين", "ليش", "كيف", "هل", "ممكن", "يوصل", "توصلون", "كم",
    # Common product nouns for Iraqi Instagram shops (clothes, cosmetics, accessories, gadgets).
    "فستان", "الفستان", "قميص", "القميص", "تيشيرت", "تيشرت", "بنطرون", "بنطلون", "جينز", "تنورة", "بلوزة",
    "عباية", "العباية", "بدلة", "البدلة", "دشداشة", "جاكيت", "جاكيتة", "قمصلة", "حذاء", "الحذاء", "جزمة",
    "قندرة", "نعال", "شنطة", "الشنطة", "حقيبة", "جنطة", "ساعة", "الساعة", "عطر", "العطر", "مكياج", "روج",
    "سيروم", "نظارة", "نظارات", "اكسسوارات", "قلادة", "حجاب", "شال", "طقم", "الطقم", "بيجامة",
    "سماعة", "سماعات", "شاحن", "كفر", "جراب", "موبايل", "لابتوب", "كرتون", "علبة", "عرض", "العرض", "خصم",
    "dress", "shirt", "tshirt", "t-shirt", "pants", "jeans", "skirt", "abaya", "jacket", "shoes", "bag",
    "watch", "perfume", "makeup", "glasses", "hoodie", "set", "charger", "case", "offer", "discount",
    "want", "order", "buy", "size", "color", "colour", "qty", "quantity", "price", "delivery", "deliver",
    "piece", "pieces", "item", "items", "pcs", "iqd", "dinar", "dinars", "product", "model", "code",
    "when", "how", "much", "can", "could", "would", "need", "like", "x1", "x2", "abi", "areed", "arid",
])

# Order chatter that ends an address ("بغداد الكرادة اريد قطعتين"). Product
# nouns are not here: "مطعم الساعة" is a landmark, not a watch.
ORDER_INTENT = _key_set([
    "اريد", "اريده", "اريدها", "ابي", "ابغى", "احتاج", "اطلب", "اطلبه", "اطلبها", "قياس", "مقاس", "سعر",
    "السعر", "بكم", "شكد", "دينار", "اجور", "want", "order", "size", "price", "qty", "quantity", "iqd",
])

# Prepositions / connectors stripped from the edges of address and name pieces.
EDGE_WORDS = _key_set([
    "في", "فـ", "ب", "الى", "إلى", "لـ", "من", "و", "عند", "in", "at", "to", "from", "of", "on",
])

# Words that end a name ("اسمي علي حسين من بغداد").
NAME_STOP = _key_set([
    "من", "في", "و", "ساكن", "ساكنة", "اسكن", "عنواني", "رقمي", "رقم", "وانا", "واني", "عمري",
    "from", "in", "and", "living", "live", "at", "my", "phone", "number", "address", "near",
]) | FILLER | COMMERCE

# Words that mark a segment as an address even when no known place is named.
ADDRESS_KEYWORDS = [
    "حي", "شارع", "شارغ", "محلة", "محله", "زقاق", "زقاك", "دربونة", "دربونه", "عكد", "دار", "بيت",
    "قرب", "مقابل", "خلف", "جنب", "يم", "بجانب", "قريب", "بالقرب", "منطقة", "ناحية", "قضاء", "قرية",
    "مدينة", "عمارة", "مجمع", "سوق", "جامع", "مسجد", "حسينية", "مستشفى", "مستوصف", "مدرسة", "جامعة",
    "مول", "فلكة", "ساحة", "تقاطع", "سيطرة", "كراج", "جسر", "مفرق", "طابق", "شقة", "بناية", "مقاطعة",
    "فرع", "مركز", "نهاية", "بداية", "ركن", "صيدلية", "فندق", "مطعم", "كازية", "محطة", "بنزينخانة",
    "مخبز", "فرن", "ملعب", "نادي", "كنيسة", "مقام", "مرقد", "حديقة", "متنزه", "معمل", "دائرة", "بلدية",
    "قطاع", "بلوك", "الجانب", "جانب", "صوب", "مقابيل", "شمال", "جنوب", "شرق", "غرب",
    "street", "st", "str", "road", "rd", "avenue", "ave", "district", "near", "opposite", "behind",
    "next to", "beside", "across from", "neighborhood", "neighbourhood", "block", "building", "bldg",
    "apt", "apartment", "floor", "house", "home", "mall", "mosque", "hospital", "school", "university",
    "square", "roundabout", "bridge", "market", "landmark", "village", "mahalla", "mahala", "zuqaq",
    "zqaq", "zgag", "hay", "7ay", "shar3", "shari3", "qurb", "gurb", "grb", "yam", "mqabil", "muqabil",
    "jnb", "jamb", "complex", "compound", "tower", "villa", "sector", "quarter", "junction",
    "checkpoint", "pharmacy", "hotel", "restaurant", "station", "park", "church",
]


def _keyword_pattern(words: list[str]) -> re.Pattern:
    parts = []
    for w in sorted({norm(x) for x in words}, key=len, reverse=True):
        body = r"\s+".join(re.escape(t) for t in w.split())
        if re.search("[a-z0-9]", w):
            parts.append(rf"(?<![a-z0-9]){body}(?![a-z0-9])")
        else:
            parts.append(rf"(?<!\w)(?:[وبل]?ال|لل|[وبل])?{body}(?!\w)")
    return re.compile("|".join(parts))


ADDRESS_KEYWORD_RE = _keyword_pattern(ADDRESS_KEYWORDS)

# Removed from addresses: they add nothing for a domestic courier.
COUNTRY_RE = re.compile(
    r"(?<!\w)(?:[وبفل]?ال|لل)عراق(?!\w)|(?<![a-z])(?:iraq|al[\s\-]?iraq|el[\s\-]?iraq)(?![a-z])"
)
GOV_WORD_RE = re.compile(
    rf"(?<!\w)(?:و?ال|و?)?(?:{norm('محافظة')}|{norm('محافظتي')})(?!\w)|(?<![a-z])(?:governorate|province|gov)(?![a-z])"
)
