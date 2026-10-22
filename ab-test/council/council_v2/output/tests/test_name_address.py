"""D6-D8: labels, names, addresses."""
import unittest

import _helpers  # noqa: F401
from dallal_parser import parse_order


class TestName(unittest.TestCase):
    def test_labels(self):
        for raw, name in [
            ("الاسم: علي حسين\n07701234567\nبغداد الكرادة", "علي حسين"),
            ("الاسم الثلاثي: مرتضى جبار كاظم\n07701234567", "مرتضى جبار كاظم"),
            ("اسمي Ali, رقمي 0781 234 5678, Baghdad الكرادة", "Ali"),
            ("Name: Sara Ahmed, phone 07501234567, Erbil", "Sara Ahmed"),
            ("رقمي07801112233 واسمي حيدر سالم من الناصريه شارع الحبوبي", "حيدر سالم"),
            ("الاسم: عباس فاضل الرقم 07831234567 كربله شارع ميثم التمار", "عباس فاضل"),
            ("my name is Ahmed Ali, I live in Basra, Ashar. my number is 07801234567", "Ahmed Ali"),
            ("الاسم:\nزينب علي\n07701234567\nبغداد الكرادة", "زينب علي"),
            ("انا علي من بغداد الكرادة 07701234567", "علي"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_order(raw)["name"], name)

    def test_unlabelled(self):
        for raw, name in [
            ("محمد كاظم ٠٧٨١٢٣٤٥٦٧٨ كربلاء حي الحسين", "محمد كاظم"),
            ("بغداد البياع يم مطعم الساعة\nكاظم جبار 07809876512", "كاظم جبار"),
            ("07805556677\nبغداد البياع\nسجاد", "سجاد"),
            ("ام زهراء\n07709871234\nبغداد البياع شارع ٢٠", "ام زهراء"),
            ("مريم كريم، ديالى بعقوبة قرب سيطرة المفرق", "مريم كريم"),
            ("علي حسين بغداد الكرادة 07701234567", "علي حسين"),
            ("بغداد الكرادة علي حسين 07701234567", "علي حسين"),
            ("3li 07701234567 baghdad karrada", "3li"),
            ("سارة 🌹\n07701234567\nاربيل عنكاوا", "سارة"),
            ("منصور كاظم 07701234567 النجف حي الامير", "منصور كاظم"),
            ("Rawand 07504567890 Duhok, Malta quarter", "Rawand"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_order(raw)["name"], name)

    def test_no_name(self):
        for raw in ["البصره الزبير\n07709876543", "شكرا ❤️❤️", "السلام عليكم\n07701234567",
                    "اني من البصرة 07701234567", "اريد اطلب\n07701234567\nبغداد الكرادة",
                    "البصرة الجزائر 07701234567", "بغداد الكرادة قرب جامع الرحمن 07701234567"]:
            with self.subTest(raw=raw):
                r = parse_order(raw)
                self.assertIsNone(r["name"])
                self.assertIn("name", r["missing"])
                self.assertTrue(r["needs_review"])

    def test_greeting_and_product_not_name(self):
        r = parse_order("السلام عليكم\nاريد اطلب القطعة السودة\nالاسم: زينب عباس\n"
                        "الرقم: 0771 234 5678\nالعنوان: بغداد / الدورة / قرب سوق الدورة")
        self.assertEqual(r["name"], "زينب عباس")
        self.assertNotIn("اطلب", r["address"])
        self.assertNotIn("السلام", r["address"])


class TestAddress(unittest.TestCase):
    def test_address_kept_verbatim(self):
        r = parse_order("حيدر علي 07813456789\nبغداد مدينة الصدر قطاع ٤٤ يم سوق مريدي")
        self.assertIn("مدينة الصدر قطاع ٤٤ يم سوق مريدي", r["address"])
        r = parse_order("الاسم: رسل\nالهاتف: 07601234567\nكربله حي النقيب يم مدرسة الفرات")
        self.assertIn("يم مدرسة الفرات", r["address"])
        self.assertNotIn("كربله", r["address"])

    def test_labels_and_name_removed(self):
        r = parse_order("الاسم: نور محمد\nالعنوان: الموصل الزهور\nالرقم: 07701234567")
        self.assertEqual(r["address"], "الموصل الزهور")
        r = parse_order("المحافظة: ذي قار - الشطرة\nالاسم: مرتضى\nالهاتف: 07823456789")
        self.assertEqual(r["address"], "الشطرة")

    def test_landmark_city_names_stay(self):
        r = parse_order("ميسان العمارة شارع بغداد قرب الكراج\nالاسم: عباس جواد\n07735556677")
        self.assertIn("شارع بغداد", r["address"])

    def test_capital_or_governorate_only_is_missing(self):
        for raw in ["فاطمة 07801234567 كركوك", "فاطمة 07801234567 الناصرية",
                    "ئارام 07501472583 حلبجة", "الاسم: نور\nالعنوان: بغداد\nالرقم: 07701234567",
                    "Ali 07701234567 Basra"]:
            with self.subTest(raw=raw):
                r = parse_order(raw)
                self.assertIsNone(r["address"])
                self.assertIn("address", r["missing"])
                self.assertTrue(r["needs_review"])

    def test_district_town_is_an_address(self):
        r = parse_order("البصره الزبير\nعلي 07709876543")
        self.assertEqual(r["address"], "الزبير")
        self.assertFalse(r["needs_review"])

    def test_english_address(self):
        r = parse_order("Name: Sara, phone 07501234567, Erbil, 100m street near Family Mall")
        self.assertEqual(r["address"], "100m street near Family Mall")

    def test_house_numbers_not_labels(self):
        r = parse_order("Mansour street no 5, Ahmed 07701234567")
        self.assertIn("no 5", r["address"])
        r = parse_order("بغداد الدورة زقاق رقم 5 دار 12\nحسن 07701234567")
        self.assertIn("زقاق رقم 5 دار 12", r["address"])


if __name__ == "__main__":
    unittest.main()
