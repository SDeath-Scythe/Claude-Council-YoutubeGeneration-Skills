import unittest

from dallal_parser import extract_phones, normalize_phone


class NormalizePhoneTests(unittest.TestCase):
    def test_accepted_formats(self):
        expected = "+9647701234567"
        for raw in [
            "07701234567",
            "7701234567",
            "+9647701234567",
            "9647701234567",
            "009647701234567",
            "+964 770 123 4567",
            "0770 123 4567",
            "0770-123-4567",
            "0770.123.4567",
            "(0770) 123 4567",
            "+964 07701234567",  # redundant trunk zero
            "٠٧٧٠١٢٣٤٥٦٧",  # Arabic-Indic digits
            "۰۷۷۰۱۲۳۴۵۶۷",  # Persian digits
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone(raw), expected)

    def test_all_mobile_operator_prefixes(self):
        for prefix in ("75", "77", "78", "79"):
            self.assertEqual(normalize_phone(f"0{prefix}01234567"), f"+964{prefix}01234567")

    def test_rejected(self):
        for raw in [
            "0770123456",  # one digit short
            "077012345678",  # one digit long
            "+971501234567",  # UAE
            "017123456",  # Baghdad landline
            "0612345678",  # not a 07 mobile
            "07201234567",  # 072 is not a mobile range
            "",
            "abc",
        ]:
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_phone(raw))


class ExtractPhonesTests(unittest.TestCase):
    def numbers(self, text):
        return [h.number for h in extract_phones(text) if h.problem is None]

    def problems(self, text):
        return [h.problem for h in extract_phones(text) if h.problem]

    def test_number_after_house_number_is_not_glued(self):
        self.assertEqual(self.numbers("دار 5 07701234567"), ["+9647701234567"])
        self.assertEqual(self.numbers("زقاق 12 دار 7 0770 123 4567"), ["+9647701234567"])

    def test_two_numbers(self):
        self.assertEqual(
            self.numbers("07701234567 / 07801234567"),
            ["+9647701234567", "+9647801234567"],
        )
        self.assertEqual(
            self.numbers("07701234567 07801234567"),
            ["+9647701234567", "+9647801234567"],
        )

    def test_short_numbers_are_not_phones(self):
        self.assertEqual(extract_phones("زقاق 12 دار 5 شارع 62"), [])

    def test_invalid_attempts_are_reported(self):
        self.assertEqual(self.problems("رقمي 0770123456"), ["wrong_length"])
        self.assertEqual(self.problems("+971 50 123 4567"), ["non_iraqi"])

    def test_spans_cover_the_raw_text(self):
        text = "رقمي 0770 123 4567 شكرا"
        (hit,) = extract_phones(text)
        self.assertEqual(text[hit.start:hit.end], "0770 123 4567")


if __name__ == "__main__":
    unittest.main()
