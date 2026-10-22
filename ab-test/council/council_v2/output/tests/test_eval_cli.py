"""D11: the eval CLI contract."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import _helpers

CLI = os.path.join(_helpers.ROOT, "eval_cases.py")


def run(cases, *flags):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(cases, fh, ensure_ascii=False)
        path = fh.name
    try:
        return subprocess.run([sys.executable, CLI, *flags, path], capture_output=True,
                              text=True, encoding="utf-8")
    finally:
        os.unlink(path)


class TestEvalCli(unittest.TestCase):
    def test_raw_mode(self):
        p = run([{"id": "a", "input": "علي 07701234567 بغداد الكرادة"}, {"id": 2, "input": ""}])
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertEqual([o["id"] for o in out], ["a", 2])
        self.assertEqual(out[0]["output"]["phone"], "+9647701234567")
        self.assertEqual(out[0]["output"]["governorate"], "Baghdad")

    def test_scored_mode(self):
        ok = run([{"id": "a", "input": "علي 07701234567 بغداد الكرادة",
                   "expected": {"governorate": "Baghdad", "address": "~الكرادة"}}])
        self.assertEqual(ok.returncode, 0)
        bad = run([{"id": "a", "input": "علي", "expected": {"phone": "+9647701234567"}}])
        self.assertEqual(bad.returncode, 1)
        self.assertIn("FAIL", bad.stdout)

    def test_force_raw(self):
        p = run([{"id": "a", "input": "x", "expected": {"name": None}}], "--raw")
        self.assertEqual(json.loads(p.stdout)[0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
