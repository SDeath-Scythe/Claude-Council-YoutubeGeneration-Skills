"""Holdout gate (D10): DMs written by separate agents that never saw the code.

* holdout.json (30 cases) - read by council seats during debate, so partly seen.
* holdout_blind.json (40 cases) - written after the build by an agent that saw
  nothing; its first score (before any fix) is recorded in the README.

Both files are frozen.  A failing case may only be fixed by a *generic* rule or
lexicon change, and a copy may be added to corpus.json - never by editing
holdout.json.  Run this file directly for the per-field report:

    python3 tests/test_holdout.py --report
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dallal_parser import parse_order  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
HOLDOUTS = ("holdout.json", "holdout_blind.json")
FIELDS = ("name", "phone", "governorate")
CONFIDENT = ("high", "medium")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)["cases"]


def score(name):
    """Per field: correct / abstained (None or low) / confident-wrong."""
    stats = {f: {"correct": 0, "abstained": 0, "confident_wrong": 0, "low_wrong": 0} for f in FIELDS}
    stats["address"] = {"correct": 0, "missed": 0}
    wrong = []
    cases = load(name)
    for case in cases:
        r = parse_order(case["input"])
        for f in FIELDS:
            exp, got, conf = case["expect"].get(f), r[f], r["confidence"][f]
            if got == exp:
                stats[f]["correct"] += 1
            elif got is None:
                stats[f]["abstained"] += 1
            elif conf in CONFIDENT:
                stats[f]["confident_wrong"] += 1
                wrong.append((case["id"], f, exp, got, conf))
            else:
                stats[f]["low_wrong"] += 1
        subs = case["expect"].get("address_contains") or []
        if all(r["address"] and s in r["address"] for s in subs):
            stats["address"]["correct"] += 1
        else:
            stats["address"]["missed"] += 1
    return len(cases), stats, wrong


class TestHoldout(unittest.TestCase):
    def test_no_confident_wrong_phone_or_governorate(self):
        for name in HOLDOUTS:
            with self.subTest(file=name):
                _, stats, wrong = score(name)
                self.assertEqual(stats["phone"]["confident_wrong"], 0, wrong)
                self.assertEqual(stats["governorate"]["confident_wrong"], 0, wrong)

    def test_name_confident_wrong_at_most_one(self):
        for name in HOLDOUTS:
            with self.subTest(file=name):
                _, stats, wrong = score(name)
                self.assertLessEqual(stats["name"]["confident_wrong"], 1, wrong)

    def test_reported_floors(self):
        """Non-blocking floors from D10, asserted so a regression is visible."""
        for name in HOLDOUTS:
            n, stats, _ = score(name)
            self.assertGreaterEqual(stats["phone"]["correct"] / n, 0.9)
            self.assertGreaterEqual(stats["governorate"]["correct"] / n, 0.8)


if __name__ == "__main__":
    if "--report" in sys.argv:
        for name in HOLDOUTS:
            n, stats, wrong = score(name)
            print("%s: %d cases" % (name, n))
            for f, st in stats.items():
                print("  %-12s %s" % (f, "  ".join("%s=%d" % kv for kv in st.items())))
            for w in wrong:
                print("  confident-wrong:", w)
    else:
        unittest.main()
