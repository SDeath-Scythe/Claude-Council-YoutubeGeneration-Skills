"""D4/D5: gazetteer tiers, false friends, conflicts."""
import unittest

import _helpers  # noqa: F401
from dallal_parser import parse_order, GOVERNORATES


def G(t):
    return parse_order(t)["governorate"]


class TestGovernorate(unittest.TestCase):
    def test_all_19_arabic(self):
        names = {"بغداد": "Baghdad", "البصرة": "Basra", "نينوى": "Nineveh", "اربيل": "Erbil",
                 "السليمانية": "Sulaymaniyah", "دهوك": "Duhok", "كركوك": "Kirkuk", "ديالى": "Diyala",
                 "الانبار": "Anbar", "بابل": "Babylon", "كربلاء": "Karbala", "النجف": "Najaf",
                 "واسط": "Wasit", "ميسان": "Maysan", "ذي قار": "Dhi Qar", "المثنى": "Muthanna",
                 "القادسية": "Qadisiyyah", "صلاح الدين": "Saladin", "حلبجة": "Halabja"}
        self.assertEqual(sorted(names.values()), sorted(GOVERNORATES))
        for ar, en in names.items():
            with self.subTest(ar=ar):
                self.assertEqual(G("علي حسين 07701234567 %s حي الجامعة" % ar), en)

    def test_english_and_kurdish(self):
        cases = {"Hawler": "Erbil", "Slemani": "Sulaymaniyah", "Dohuk": "Duhok", "Kerbala": "Karbala",
                 "Thi Qar": "Dhi Qar", "Salahaddin": "Saladin", "Babil": "Babylon", "Ninawa": "Nineveh",
                 "هەولێر": "Erbil", "سلێمانی": "Sulaymaniyah", "دهۆک": "Duhok", "Al-Anbar": "Anbar",
                 "Nasiriyah": "Dhi Qar", "Diwaniyah": "Qadisiyyah", "Samawah": "Muthanna",
                 "Ramadi": "Anbar", "Tikrit": "Saladin", "Baqubah": "Diyala", "Amarah": "Maysan",
                 "Hilla": "Babylon", "Zakho": "Duhok", "Ankawa": "Erbil", "Kufa": "Najaf"}
        for raw, en in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(G("Ali 07701234567 %s, near the bridge" % raw), en)

    def test_dialect_spellings(self):
        for raw, en in [("كربله", "Karbala"), ("كربلا", "Karbala"), ("دياله", "Diyala"),
                        ("حلبجه", "Halabja"), ("بـغـداد", "Baghdad"), ("البَصْرة", "Basra"),
                        ("بالحله", "Babylon"), ("للبصرة", "Basra"), ("الديوانيه", "Qadisiyyah"),
                        ("الناصريه", "Dhi Qar"), ("سامرا", "Saladin"), ("العماره", "Maysan")]:
            with self.subTest(raw=raw):
                self.assertEqual(G("علي 07701234567 %s حي الجامعة" % raw), en)

    def test_inferred_warning_non_blocking(self):
        r = parse_order("علي 07701234567 الموصل حي الزهور")
        self.assertEqual(r["governorate"], "Nineveh")
        self.assertIn("governorate_inferred_from_city", r["warnings"])
        self.assertFalse(r["needs_review"])

    def test_nisba_surnames_not_places(self):
        r = parse_order("الاسم: حسين البصري\nالرقم: 07823334455\nالنجف حي الحنانة")
        self.assertEqual(r["governorate"], "Najaf")
        self.assertEqual(G("علي الموصلي 07701234567 كربلاء حي العباس"), "Karbala")

    def test_landmarks_named_after_cities(self):
        self.assertEqual(G("ميسان العمارة شارع بغداد قرب الكراج\nعباس 07735556677"), "Maysan")
        self.assertEqual(G("بغداد المنصور قرب مطعم الموصل\nسارة 07801234567"), "Baghdad")
        self.assertEqual(G("اربيل قرب جامعة صلاح الدين\nعلي 07501234567"), "Erbil")
        self.assertEqual(G("البصرة كراج النجف\nعلي 07701234567"), "Basra")
        self.assertIsNone(G("شارع بغداد\nعلي 07701234567"))

    def test_district_named_like_governorate(self):
        self.assertEqual(G("تكريت حي القادسية\nياسر 07709990011"), "Saladin")
        self.assertEqual(G("تكريت القادسية 07701230000 ابو احمد"), "Saladin")
        self.assertEqual(G("بغداد الكرادة حي بابل\nرنا 07705551234"), "Baghdad")

    def test_amarah_building(self):
        self.assertEqual(G("بغداد زيونة قرب عمارة الاطباء\nمريم 07711223344"), "Baghdad")
        self.assertEqual(G("بغداد العمارة 12 شقة 4\nزينب 07712345678"), "Baghdad")
        self.assertEqual(G("كرار ٠٧٨٠٥٥٥٤٤٣٣ العماره شارع دجلة"), "Maysan")

    def test_collision_aliases_in_product_lines(self):
        r = parse_order("اريد الكوت الرمادي قياس L\nالاسم احمد\n07701234567\nبغداد زيونة")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertNotIn("governorate_conflict", r["warnings"])
        r = parse_order("اريد القميص الهندي او الرمادي\nعلي 07701234567 البصرة العشار")
        self.assertEqual(r["governorate"], "Basra")
        self.assertEqual(G("علي 07701234567 الرمادي حي الملعب"), "Anbar")
        self.assertEqual(G("علي 07701234567 ساكن بالكوت"), "Wasit")

    def test_generic_districts_do_not_infer(self):
        for d in ["حي الحسين قرب الجامع", "حي العسكري", "الجمهورية", "حي الشهداء", "اليرموك",
                  "العامرية", "الحسينية", "الجزائر"]:
            with self.subTest(d=d):
                r = parse_order("الاسم علي\n07709998877\n" + d)
                self.assertIsNone(r["governorate"])
                self.assertTrue(r["needs_review"])

    def test_multiple_governorates(self):
        r = parse_order("ابو حيدر 07701234567 البصرة او ميسان")
        self.assertIsNone(r["governorate"])
        self.assertIn("multiple_governorates", r["warnings"])
        self.assertTrue(r["needs_review"])
        self.assertIn("البصرة", r["followup_ar"])
        r = parse_order("انا بالحلة بس ابعثوه للناصرية حي الشهداء\n07701234567 علي")
        self.assertEqual(r["governorate"], "Dhi Qar")
        self.assertIn("multiple_governorates", r["warnings"])

    def test_conflict_tier1_vs_district(self):
        r = parse_order("علي 07701234567 بغداد الزبير")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIn("governorate_conflict", r["warnings"])
        self.assertTrue(r["needs_review"])

    def test_person_name_governorates(self):
        r = parse_order("ميسان 07701234567 بغداد الكرادة")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertEqual(r["name"], "ميسان")
        r = parse_order("اسمي صلاح الدين خليل\n07501234567\nاربيل عنكاوا")
        self.assertEqual(r["governorate"], "Erbil")
        self.assertEqual(r["name"], "صلاح الدين خليل")

    def test_never_from_phone_prefix(self):
        self.assertIsNone(G("07501234567"))


if __name__ == "__main__":
    unittest.main()
