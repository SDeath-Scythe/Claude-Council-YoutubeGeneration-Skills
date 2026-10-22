import unittest

from dallal_parser import normalize_iraqi_mobile, parse_order
from dallal_parser.normalize import clean_text
from dallal_parser.phones import find_phones


def phones_in(text):
    found, bad = find_phones(clean_text(text))
    return [p.e164 for p in found], [b.raw for b in bad]


class NormalizeMobileTest(unittest.TestCase):
    def test_accepted_forms(self):
        for raw in ["07701234567", "7701234567", "9647701234567", "009647701234567", "96407701234567"]:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_iraqi_mobile(raw), "+9647701234567")

    def test_rejected_forms(self):
        for raw in ["0770123456", "077012345678", "01234567890", "9641234567890", "12345", ""]:
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_iraqi_mobile(raw))


class FindPhonesTest(unittest.TestCase):
    def test_spacing_and_punctuation(self):
        for text in [
            "0770 123 4567", "0770-123-4567", "0770.123.4567", "+964 770 123 4567",
            "+964 (0) 770 123 4567", "00964-770-1234567", "(0770) 1234567", "0 7 7 0 1 2 3 4 5 6 7",
        ]:
            with self.subTest(text=text):
                self.assertEqual(phones_in(text)[0], ["+9647701234567"])

    def test_arabic_and_persian_digits(self):
        self.assertEqual(phones_in("٠٧٧٠١٢٣٤٥٦٧")[0], ["+9647701234567"])
        self.assertEqual(phones_in("۰۷۷۰۱۲۳۴۵۶۷")[0], ["+9647701234567"])
        self.assertEqual(phones_in("+٩٦٤ ٧٧٠ ١٢٣ ٤٥٦٧")[0], ["+9647701234567"])

    def test_glued_to_arabic_word(self):
        self.assertEqual(phones_in("رقمي07801234567")[0], ["+9647801234567"])

    def test_house_number_not_glued_to_phone(self):
        self.assertEqual(phones_in("زقاق 5 دار 12 07701234567")[0], ["+9647701234567"])
        self.assertEqual(phones_in("دار 7 07701234567")[0], ["+9647701234567"])

    def test_two_phones(self):
        self.assertEqual(phones_in("07701234567 07801234567")[0], ["+9647701234567", "+9647801234567"])
        self.assertEqual(phones_in("07701234567/07801234567")[0], ["+9647701234567", "+9647801234567"])

    def test_prices_are_not_phones(self):
        self.assertEqual(phones_in("السعر 25,000 دينار و 1.500.000"), ([], []))

    def test_short_number_reported_as_bad(self):
        found, bad = phones_in("رقمي 0770123456")
        self.assertEqual(found, [])
        self.assertEqual(bad, ["0770123456"])

    def test_arabizi_digits_are_not_phones(self):
        self.assertEqual(phones_in("jame3 07701234567")[0], ["+9647701234567"])


class PhoneFieldTest(unittest.TestCase):
    def test_alt_phone_label(self):
        r = parse_order("علي حسين\nرقم ثاني: 07801234567\nرقمي: 07701234567\nبغداد الكرادة قرب ساحة كهرمانة")
        self.assertEqual(r["phone"], "+9647701234567")
        self.assertEqual(r["alt_phones"], ["+9647801234567"])

    def test_duplicate_phone_collapsed(self):
        r = parse_order("علي حسين 07701234567 بغداد الكرادة قرب الجسر 0770 123 4567")
        self.assertEqual(r["phone"], "+9647701234567")
        self.assertEqual(r["alt_phones"], [])

    def test_unknown_operator_needs_review(self):
        r = parse_order("علي حسين 07601234567 بغداد الكرادة قرب الجسر")
        self.assertEqual(r["phone"], "+9647601234567")
        self.assertIn("phone_unknown_operator", [w["code"] for w in r["warnings"]])
        self.assertTrue(r["needs_review"])

    def test_invalid_phone_is_not_guessed(self):
        r = parse_order("علي حسين 077012345 بغداد الكرادة قرب الجسر")
        self.assertIsNone(r["phone"])
        self.assertIn("phone", r["missing"])
        self.assertIn("phone_invalid", [w["code"] for w in r["warnings"]])
        self.assertNotIn("077012345", r["address"])


if __name__ == "__main__":
    unittest.main()
