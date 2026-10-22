import random
import unittest

from dallal_parser import parse_order

KEYS = {"name", "phone", "alt_phones", "governorate", "governorate_ar", "address", "notes", "missing",
        "warnings", "needs_review"}


def codes(result):
    return [w["code"] for w in result["warnings"]]


# (message, expected name, phone, governorate, address). These are complete,
# clean orders: they must parse exactly and must NOT be flagged for review.
CLEAN_ORDERS = [
    # Unlabelled lines, the most common DM shape.
    ("علي حسين\n07701234567\nبغداد\nالكرادة قرب جامع براثا",
     "علي حسين", "+9647701234567", "Baghdad", "الكرادة قرب جامع براثا"),
    # Order template filled in by the customer, Arabic-Indic digits.
    ("الاسم: محمد عبد الله\nرقم الهاتف: ٠٧٨١ ٢٣٤ ٥٦٧٨\nالمحافظة: البصرة\nالعنوان: الزبير، قرب المستشفى العام",
     "محمد عبد الله", "+9647812345678", "Basra", "الزبير، قرب المستشفى العام"),
    # One running sentence with inline markers.
    ("السلام عليكم اسمي زهراء كاظم ورقمي 07501234567 وانا من النجف حي الأنصار قرب مدرسة الغدير",
     "زهراء كاظم", "+9647501234567", "Najaf", "حي الأنصار قرب مدرسة الغدير"),
    # English template.
    ("Name: Ali Hussein\nPhone: +964 770 123 4567\nCity: Erbil\nAddress: Ankawa, near Family Mall",
     "Ali Hussein", "+9647701234567", "Erbil", "Ankawa, near Family Mall"),
    # Arabizi.
    ("esmi ahmed jasim, ra8mi 07901234567, sakin baghdad al mansour qurb jame3 al rahman",
     "Ahmed Jasim", "+9647901234567", "Baghdad", "al mansour qurb jame3 al rahman"),
    # Template with values on the next line.
    ("الاسم:\nسجاد محمد\nالعنوان:\nذي قار الناصرية شارع الحبوبي\nالرقم:\n07734567890",
     "سجاد محمد", "+9647734567890", "Dhi Qar", "الناصرية شارع الحبوبي"),
    # Emoji bullets, dash separators.
    ("📍 كربلاء - حي العباس شارع ٢٠\n📞 07809876543\n👤 ام حسين",
     "ام حسين", "+9647809876543", "Karbala", "حي العباس شارع 20"),
    # English sentence, 00964 prefix, trailing thanks.
    ("Hi, I'm Sara Ahmed from Basra, Al-Ashar near the Corniche. my number is 00964 780 555 4433. thanks",
     "Sara Ahmed", "+9647805554433", "Basra", "Al-Ashar near the Corniche"),
    # Name glued to the front of the address on one line.
    ("حيدر علي 07712345678 الموصل حي الزهور قرب جامع الزهور",
     "حيدر علي", "+9647712345678", "Nineveh", "الموصل حي الزهور قرب جامع الزهور"),
    # Address line first; "شارع بغداد" is a street, not the governorate.
    ("البصرة شارع بغداد قرب صيدلية الشفاء\nكرار حسن\n07701112222",
     "كرار حسن", "+9647701112222", "Basra", "شارع بغداد قرب صيدلية الشفاء"),
    # Greeting, order chatter, labels without colons, thanks.
    ("السلام عليكم\nاريد اطلب البدلة الزرقاء قياس 42\nالاسم حسين علي\nالرقم 07709998888\nالمحافظة واسط\n"
     "العنوان الكوت حي الحسين قرب مستشفى الزهراء\nشكرا",
     "حسين علي", "+9647709998888", "Wasit", "الكوت حي الحسين قرب مستشفى الزهراء"),
    # "محافظة X" line; +964 (0) style.
    ("حي الضباط قرب صيدلية الامل\nمحافظة البصرة\nمحمد جاسم\n+964 (0) 780 123 4567",
     "محمد جاسم", "+9647801234567", "Basra", "حي الضباط قرب صيدلية الامل"),
    # Dash-separated single line with a sector number.
    ("زينب علي - بغداد - مدينة الصدر - قطاع 45 - 07711223344",
     "زينب علي", "+9647711223344", "Baghdad", "مدينة الصدر، قطاع 45"),
    # "The order is for ..." phrasing.
    ("The order is for Huda Salman, Sulaymaniyah, Salim street near Grand Millennium hotel. Phone 07701231234",
     "Huda Salman", "+9647701231234", "Sulaymaniyah", "Salim street near Grand Millennium hotel"),
    # Landmark label -> rendered as "قرب ...".
    ("الاسم: رقية حسن\nالهاتف: 07811112222\nالمحافظة: بابل\nالمنطقة: الحلة حي بابل\nاقرب نقطة دالة: جامع الحسن",
     "رقية حسن", "+9647811112222", "Babil", "الحلة حي بابل، قرب جامع الحسن"),
    # Personal name "باسم" must not be read as a label.
    ("عندي طلب\nباسم محمد\n07812345678\nبابل\nالمسيب شارع المستشفى",
     "باسم محمد", "+9647812345678", "Babil", "المسيب شارع المستشفى"),
    # Name after the address inside an address label.
    ("العنوان: ديالى بعقوبة حي المعلمين قرب الجسر، علي حسين 07701234567",
     "علي حسين", "+9647701234567", "Diyala", "بعقوبة حي المعلمين قرب الجسر"),
    # Mixed Arabic/English.
    ("Mustafa Kareem\n0780 222 3333\nNajaf, حي الامير قرب مطعم الساعة",
     "Mustafa Kareem", "+9647802223333", "Najaf", "حي الامير قرب مطعم الساعة"),
    # Delivery destination overrides where the customer is from.
    ("انا من البصرة بس التوصيل لبغداد الدورة قرب سوق الدورة 07712223333 ام زينب",
     "ام زينب", "+9647712223333", "Baghdad", "الدورة قرب سوق الدورة"),
    # Kurdish-region order in English with Kurdish spelling of the city.
    ("Lana Kareem 0750 123 9876 Hawler, Ankawa near Ankawa mall",
     "Lana Kareem", "+9647501239876", "Erbil", "Ankawa near Ankawa mall"),
    # Country name dropped from the address.
    ("العراق - البصرة - حي الجزائر قرب مول البصرة\nمنتظر سالم 07801231231",
     "منتظر سالم", "+9647801231231", "Basra", "حي الجزائر قرب مول البصرة"),
]


class CleanOrdersTest(unittest.TestCase):
    def test_clean_orders(self):
        for message, name, phone, gov, address in CLEAN_ORDERS:
            with self.subTest(message=message):
                r = parse_order(message)
                self.assertEqual(r["name"], name)
                self.assertEqual(r["phone"], phone)
                self.assertEqual(r["governorate"], gov)
                self.assertEqual(r["address"], address)
                self.assertEqual(r["missing"], [])
                review = [w for w in r["warnings"] if w["severity"] == "review"]
                self.assertEqual(review, [])
                self.assertFalse(r["needs_review"])


class OutputShapeTest(unittest.TestCase):
    def test_keys_and_types(self):
        r = parse_order(CLEAN_ORDERS[0][0])
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r["governorate_ar"], "بغداد")
        self.assertIsInstance(r["alt_phones"], list)
        for w in r["warnings"]:
            self.assertEqual(set(w), {"code", "field", "severity", "message"})
            self.assertIn(w["severity"], ("review", "info"))

    def test_empty_message(self):
        r = parse_order("")
        self.assertEqual(r["missing"], ["name", "phone", "governorate", "address"])
        self.assertTrue(r["needs_review"])

    def test_non_string_rejected(self):
        with self.assertRaises(TypeError):
            parse_order(None)

    def test_never_raises_on_noise(self):
        rng = random.Random(1234)
        alphabet = "علي حسين بغداد البصرة 0123456789٠١٢٣٤٥٦٧٨٩ ,،:;-/\n.?؟ abcxyz +()📞📍 الاسم العنوان رقمي"
        for _ in range(500):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
            r = parse_order(text)
            self.assertEqual(set(r), KEYS)


class IncompleteOrdersTest(unittest.TestCase):
    def test_missing_fields_are_listed(self):
        r = parse_order("سارة 07733445566")
        self.assertEqual(r["missing"], ["governorate", "address"])
        self.assertTrue(r["needs_review"])

    def test_address_without_detail_is_vague(self):
        r = parse_order("مصطفى كريم\nالعمارة\n07725556666")
        self.assertEqual(r["governorate"], "Maysan")
        self.assertEqual(r["address"], "العمارة")
        self.assertIn("address_vague", codes(r))
        self.assertTrue(r["needs_review"])

    def test_governorate_only_gives_no_address(self):
        r = parse_order("علي حسين 07701234567 بغداد")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIsNone(r["address"])
        self.assertIn("address", r["missing"])

    def test_single_word_name_needs_review(self):
        r = parse_order("Name: Mustafa\nNumber: 7701234567\nAddress: Baghdad, Sadr City, sector 10")
        self.assertEqual(r["name"], "Mustafa")
        self.assertIn("name_single_word", codes(r))
        self.assertTrue(r["needs_review"])


class AmbiguityTest(unittest.TestCase):
    def test_city_from_other_governorate_flagged(self):
        r = parse_order("علي حسين 07701234567 بغداد الزبير قرب الجامع")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIn("governorate_city_mismatch", codes(r))
        self.assertTrue(r["needs_review"])

    def test_two_governorates_flagged(self):
        r = parse_order("علي حسين 07701234567 البصرة او بغداد حي الجامعة")
        self.assertIn("governorate_conflict", codes(r))
        self.assertTrue(r["needs_review"])

    def test_governorate_inferred_from_city_is_info_only(self):
        r = parse_order("حيدر علي 07712345678 الموصل حي الزهور قرب جامع الزهور")
        self.assertEqual(r["governorate"], "Nineveh")
        warning = next(w for w in r["warnings"] if w["code"] == "governorate_inferred")
        self.assertEqual(warning["severity"], "info")

    def test_misspelt_governorate_is_guessed_but_flagged(self):
        r = parse_order("بقداد الشعب قرب سوق الشعب\nمرتضى سالم\n07804445566")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIn("governorate_fuzzy", codes(r))
        self.assertTrue(r["needs_review"])

    def test_unrecognised_labelled_governorate(self):
        r = parse_order("الاسم: علي حسين\nالرقم: 07701234567\nالمحافظة: xyz\nالعنوان: حي الجامعة قرب الجسر")
        self.assertIsNone(r["governorate"])
        self.assertIn("governorate_unrecognized", codes(r))

    def test_product_line_is_not_the_name(self):
        r = parse_order("فستان احمر\nمحمد علي\n07712345678\nالنجف الكوفة حي ميسان قرب الجسر")
        self.assertEqual(r["name"], "محمد علي")
        self.assertEqual(r["notes"], "فستان احمر")

    def test_two_possible_names_flagged(self):
        r = parse_order("سيف علي\nمحمد كاظم\n07712345678\nالنجف حي الامير قرب الجسر")
        self.assertIn("name_ambiguous", codes(r))
        self.assertTrue(r["needs_review"])

    def test_greeting_that_is_also_a_name(self):
        r = parse_order("هلا علي كريم 07801234567 بابل الحلة حي الجزائر")
        self.assertEqual(r["name"], "علي كريم")
        self.assertIn("name_after_greeting", codes(r))

    def test_questions_go_to_notes(self):
        r = parse_order("كم سعر التوصيل للموصل؟\nنور الهدى محمد 07722334455 الموصل حي المثنى قرب جامعة الموصل")
        self.assertEqual(r["governorate"], "Nineveh")
        self.assertEqual(r["address"], "الموصل حي المثنى قرب جامعة الموصل")
        self.assertIn("كم سعر", r["notes"])


class NormalisationTest(unittest.TestCase):
    def test_diacritics_and_tatweel_removed(self):
        r = parse_order("الاسم: عَلِيّ حُسَيـــن\nالرقم: 07701234567\nبغداد الكرادة قرب الجسر")
        self.assertEqual(r["name"], "علي حسين")

    def test_latin_name_title_cased(self):
        r = parse_order("name: ALI al-rubaie\nphone 07701234567\nBaghdad Karrada near the bridge")
        self.assertEqual(r["name"], "Ali Al-Rubaie")

    def test_order_details_kept_in_notes(self):
        r = parse_order("اريد قطعتين لون اسود\nعلي حسين 07701234567 بغداد الكرادة قرب الجسر")
        self.assertEqual(r["notes"], "اريد قطعتين لون اسود")


if __name__ == "__main__":
    unittest.main()
