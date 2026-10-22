"""README must document exactly the schema keys, warning codes and reasons in the code."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dallal_parser import GOVERNORATES, INVALID_PHONE_REASONS, SCHEMA_KEYS, WARNING_CODES  # noqa: E402

README = os.path.join(os.path.dirname(__file__), "..", "README.md")


def _section(text, title):
    start = text.index(title)
    nxt = re.search(r"\n#{2,3} ", text[start + len(title):])
    return text[start:start + len(title) + (nxt.start() if nxt else len(text))]


class TestReadmeInSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(README, encoding="utf-8") as f:
            cls.text = f.read()

    def _table_keys(self, title):
        return re.findall(r"^\| `([a-z_]+)` \|", _section(self.text, title), re.M)

    def test_schema_table(self):
        self.assertEqual(tuple(self._table_keys("## Output schema")), SCHEMA_KEYS)

    def test_warning_table(self):
        self.assertEqual(tuple(self._table_keys("### Warning codes")), WARNING_CODES)

    def test_reasons_and_governorates_listed(self):
        for r in INVALID_PHONE_REASONS:
            self.assertIn("`%s`" % r, self.text)
        for g in GOVERNORATES:
            self.assertIn(g, self.text)


if __name__ == "__main__":
    unittest.main()
