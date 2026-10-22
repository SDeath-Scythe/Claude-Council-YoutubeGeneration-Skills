"""Council dev cases through the shared matcher (D11)."""
import json
import os
import unittest

import _helpers
from dallal_parser import parse_order
from dallal_parser.evalcases import check_case

DATA = os.path.join(_helpers.ROOT, "tests", "data")
# id -> reason.  Mirrored in README "Known limitations".
KNOWN_FAILURES = {}


class TestCases(unittest.TestCase):
    def _run_file(self, fname):
        with open(os.path.join(DATA, fname), encoding="utf-8") as fh:
            cases = json.load(fh)
        for c in cases:
            with self.subTest(id=c["id"]):
                bad = check_case(parse_order(c["input"]), c["expected"])
                if c["id"] in KNOWN_FAILURES:
                    continue
                self.assertEqual(bad, [], "%s: %r" % (c["id"], c["input"]))

    def test_dev_cases(self):
        self._run_file("dev_cases.json")

    def test_regression_cases(self):
        self._run_file("regression_cases.json")


if __name__ == "__main__":
    unittest.main()
