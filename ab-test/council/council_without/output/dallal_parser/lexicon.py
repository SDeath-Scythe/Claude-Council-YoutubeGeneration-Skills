"""Word lists: field labels, greetings, fillers, address words, first names.

All lists are written in natural spelling; they are normalised when the
matchers are built, so spelling variants (أ/ا, ة/ه, ى/ي) need not be repeated.
"""

from __future__ import annotations

from .matcher import PhraseMatcher, key_set

# ---------------------------------------------------------------------------
# Field labels. (phrase, field, strong)
# A *strong* label also splits a line in the middle, so single-line forms like
# "الاسم احمد المحافظة بغداد العنوان الكرادة" work. Weak labels only count at
# the start of a segment, or anywhere when followed by ":".
# ---------------------------------------------------------------------------
LABELS: list[tuple[str, str, bool]] = [
    # name
    ("الاسم الكامل", "name", True), ("الاسم الثلاثي", "name", True),
    ("الاسم الرباعي", "name", True), ("اسم الزبون", "name", True),
    ("اسم المستلم", "name", True), ("اسم الزبونة", "name", True), ("المستلم", "name", True),
    ("اسم صاحب الطلب", "name", True), ("الاسم صاحب الطلب", "name", True),
    ("ismi", "name", False), ("esmi", "name", False), ("isme", "name", False),  # Arabizi
    ("recipient", "name", False), ("receiver", "name", False),
    ("الاسم", "name", True), ("اسمي", "name", True), ("اسم", "name", False),
    ("ناو", "name", False), ("ناوم", "name", False),  # Kurdish
    ("full name", "name", False), ("customer name", "name", False),
    ("my name is", "name", True), ("my name", "name", False), ("name is", "name", False),
    ("name", "name", False),
    # phone
    ("رقم الهاتف", "phone", True), ("رقم الموبايل", "phone", True),
    ("رقم التلفون", "phone", True), ("رقم الجوال", "phone", True),
    ("رقم الواتساب", "phone", True), ("رقم الواتس", "phone", True),
    ("رقم ثاني", "phone", True), ("رقم اخر", "phone", True), ("رقم احتياط", "phone", True),
    ("رقم احتياطي", "phone", True), ("رقم بديل", "phone", True),
    ("الرقم", "phone", False), ("رقم", "phone", False), ("رقمي", "phone", False),
    ("هاتف", "phone", False), ("الهاتف", "phone", False), ("موبايل", "phone", False),
    ("الموبايل", "phone", False), ("تلفون", "phone", False), ("تلفوني", "phone", False),
    ("جوال", "phone", False), ("واتساب", "phone", False), ("واتس", "phone", False),
    ("ژمارە", "phone", False), ("ژمارەی مۆبایل", "phone", False),  # Kurdish
    ("phone number", "phone", False), ("phone", "phone", False), ("mobile", "phone", False),
    ("mobile number", "phone", False), ("number", "phone", False), ("tel", "phone", False),
    ("whatsapp", "phone", False), ("mob", "phone", False), ("cell", "phone", False),
    ("ra8mi", "phone", False), ("raqmi", "phone", False), ("rqmi", "phone", False),
    # governorate
    ("المحافظة", "governorate", True), ("محافظة", "governorate", False),
    ("المدينة", "governorate", False), ("مدينة", "governorate", False),
    ("پارێزگا", "governorate", False), ("شار", "governorate", False),  # Kurdish
    ("governorate", "governorate", False), ("province", "governorate", False),
    ("city", "governorate", False), ("state", "governorate", False),
    # address
    ("العنوان الكامل", "address", True), ("عنوان السكن", "address", True),
    ("العنوان", "address", True), ("عنواني", "address", True), ("عنوان", "address", False),
    ("المنطقة", "address", False), ("منطقة السكن", "address", True),
    ("القضاء", "address", False), ("الناحية", "address", False), ("district", "address", False),
    ("ناونیشان", "address", False), ("گەڕەک", "address", False),  # Kurdish
    ("full address", "address", False), ("address", "address", False),
    ("area", "address", False), ("location", "address", False),
    # landmark ("أقرب نقطة دالة" is how Iraqi couriers ask for a landmark)
    ("اقرب نقطة دالة", "landmark", True), ("اقرب نقطه داله", "landmark", True),
    ("نقطة دالة", "landmark", True), ("نقطه داله", "landmark", True), ("دالة", "landmark", False),
    ("nearest landmark", "landmark", False), ("closest landmark", "landmark", False),
    ("landmark", "landmark", False), ("nearest point", "landmark", False),
    # free-text notes the shop should see but that is not the address
    ("ملاحظة", "notes", True), ("ملاحظات", "notes", True), ("ملاحظه", "notes", True),
    ("الطلب", "notes", False), ("المنتج", "notes", False), ("القياس", "notes", False),
    ("اللون", "notes", False), ("note", "notes", False), ("notes", "notes", False),
    ("order", "notes", False), ("product", "notes", False), ("size", "notes", False),
    ("color", "notes", False), ("colour", "notes", False),
]

LABEL_MATCHER = PhraseMatcher((phrase, (field, strong)) for phrase, field, strong in LABELS)

# Phone-label words that are left dangling once the number itself is cut out:
# "احمد علي رقمي 0770..." -> "احمد علي رقمي" -> strip "رقمي".
PHONE_WORDS = key_set([
    "رقم", "رقمي", "الرقم", "هاتف", "هاتفي", "موبايل", "موبايلي", "تلفون", "تلفوني", "جوال",
    "جوالي", "واتساب", "واتس", "الهاتف", "الموبايل", "اتصال", "اتصل",
    "phone", "number", "mobile", "tel", "whatsapp", "mob", "cell", "no", "call", "on",
])

# ---------------------------------------------------------------------------
# Greetings and politeness, removed wherever they appear.
# ---------------------------------------------------------------------------
GREETINGS = [
    "السلام عليكم ورحمة الله وبركاته", "السلام عليكم ورحمة الله", "السلام عليكم",
    "سلام عليكم", "وعليكم السلام", "مرحبا", "مرحبه", "مرحباً", "هلو", "هلاو", "اهلا",
    "اهلين", "هاي", "صباح الخير", "مساء الخير", "صباح النور", "مساء النور", "شلونكم",
    "شلونك", "شكرا", "شكراً", "مشكورين", "مشكور", "مشكورة", "تسلم", "تسلمون", "تسلمين",
    "لو سمحت", "لو سمحتو", "رجاء", "رجاءا", "الله يخليك", "الله يخليكم", "يعطيكم العافية",
    "يعطيك العافية", "الله يحفظكم", "عيوني", "حبيبي", "حبيبتي", "اخي", "اختي",
    "سڵاو", "سوپاس",  # Kurdish: hello, thanks
    "hi", "hello", "hey", "salam alaikum", "salam alaykum", "assalamu alaikum",
    "asalamu alaikum", "good morning", "good evening", "thanks", "thank you", "thx",
    "please", "pls", "plz", "dear", "salam 3likum", "salam alekum", "mar7aba", "marhaba",
    "ان شاء الله", "انشاء الله", "انشالله", "اوكي", "حبي", "شكرا لكم", "شكرا الكم", "بليز",
    # order preambles: "طلب جديد: ..." / "معلوماتي: ..."
    "طلب جديد", "تفاصيل الطلب", "معلومات الطلب", "بيانات الطلب", "معلومات التوصيل",
    "بيانات التوصيل", "معلوماتي", "المعلومات", "new order", "order details", "my details",
    "delivery details", "my info",
]
GREETING_MATCHER = PhraseMatcher((g, "greeting") for g in GREETINGS)

# Removed only when they are a whole segment by themselves at the start or end
# of the message: they are also common given names (سلام, هلا).
WEAK_GREETINGS = key_set(["سلام", "هلا", "salam", "ok", "okay", "اوكي", "تمام", "هلا والله"])

# Function words that never occur inside a person's name. A token sequence
# containing one of them ("i live", "ساكن هنا") is not a name. (Never add
# على here: it normalises to the same key as the name علي.)
NON_NAME_WORDS = key_set([
    "من", "في", "الى", "هنا", "هسه", "حاليا", "ساكن", "ساكنه", "اسكن", "نسكن", "بس", "و", "او",
    "هذا", "هذه", "هاي", "عدنا", "عندي", "يرجى", "ارجو", "ممكن", "اكو", "ماكو", "لا", "نعم",
    "i", "we", "my", "our", "the", "is", "am", "are", "live", "living", "to", "in", "from",
    "at", "and", "or", "for", "of", "with", "this", "that", "it", "you", "your", "me", "here",
    "want", "need", "would", "like", "can", "could", "yes", "no", "not", "and", "but", "so", "ok",
    "im", "send", "هو", "هي", "هذا", "اسمه", "اسمها", "لان", "لأن", "ساكنين", "ساكنة", "انطيك",
    "هاي", "اذا", "اخوي", "اختي", "زوجي", "زوجتي", "ابوي", "امي", "مال", "مالي", "الي", "اللي",
    "ana", "ani", "mn", "men", "w",
])

# Honorifics in front of a name ("الست هدى", "حجي ابو مصطفى"): kept in the
# output, ignored when judging whether a line looks like a name.
HONORIFICS = key_set([
    "ست", "الست", "حجي", "حجية", "الحجي", "الحجية", "سيد", "السيد", "السيدة", "سيدة", "شيخ", "الشيخ",
    "دكتور", "دكتورة", "د", "استاذ", "استاذة", "ملا", "كاك", "كاكه", "خاتو",
    "mr", "mrs", "ms", "miss", "dr", "haji", "hajji", "sayed", "sayyid", "sheikh", "kak",
])

# Words before a place that mark it as where the customer lives / wants
# delivery, or as somewhere else (origin, work). Used to pick between two
# governorates mentioned in one message (the order is still flagged).
RESIDENCE_WORDS = key_set([
    "ساكن", "ساكنه", "ساكنة", "ساكنين", "اسكن", "نسكن", "عنواني", "التوصيل", "توصيل", "للتوصيل",
    "هسه", "حاليا", "live", "living", "deliver", "delivery", "send", "currently", "now",
])
ORIGIN_WORDS = key_set(["من", "اصلي", "اصلا", "اشتغل", "دوامي", "from", "originally", "work"])

# Self-introduction / filler words stripped from the *start* of a segment.
INTRO_FILLERS = [
    "انا اسمي", "اني اسمي", "انا", "اني", "احنا", "i am", "i'm", "im", "this is", "it's", "its",
]
INTRO_MATCHER = PhraseMatcher((p, "intro") for p in INTRO_FILLERS)

ADDRESS_FILLERS = [
    "ساكن في", "ساكنة في", "ساكنه في", "ساكن ب", "ساكن", "ساكنة", "ساكنه", "اسكن في", "اسكن",
    "نسكن", "من", "في", "بي", "التوصيل الى", "التوصيل ل", "توصيل الى", "الى",
    "i live in", "live in", "we live in", "from", "in", "at", "deliver to", "to",
    "ساكنين في", "ساكنين", "mn", "men", "fi",
]
ADDRESS_FILLER_MATCHER = PhraseMatcher((p, "filler") for p in ADDRESS_FILLERS)

# "محافظة" / "governorate" next to a governorate name that has been removed.
GOV_WORDS = key_set(["محافظة", "محافظه", "governorate", "province", "پارێزگای", "پارێزگا"])

# ---------------------------------------------------------------------------
# Address vocabulary: a segment containing any of these is an address, and a
# token sequence containing them is never a person's name.
# ---------------------------------------------------------------------------
ADDRESS_WORDS = key_set([
    "حي", "محلة", "محله", "منطقة", "شارع", "زقاق", "زقاق", "عكد", "دربونة", "درب", "دار",
    "بيت", "بناية", "بنايه", "عمارة", "طابق", "شقة", "مجمع", "قرب", "مقابل", "خلف", "جنب",
    "يم", "بجانب", "قريب", "صوب", "ساحة", "سوق", "جامع", "مسجد", "حسينية", "مدرسة",
    "مستشفى", "مستوصف", "مول", "فلكة", "تقاطع", "جسر", "كراج", "مركز", "قضاء", "ناحية",
    "قرية", "مقاطعة", "نقطة", "دالة", "بالقرب", "محطة", "مطعم", "صيدلية", "اسواق", "مفرق",
    "سيطرة", "دائرة", "كلية", "جامعة", "ملعب", "حديقة", "مدينة", "فندق", "معرض", "كنيسة",
    "مرقد", "ضريح", "مقام", "مول", "بلوك", "قطاع", "جادة", "طريق", "فرع",
    "گەڕەک", "گەڕەکی", "شەقام", "شەقامی", "نزیک", "نزیکی", "بەرامبەر", "تەنیشت",  # Kurdish
    "street", "st", "road", "rd", "district", "area", "near", "opposite", "behind", "next",
    "beside", "block", "building", "apartment", "apt", "floor", "house", "home", "mosque",
    "school", "hospital", "mall", "market", "square", "bridge", "intersection", "village",
    "neighborhood", "neighbourhood", "hay", "mahalla", "zuqaq", "alley", "compound",
    "complex", "sector", "landmark", "garage", "station", "church", "shrine", "park",
    "restaurant", "pharmacy", "university", "college", "behind", "across", "avenue",
])

# Words that introduce a landmark ("near X"). The landmark field is taken from
# the marker to the end of its segment.
LANDMARK_MARKERS = key_set([
    "قرب", "مقابل", "خلف", "جنب", "يم", "بجانب", "قريب", "بالقرب", "جوار", "بجوار", "مجاور",
    "وراء", "ورا", "امام", "نزیک", "نزیکی", "بەرامبەر", "تەنیشت",
    "near", "opposite", "behind", "beside", "next", "across", "nearby", "facing",
])

# Order / delivery chatter that belongs in ``notes``, not in the address.
NOTE_WORDS = key_set([
    "اريد", "اريد", "ابي", "ابغي", "اطلب", "طلب", "طلبي", "قياس", "لون", "حجم", "عدد", "قطعة",
    "قطع", "سايز", "موديل", "كمية", "توصيل", "وقت", "ساعة", "باجر", "بكرة", "بكره", "عصر",
    "العصر", "الصبح", "صباحا", "مساءا", "الظهر", "اتصلو", "اتصلوا", "دوام", "سعر", "السعر",
    "دينار", "الف", "واحد", "اثنين", "ثنين", "حبة", "حبتين", "وحدة", "وحده", "احجز", "احجزلي",
    "حجز", "احجزولي", "ارسل", "ارسلولي", "دزولي", "دزلي", "ابيها", "اريدها", "اريده", "ابيه",
    "ستوري", "الستوري", "بوست", "منشور", "هدية", "تتاخرون", "تتأخرون", "تأخير", "توصل", "قبل",
    "عاطل", "مسد", "story", "post", "gift", "late",
    "want", "order", "size", "color", "colour", "qty", "quantity", "piece", "pieces", "pcs",
    "delivery", "deliver", "time", "tomorrow", "pm", "am", "model", "price", "iqd", "dinar",
    "call", "before", "after", "morning", "evening",
])

# ---------------------------------------------------------------------------
# Common first names (Iraqi Arabic, Kurdish, and their usual Latin spellings),
# plus kunya starters (ابو علي / ام حسين are how many Iraqis are addressed).
# A hit is strong evidence that a segment is the customer's name.
# ---------------------------------------------------------------------------
FIRST_NAMES = key_set("""
محمد احمد علي حسين حسن عباس مصطفى عمر عمار يوسف ابراهيم كرار حيدر سجاد مرتضى منتظر مهدي جعفر
كاظم جاسم قاسم سعد سعيد صادق باقر رضا عبدالله عبد زيد زياد ياسر ياسين طه ليث وسام وليد خالد
سيف سلام حمزة امير امين بلال بشير جواد جلال حامد حارث حازم حسام حكيم رائد رعد رافد رياض زهير
سامر سامي ستار شاكر صباح صلاح ضياء طارق عادل عدنان عزيز عقيل علاء عماد فاضل فراس فلاح فيصل
قيس كريم ماجد مازن محسن محمود مراد مشتاق مقتدى منير مهند موسى ميثم نبيل نزار نصير نوري هادي
هاشم هيثم وائل وسيم ياس يحيى اياد ايهاب بسام تحسين ثامر جبار جمال حميد خضير رسول سالم سليم
شهاب صفاء عبود غسان فؤاد كمال لؤي مالك مثنى مجيد مؤمل نجم نعمان هشام همام زين اسامة انس
ايمن بكر حمودي حمادة سرمد سنان عثمان عون غيث فارس قصي كرم لؤي مجتبى مرتضي منذر
ناصر نجاح هاني هلال يونس امجد اكرم ازهر اسعد باسم بهاء جميل حسنين حمد خليل ذوالفقار
رامي رحيم زكي سالم سعدون شوكت صالح ضرغام طلال عامر عدي علوان عمران غانم فهد كامل
مصعب معتز مقداد منصور مهيمن نادر نشوان هيمن ولید
زينب فاطمة مريم نور سارة زهراء رقية هدى اسراء اية اسيل ايات بنين تبارك حوراء دعاء رسل رنا ريم
زهرة سجى سرى شهد شيماء صفا ضحى طيبة عذراء علياء غدير فرح لمى لينا مروة منى ميس نبأ نرجس هبة
هالة هند ولاء ياسمين اسماء امل ايمان بتول جنان حنان خديجة دنيا رحاب زينة سعاد سهى سلمى شذى
عبير غادة كوثر ليلى مها نادية نجلاء نهى هيفاء وفاء ابتهال اخلاص امنة رباب سناء انوار هلا
بان تقى حلا دانية رغد رهف زهور سلوى سماح شمس صبا عائشة عفراء غفران فاطمه لبنى مآب ملاك
منار ميساء نبراس نغم هديل وجدان ياسمينة
دلشاد شيرزاد هيوا ريبوار سركوت كاوه ازاد اراس اسو شيلان ديلان روژان هاوري بختيار دلير
كوران ئاراس ئازاد شنو ئاسو بيخال روناك ئەڤین ئاوات نەوزاد ژیلە
ابو ام
ahmed ahmad mohammed muhammad mohammad mohamed mohamad muhamad ali hussein husain hussain
hassan hasan abbas mustafa mustafa omar ammar yousif yousef yusuf youssef ibrahim karrar haider
hayder sajjad murtadha murtada muntadhar muntather mahdi mehdi jaafar jafar kadhim kazim jassim
jasim qasim saad saeed said sadiq baqir ridha reza abdullah abdulla abdul zaid zayd ziad ziyad
yasir yaser yasser yassin yaseen taha laith layth leith wisam waleed walid khalid khaled saif sayf
salam hamza hamzah ameer amir bilal jawad hamid harith hazim husam hussam hakim raed rafid riyadh
zuhair samer sami sattar tariq tarik adel adil adnan aziz aqeel aqil alaa imad emad firas falah
faisal qais qays karim kareem majid mazin mahmoud mahmud murad mushtaq muqtada munir muhanad
mohanad mohannad musa mousa maitham maytham nabil nizar nouri noori hadi hashim haitham haytham
wael wasim yahya ayad iyad ihab tahseen thamer jabbar jamal hameed rasool rasul salim saleem
shihab ghassan kamal luay malik muthanna najm noman hisham zain zein osama usama anas ayman bakr
sarmad sinan othman uthman ghaith faris fares qusay mujtaba munther nasser naser hani younis
yunus amjad akram azhar asaad basim baha jamil hasanain hassanein khalil rami raheem salih saleh
taha talal amer uday adi mosab moataz miqdad mansour mansoor nader dilshad shirzad hiwa rebwar
sarkawt kawa azad aras aso shilan dilan rozhan bakhtiyar dler goran awat
zainab zaynab zaineb fatima fatimah fatma maryam mariam mariem noor nour nur sara sarah zahraa
zahra ruqaya ruqayya ruqaia huda israa esraa aya aseel ayat banin baneen tabarak hawraa hawra
duaa doaa rusul rasul rana reem rim zahra saja sura shahad shaimaa safa duha tayba athraa alyaa
ghadeer ghadir farah lama lina marwa marwah muna mona mais mays naba narjis hiba heba hala hind
walaa yasmin yasmeen yasmine asmaa amal iman eman batool batoul jinan hanan khadija khadijah dunya
donya rehab zina zeina suad suha salma shatha abeer ghada kawthar kawther layla laila leila maha
nadia najlaa noha nuha haifa wafaa amna aamina rabab sanaa anwar ban tuqa hala rahaf raghad zahoor
salwa samah shams saba aisha aysha ghufran lubna malak manar maysaa nibras nagham hadeel wijdan
roza runak shno awin
abu umm um
""".split())
