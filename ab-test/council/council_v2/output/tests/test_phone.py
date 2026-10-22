"""D3: strict phone grammar, never repaired."""
import unittest

import _helpers  # noqa: F401
from dallal_parser import parse_order


def P(t):
    return parse_order(t)


class TestPhone(unittest.TestCase):
    def test_valid_forms(self):
        for raw in ["07501234567", "0750-123-4567", "0750.123.4567", "(0750) 123 4567",
                    "750 123 4567", "+9647501234567", "00 964 750 123 4567", "+964-750-123-4567",
                    "٠٧٥٠ ١٢٣ ٤٥٦٧", "۰۷۵۰۱۲۳۴۵۶۷", "0750‏123‏4567", "رقمي07501234567"]:
            with self.subTest(raw=raw):
                self.assertEqual(P(raw)["phone"], "+9647501234567")

    def test_all_operator_prefixes(self):
        for p in "3456789":
            self.assertEqual(P("07%s01234567" % p)["phone"], "+9647%s01234567" % p)

    def test_trunk_zero(self):
        r = P("+964 0770 123 4567")
        self.assertEqual(r["phone"], "+9647701234567")
        self.assertIn("phone_trunk_zero_removed", r["warnings"])
        self.assertEqual(P("964 07701234567")["phone"], "+9647701234567")

    def test_invalid_length_never_trimmed_or_padded(self):
        for raw in ["0770123456", "077012345678", "0770 123 45", "0781234567", "07701234567890"]:
            with self.subTest(raw=raw):
                r = P(raw)
                self.assertIsNone(r["phone"])
                self.assertIn("phone_invalid_length", r["warnings"])
                self.assertTrue(r["needs_review"])

    def test_invalid_prefix(self):
        for raw in ["07012345678", "07112345678", "07212345678", "+964 720 123 4567"]:
            with self.subTest(raw=raw):
                r = P(raw)
                self.assertIsNone(r["phone"])
                self.assertIn("phone_invalid_prefix", r["warnings"])

    def test_foreign(self):
        for raw in ["+44 7700 900123", "+46 70 123 45 67", "+1 415 555 2671", "0044 7700 900123"]:
            with self.subTest(raw=raw):
                r = P("علي " + raw + " بغداد الكرادة")
                self.assertIsNone(r["phone"])
                self.assertIn("phone_foreign", r["warnings"])
                self.assertTrue(r["needs_review"])

    def test_ambiguous_prefix(self):
        for raw in ["44 7700 900123", "دار 7 7712345678"]:
            with self.subTest(raw=raw):
                r = P(raw)
                self.assertIn("phone_ambiguous_prefix", r["warnings"])
                self.assertTrue(r["needs_review"])
                self.assertIsNone(r["phone"])  # never a guessed number (F46)
                self.assertIn("الرقم ناقص أو غلط", r["followup_ar"])

    def test_ambiguous_join(self):
        for raw in ["0770123456 4", "0 7701234567"]:
            with self.subTest(raw=raw):
                r = P("علي " + raw + " بغداد الكرادة")
                self.assertIn("phone_ambiguous_join", r["warnings"])
                self.assertIsNone(r["phone"])
        self.assertEqual(P("0770 123 45 67")["warnings"], [])

    def test_correction_and_ranking(self):
        r = P("علي 07701234567 بغداد المنصور\nعفوا الرقم غلط الصحيح 07801234567")
        self.assertEqual((r["phone"], r["alt_phone"]), ("+9647801234567", None))
        self.assertIn("phone_corrected", r["warnings"])
        self.assertFalse(r["needs_review"])
        r = P("رقم البيت 07801234567 رقمي 07712345678 علي بغداد الكرادة")
        self.assertEqual((r["phone"], r["alt_phone"]), ("+9647712345678", "+9647801234567"))

    def test_short_group_before_national_is_clean(self):
        r = P("بغداد مدينة الصدر قطاع 10 07711112222 علي")
        self.assertEqual(r["phone"], "+9647711112222")
        self.assertNotIn("phone_ambiguous_prefix", r["warnings"])
        self.assertIn("قطاع 10", r["address"])

    def test_short_numbers_ignored(self):
        r = P("بغداد زقاق رقم 5 دار 12 شارع 60\nعلي 07701234567")
        self.assertEqual(r["warnings"], [])
        self.assertIn("زقاق رقم 5", r["address"])

    def test_two_numbers(self):
        r = P("07701234567 07501234567")
        self.assertEqual((r["phone"], r["alt_phone"]), ("+9647701234567", "+9647501234567"))
        r = P("07701234567 او 07501234567")
        self.assertEqual(r["alt_phone"], "+9647501234567")
        r = P("07701234567\n0770 123 4567")
        self.assertEqual((r["phone"], r["alt_phone"]), ("+9647701234567", None))
        r = P("07701234567 07501234567 07801234567")
        self.assertIn("extra_phones", r["warnings"])

    def test_phone_not_from_other_line_digits(self):
        r = P("عندي طلب ٢ قطعة السعر ٢٥ الف\nالاسم فاطمة\nرقم ٠٧٧١٥٥٥٦٦٦٧\nبغداد الكرادة")
        self.assertEqual(r["phone"], "+9647715556667")

    def test_address_never_contains_phone(self):
        r = P("بغداد الكرادة 07701234567 قرب جامع 077012345678")
        self.assertNotIn("0770", r["address"] or "")


if __name__ == "__main__":
    unittest.main()
