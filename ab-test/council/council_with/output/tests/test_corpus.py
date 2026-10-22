"""Corpus-driven tests and seeded fuzzing of the output invariants (D10)."""

import json
import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dallal_parser import GOVERNORATES, SCHEMA_KEYS, WARNING_CODES, clean_text, parse_order  # noqa: E402
from dallal_parser import gazetteer as gz  # noqa: E402
from dallal_parser import lexicon as lx  # noqa: E402
from dallal_parser.normalize import fold  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
PHONE_RE = re.compile(r"^\+9647[5-9][0-9]{8}$")
CORE = ("name", "phone", "governorate", "address")

# words that must never end up inside a name
_FORBIDDEN_IN_NAME = {
    fold(w)
    for words in (lx.EDGE_NOISE, lx.PRODUCT_WORDS, lx.ADDRESS_KEYWORDS, lx.LABELS["phone"], lx.LABELS["address"],
                  lx.LABELS["governorate"], ["اسمي", "انا", "اني", "i'm", "my"])
    for w in words
    if " " not in w
} - {fold(w) for w in lx.NAME_LIKE_GREETINGS} - {"no", "next", "town", "city"}
# ... nor place names (other than words that are also personal names), 'من/from', instructions
_GATED_WORDS = {fold(w) for w in gz.NAME_COLLISIONS + gz.GATED}
_FORBIDDEN_IN_NAME |= {
    fold(a) for tier in (gz.TIER_A, gz.TIER_B) for aliases in tier.values() for a in aliases
    if " " not in a and fold(a) not in _GATED_WORDS
} | {fold(w) for w in lx.NAME_TRAILERS + lx.NOT_NAME_WORDS if " " not in w} - {"ب"}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)["cases"]


def check_invariants(tc, text, r):
    tc.assertEqual(tuple(r), SCHEMA_KEYS)
    json.dumps(r, ensure_ascii=False)
    if r["phone"] is not None:
        tc.assertRegex(r["phone"], PHONE_RE)
        tc.assertEqual(r["phones"][0], r["phone"])
    for p in r["phones"]:
        tc.assertRegex(p, PHONE_RE)
    if r["governorate"] is not None:
        tc.assertIn(r["governorate"], GOVERNORATES)
    for f in CORE:
        tc.assertEqual(r[f] is None, f in r["missing"], f)
    for w in r["warnings"]:
        tc.assertIn(w["code"], WARNING_CODES)
    if r["name"]:
        source = clean_text(text)
        for tok in r["name"].split():
            tc.assertFalse(tok.isdigit(), r["name"])
            tc.assertFalse(re.search("[؀-ۿ][0-9]|[0-9][؀-ۿ]", tok), r["name"])
            tc.assertIn(tok, source, "name token not in input")
            tc.assertNotIn(fold(tok), _FORBIDDEN_IN_NAME, r["name"])
    if r["address"] and r["phone"]:
        tc.assertNotIn(r["phone"][4:], r["address"].replace(" ", ""))


class TestCorpus(unittest.TestCase):
    def test_cases(self):
        for case in load("corpus.json"):
            with self.subTest(id=case["id"], note=case["note"]):
                r = parse_order(case["input"])
                e = case["expect"]
                for f in ("name", "phone", "governorate"):
                    if f in e:
                        self.assertEqual(r[f], e[f], f)
                for s in e.get("address_contains", []):
                    self.assertIn(s, r["address"] or "")
                got = [w["code"] for w in r["warnings"]]
                for code in e.get("warnings", []):
                    self.assertIn(code, got)
                for code in e.get("no_warnings", []):
                    self.assertNotIn(code, got)
                check_invariants(self, case["input"], r)

    def test_corpus_size(self):
        self.assertGreaterEqual(len(load("corpus.json")), 60)


_DECOR = ["🌹", "❤️", "🙏", "السلام عليكم", "هلا اخي", "شكرا", "مرحبا 😍", "تمام", "صباح الخير",
          "اريد القطعة السودة قياس L", "لون رمادي", "اريد الكوت الاسود", "عدد 2 قطعة"]
_ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


class TestFuzz(unittest.TestCase):
    def test_decorated_and_shuffled_variants(self):
        rng = random.Random(1234)
        cases = load("corpus.json") + load("holdout.json")
        for n in range(500):
            case = rng.choice(cases)
            lines = case["input"].split("\n")
            if rng.random() < 0.5:
                lines.insert(rng.randrange(len(lines) + 1), rng.choice(_DECOR))
            if case.get("shuffle_safe") and rng.random() < 0.5:
                rng.shuffle(lines)
            text = "\n".join(lines)
            if rng.random() < 0.3:
                text = text.translate(rng.choice([_ARABIC_DIGITS, _PERSIAN_DIGITS]))
            if rng.random() < 0.2:
                text = text.replace(" ", rng.choice(["‏ ", "  ", "  "]))
            with self.subTest(n=n, id=case["id"]):
                r = parse_order(text)
                check_invariants(self, text, r)
                base = parse_order(case["input"])
                self.assertEqual(set(r["phones"]), set(base["phones"]))
                if case.get("shuffle_safe"):
                    self.assertEqual(r["phone"], base["phone"])
                    self.assertEqual(r["governorate"], base["governorate"])

    def test_decorations_alone_never_give_a_confident_governorate(self):
        for d in _DECOR + ["عمر خالد الرمادي", "هلا محمد", "ديالا حسن", "زين علي", "مثنى", "حمزة علي"]:
            with self.subTest(d=d):
                r = parse_order(d + "\n07701234567")
                self.assertFalse(r["governorate"] and r["confidence"]["governorate"] in ("high", "medium"), r)

    def test_random_strings(self):
        rng = random.Random(99)
        alphabet = ("ابتثجحخدذرزسشصضطظعغفقكلمنهويةىءأإآ ٠١٢٣٤٥٦٧٨٩۰۱۲۳0123456789+-()/.,،:\n"
                    "abcdefxyz 🌹😍‏‎ــ")
        for n in range(1000):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 300)))
            with self.subTest(n=n):
                check_invariants(self, text, parse_order(text))


if __name__ == "__main__":
    unittest.main()
