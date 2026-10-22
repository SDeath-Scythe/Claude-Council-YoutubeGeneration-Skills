"""D9: follow-up message templates and invariants."""
import unittest

import _helpers  # noqa: F401
from dallal_parser import parse_order
from dallal_parser.followup import OPENER, CLOSER, TEMPLATES


class TestFollowup(unittest.TestCase):
    def test_complete_order_has_no_followup(self):
        r = parse_order("الاسم: علي حسين\nالرقم: 07701234567\nبغداد الكرادة قرب جامع الرحمن")
        self.assertFalse(r["needs_review"])
        self.assertIsNone(r["followup_ar"])

    def test_missing_fields_in_order(self):
        r = parse_order("")
        f = r["followup_ar"]
        self.assertTrue(f.startswith(OPENER) and f.endswith(CLOSER))
        order = [TEMPLATES[k] for k in ("phone_missing", "governorate_missing",
                                        "address_missing", "name_missing")]
        pos = [f.index(t) for t in order]
        self.assertEqual(pos, sorted(pos))

    def test_phone_templates(self):
        self.assertIn(TEMPLATES["phone_invalid"], parse_order("علي 0770123456 بغداد الكرادة")["followup_ar"])
        self.assertIn(TEMPLATES["phone_foreign"],
                      parse_order("علي +44 7700 900123 بغداد الكرادة")["followup_ar"])
        self.assertIn(TEMPLATES["phone_missing"], parse_order("علي بغداد الكرادة")["followup_ar"])

    def test_governorate_choice(self):
        f = parse_order("ابو حيدر 07701234567 البصرة او ميسان حي الحسين")["followup_ar"]
        self.assertIn("البصرة", f)
        self.assertIn("ميسان", f)

    def test_invariant(self):
        for raw in ["", "مرحبا", "علي 07701234567 بغداد الكرادة", "07701234567",
                    "علي 07701234567 بغداد الزبير", "x"]:
            r = parse_order(raw)
            self.assertEqual(r["followup_ar"] is None, not r["needs_review"])


if __name__ == "__main__":
    unittest.main()
