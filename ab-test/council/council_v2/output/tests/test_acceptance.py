"""Acceptance tests AT1-AT9 from the charter (written before the implementation)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dallal_parser import parse_order  # noqa: E402

KEYS = {"name", "phone", "governorate", "address", "alt_phone",
        "needs_review", "missing", "warnings", "followup_ar", "notes"}


class TestAcceptance(unittest.TestCase):
    def test_at1_labelled_arabic(self):
        r = parse_order("الاسم: علي حسين\nالرقم: 07701234567\nبغداد الكرادة قرب جامع الرحمن")
        self.assertEqual(r["name"], "علي حسين")
        self.assertEqual(r["phone"], "+9647701234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIn("الكرادة", r["address"])
        self.assertIn("قرب جامع الرحمن", r["address"])
        self.assertFalse(r["needs_review"])
        self.assertIsNone(r["followup_ar"])

    def test_at2_phone_normalisation(self):
        for raw in ["07701234567", "0770 123 4567", "0770-123-4567", "7701234567",
                    "9647701234567", "+964 770 123 4567", "00964 7701234567",
                    "٠٧٧٠١٢٣٤٥٦٧", "۰۷۷۰۱۲۳۴۵۶۷"]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_order(raw)["phone"], "+9647701234567")

    def test_at3_invalid_not_fixed(self):
        r = parse_order("0770123456")
        self.assertIsNone(r["phone"])
        self.assertTrue(r["needs_review"])
        self.assertTrue(any("phone" in w for w in r["warnings"]))

    def test_at4_governorate_spellings(self):
        cases = {"البصرة": "Basra", "بصره": "Basra", "basra": "Basra", "Basrah": "Basra",
                 "الموصل": "Nineveh", "Mosul": "Nineveh", "الناصرية": "Dhi Qar",
                 "الحلة": "Babylon", "الديوانية": "Qadisiyyah",
                 "السليمانية": "Sulaymaniyah", "slemani": "Sulaymaniyah"}
        for raw, gov in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_order(raw)["governorate"], gov)
                self.assertEqual(
                    parse_order("علي حسين 07701234567 %s حي الجامعة" % raw)["governorate"], gov)

    def test_at5_english(self):
        r = parse_order("Name: Sara Ahmed, phone +964 750 987 6543, Erbil, 100m street near Family Mall")
        self.assertEqual(r["name"], "Sara Ahmed")
        self.assertEqual(r["phone"], "+9647509876543")
        self.assertEqual(r["governorate"], "Erbil")
        self.assertIn("Family Mall", r["address"])

    def test_at6_mixed_unlabelled(self):
        r = parse_order("محمد كاظم ٠٧٨١٢٣٤٥٦٧٨ كربلاء حي الحسين")
        self.assertEqual(r["name"], "محمد كاظم")
        self.assertEqual(r["phone"], "+9647812345678")
        self.assertEqual(r["governorate"], "Karbala")
        self.assertIn("حي الحسين", r["address"])

    def test_at7_robustness(self):
        for raw in ["", "مرحبا", "😍🔥🌹", "x" * 10240, ("بغداد 0770 " * 1000)]:
            with self.subTest(raw=raw[:20]):
                r = parse_order(raw)
                self.assertEqual(set(r), KEYS)
                self.assertTrue(r["needs_review"])
                for f in ("name", "phone", "governorate", "address"):
                    if r[f] is None:
                        self.assertIn(f, r["missing"])
        r = parse_order("")
        self.assertEqual(r["missing"], ["name", "phone", "governorate", "address"])

    def test_at8_baghdad_districts(self):
        for d in ["المنصور", "الكرادة", "زيونة", "مدينة الصدر"]:
            with self.subTest(d=d):
                self.assertEqual(parse_order(d)["governorate"], "Baghdad")
                r = parse_order("علي حسين 07701234567 %s قرب الجامع" % d)
                self.assertEqual(r["governorate"], "Baghdad")
                self.assertIn("governorate_inferred_from_city", r["warnings"])
                self.assertIn(d, r["address"])


if __name__ == "__main__":
    unittest.main()
