"""Unit tests for the stages: normalisation, phones, gazetteer/governorate."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dallal_parser import GOVERNORATES, clean_text, normalize_phone, resolve_governorate  # noqa: E402
from dallal_parser import gazetteer as gz  # noqa: E402
from dallal_parser.governorate import LOOKUP, _key  # noqa: E402
from dallal_parser.normalize import fold  # noqa: E402
from dallal_parser.phones import canonicalize, extract_from_line  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_digits_only_arabic_and_persian(self):
        self.assertEqual(clean_text("٠١٢٣٤٥٦٧٨٩ ۰۱۲۳۴۵۶۷۸۹"), "0123456789 0123456789")
        # Devanagari / NKo / mathematical digits are NOT phone digits
        self.assertEqual(clean_text("०७७"), "०७७")
        self.assertEqual(clean_text("߀"), "߀")

    def test_invisible_chars_removed_letters_kept(self):
        self.assertEqual(clean_text("‏أسامة‎  جاسم﻿"), "أسامة جاسم")
        self.assertEqual(clean_text("بغـــداد"), "بغداد")
        self.assertEqual(clean_text("a b c"), "a b c")

    def test_fold(self):
        self.assertEqual(fold("البصرة"), fold("البصره"))
        self.assertEqual(fold("أربيل"), fold("اربيل"))
        self.assertEqual(fold("كربلاء"), fold("كربلا"))
        self.assertEqual(fold("البَصرة"), fold("البصرة"))
        self.assertEqual(fold("سلێمانی"), fold("سليماني"))
        self.assertEqual(fold("دهۆک"), fold("دهوك"))
        self.assertEqual(fold("BASRA"), "basra")
        self.assertNotEqual(fold("البصري"), fold("البصرة"))  # nisba stays different


class TestPhones(unittest.TestCase):
    def test_normalize_phone(self):
        for raw in ["07701234567", "+964 770 123 4567", "00964 770 123 4567", "964-770-123-4567", "7701234567",
                    "(0770) 123-4567", "+964 0770 123 4567"]:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone(raw), "+9647701234567")
        for raw in ["07401234567", "+971501234567", "0123456", "077012345678", "0770123456", "abc", "",
                    "0770 123 4567 extra"]:
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_phone(raw))
        with self.assertRaises(TypeError):
            normalize_phone(7701234567)

    def test_operator_prefixes(self):
        for p in ("75", "77", "78", "79"):
            self.assertEqual(canonicalize("0%s12345678" % p), ("+964%s12345678" % p, None, False))
        self.assertEqual(canonicalize("07612345678"), ("+9647612345678", None, True))
        for p in ("70", "71", "72", "73", "74"):
            self.assertEqual(canonicalize("0%s12345678" % p)[1], "unknown_prefix")

    def test_reasons(self):
        self.assertEqual(canonicalize("0771234567")[1], "too_short")
        self.assertEqual(canonicalize("077123456789")[1], "too_long")
        self.assertEqual(canonicalize("0112345678")[1], "not_mobile")
        self.assertEqual(canonicalize("971501234567", had_plus=True)[1], "foreign")

    def test_never_joins_across_letters_or_lines(self):
        self.assertEqual(extract_from_line("زقاق 7 دار 75").valid, [])
        self.assertEqual(extract_from_line("0770 دار 1234567").valid, [])
        self.assertEqual(extract_from_line("m7md 3li 100m").valid, [])

    def test_two_numbers_one_line(self):
        nums = [m.number for m in extract_from_line("07701234567 07801234567").valid]
        self.assertEqual(nums, ["+9647701234567", "+9647801234567"])

    def test_long_junk_is_fast_and_safe(self):
        res = extract_from_line("0 " * 3000)
        self.assertEqual(res.valid, [])


class TestGazetteer(unittest.TestCase):
    def test_every_alias_reachable(self):
        for tier in (gz.TIER_A, gz.TIER_B, gz.EXPLICIT_PHRASES):
            for gov, aliases in tier.items():
                self.assertIn(gov, GOVERNORATES)
                for a in aliases:
                    with self.subTest(alias=a):
                        self.assertIn(_key(a), LOOKUP)
        for a in gz.TIER_C_BAGHDAD:
            self.assertIn(_key(a), LOOKUP)

    def test_19_governorates_all_have_tier_a(self):
        self.assertEqual(len(GOVERNORATES), 19)
        self.assertEqual(set(gz.TIER_A), set(GOVERNORATES))

    def test_excluded_words_are_not_places(self):
        for w in ["الحي", "بلد", "حديثة", "المدينة", "الرفاعي", "اليرموك", "المنصور", "ana", "hit",
                  "balad", "حمزة", "خضر", "القاسم", "البصري", "النجفي", "البغدادي"]:
            with self.subTest(word=w):
                self.assertIsNone(resolve_governorate(w))

    def test_resolve_governorate(self):
        for text, gov in [("الناصرية", "Dhi Qar"), ("هولير", "Erbil"), ("basrah", "Basra"), ("ببغداد", "Baghdad"),
                          ("بالبصرة", "Basra"), ("للنجف", "Najaf"), ("Sulaimani", "Sulaymaniyah"),
                          ("ذي قار", "Dhi Qar"), ("صلاح الدين", "Saladin"), ("حلبجة", "Halabja"),
                          ("مثنى", "Muthanna"), ("الكرادة", "Baghdad")]:
            with self.subTest(text=text):
                self.assertEqual(resolve_governorate(text), gov)
        self.assertIsNone(resolve_governorate("بغداد البصرة"))  # ambiguous -> None
        self.assertIsNone(resolve_governorate(""))
        with self.assertRaises(TypeError):
            resolve_governorate(None)


if __name__ == "__main__":
    unittest.main()
