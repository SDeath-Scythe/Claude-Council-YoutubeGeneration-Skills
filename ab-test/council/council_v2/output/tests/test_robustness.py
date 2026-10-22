"""D10: never raises, schema/type invariants, speed (seeded fuzz)."""
import random
import re
import time
import unittest

import _helpers  # noqa: F401
from dallal_parser import parse_order, GOVERNORATES

KEYS = {"name", "phone", "governorate", "address", "alt_phone", "needs_review",
        "missing", "warnings", "followup_ar", "notes"}
PHONE_RE = re.compile(r"^\+9647[3-9]\d{8}$")
ALPHABET = list("abcdefghijklmnopqrstuvwxyz ABCXYZ0123456789٠١٢٣٤٥٦٧٨٩۰۱۲۳+-().,،/:\n\t?؟!"
                "ابتثجحخدذرزسشصضطظعغفقكلمنهويةىأإآؤئءگچپڤکیەێۆـًٌٍَُِّْ‏‎​﻿"
                "😍🌹❤️📞🔥") + ["بغداد", "البصرة", "الكرادة", "الاسم", "رقم", "07701234567",
                                 "قرب", "حي", "العمارة", "الكوت", "ميسان", "صلاح الدين", "name:",
                                 "+964", "00964", "اريد", "انا", "\ud800"]


class TestRobustness(unittest.TestCase):
    def check(self, r):
        self.assertEqual(set(r), KEYS)
        for f in ("name", "governorate", "address", "phone", "alt_phone", "followup_ar", "notes"):
            self.assertTrue(r[f] is None or isinstance(r[f], str))
        self.assertIsInstance(r["needs_review"], bool)
        self.assertIsInstance(r["missing"], list)
        self.assertIsInstance(r["warnings"], list)
        for f in ("phone", "alt_phone"):
            if r[f] is not None:
                self.assertRegex(r[f], PHONE_RE)
        self.assertTrue(r["governorate"] is None or r["governorate"] in GOVERNORATES)
        self.assertEqual(r["missing"], [f for f in ("name", "phone", "governorate", "address")
                                        if r[f] is None])
        if r["missing"]:
            self.assertTrue(r["needs_review"])
        self.assertEqual(r["followup_ar"] is None, not r["needs_review"])
        if r["name"]:
            self.assertLessEqual(len(r["name"]), 80)
        for f in ("name", "address"):
            if r[f]:
                self.assertEqual(r[f], r[f].strip())
                self.assertNotRegex(r[f], r"\d{9,}")

    def test_fuzz(self):
        rnd = random.Random(1234)
        for _ in range(2000):
            s = "".join(rnd.choice(ALPHABET) for _ in range(rnd.randint(0, 60)))
            self.check(parse_order(s))

    def test_non_str(self):
        for v in (None, 123, b"bytes", ["x"], {"a": 1}):
            self.check(parse_order(v))

    def test_large_and_speed(self):
        big = ("علي حسين 07701234567 بغداد الكرادة قرب جامع الرحمن\n" * 400)[:10240]
        t = time.perf_counter()
        self.check(parse_order(big))
        self.assertLess(time.perf_counter() - t, 0.5)
        r = parse_order("ب" * 30000)
        self.assertIn("input_truncated", r["warnings"])
        t = time.perf_counter()
        for _ in range(200):
            parse_order("الاسم: علي حسين\nالرقم: 07701234567\nبغداد الكرادة قرب جامع الرحمن")
        self.assertLess((time.perf_counter() - t) / 200, 0.05)

    def test_10kb_adversarial_under_200ms(self):
        # D10: 10 KB < 200 ms, including inputs that stress phone-group joining,
        # gazetteer matching, labels and greeting stripping.
        for s in ["0 7 " * 2500, "1 " * 5000, "ب " * 5000, "بغداد " * 1700, "شكرا " * 2000,
                  "الاسم علي " * 1000, "الكوت " * 1700, "0" * 10240, "+964 " * 2000,
                  "بغداد الكرادة قرب " * 550, "ميسان 0770123456 " * 600]:
            with self.subTest(s=s[:12]):
                t = time.perf_counter()
                self.check(parse_order(s))
                self.assertLess(time.perf_counter() - t, 0.2)

    def test_internal_error_is_logged_and_flagged(self):
        from unittest import mock
        import dallal_parser.core as core
        with mock.patch.object(core, "_parse", side_effect=RuntimeError("boom")):
            with self.assertLogs("dallal_parser", level="ERROR") as cm:
                r = parse_order("علي 07701234567 بغداد الكرادة")
        self.check(r)
        self.assertEqual(r["warnings"], ["internal_error"])
        self.assertTrue(r["needs_review"])
        self.assertIn("boom", "\n".join(cm.output))

    def test_name_length_caps(self):
        for s in ["ا" * 10240, "x" * 10240, "xxxxxxxxxx"]:
            self.assertIsNone(parse_order(s)["name"])

    def test_pathological_digits(self):
        for s in ["0" * 5000, "1 " * 5000, "+" * 3000, "07701234567" * 500, "- " * 5000]:
            self.check(parse_order(s))


if __name__ == "__main__":
    unittest.main()
