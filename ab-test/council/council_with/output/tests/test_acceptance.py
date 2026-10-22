"""Acceptance tests: charter AT1-AT9 and the council's AT10-AT26 (.council/DECISIONS.md)."""

import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dallal_parser import GOVERNORATES, SCHEMA_KEYS, parse_order  # noqa: E402

P = "+9647701234567"


def codes(r):
    return [w["code"] for w in r["warnings"]]


class TestAT1PhoneFormats(unittest.TestCase):
    def test_all_forms_normalise(self):
        for raw in [
            "07701234567", "٠٧٧٠١٢٣٤٥٦٧", "۰۷۷۰۱۲۳۴۵۶۷", "+964 770 123 4567", "00964-770-123-4567",
            "9647701234567", "7701234567", "0770 123 4567",
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_order(raw)["phone"], P)


class TestAT2ArabicLabelled(unittest.TestCase):
    def test(self):
        r = parse_order("الاسم: علي حسين\nالرقم: 07801234567\nالمحافظة: بغداد\nالعنوان: الكرادة قرب جامع براثا")
        self.assertEqual(r["name"], "علي حسين")
        self.assertEqual(r["phone"], "+9647801234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIn("الكرادة", r["address"])
        self.assertEqual(r["missing"], [])
        self.assertFalse(r["needs_followup"])


class TestAT3Unlabelled(unittest.TestCase):
    def test(self):
        r = parse_order("محمد جاسم\nالبصرة الجزائر قرب مول البصرة\n07712345678")
        self.assertEqual(r["name"], "محمد جاسم")
        self.assertEqual(r["governorate"], "Basra")
        self.assertEqual(r["phone"], "+9647712345678")
        self.assertIn("الجزائر", r["address"])
        self.assertNotIn("multiple_governorates", codes(r))


class TestAT4English(unittest.TestCase):
    def test(self):
        r = parse_order("name: Ahmed Kareem, phone 0750 123 4567, erbil, 100m street near family mall")
        self.assertEqual(r["governorate"], "Erbil")
        self.assertEqual(r["phone"], "+9647501234567")
        self.assertEqual(r["name"], "Ahmed Kareem")
        self.assertIn("100m", r["address"])


class TestAT5Aliases(unittest.TestCase):
    PAIRS = [
        (["نجف", "النجف"], "Najaf"), (["ذي قار", "الناصرية"], "Dhi Qar"), (["نينوى", "الموصل"], "Nineveh"),
        (["اربيل", "أربيل", "هولير"], "Erbil"), (["السليمانية", "سليمانية"], "Sulaymaniyah"),
        (["الديوانية", "القادسية"], "Qadisiyah"), (["الكوت", "واسط"], "Wasit"), (["الحلة", "بابل"], "Babil"),
        (["الرمادي", "الانبار"], "Anbar"), (["كربلاء", "كربلا"], "Karbala"), (["basra", "basrah"], "Basra"),
        (["nasiriyah"], "Dhi Qar"),
    ]

    def test_embedded_in_message(self):
        for aliases, gov in self.PAIRS:
            for a in aliases:
                with self.subTest(alias=a):
                    r = parse_order("علي حسن\n%s حي الحسين\n07701234567" % a)
                    self.assertEqual(r["governorate"], gov)
                    self.assertEqual(r["name"], "علي حسن")

    def test_alone_as_governorate_line(self):
        for line, gov in [
            ("هولير عنكاوة", "Erbil"), ("زاخو", "Duhok"), ("الزبير", "Basra"), ("الكوفة", "Najaf"),
            ("العمارة", "Maysan"), ("السماوة", "Muthanna"), ("بعقوبة", "Diyala"), ("تكريت", "Saladin"),
            ("الفلوجة", "Anbar"), ("حلبجة", "Halabja"), ("كركوك", "Kirkuk"), ("دهوك", "Duhok"),
        ]:
            with self.subTest(line=line):
                self.assertEqual(parse_order("علي حسن\n%s\n07701234567" % line)["governorate"], gov)


class TestAT6NeverInvent(unittest.TestCase):
    def test_no_phone(self):
        r = parse_order("علي\nبغداد الكرادة")
        self.assertIsNone(r["phone"])
        self.assertIn("phone", r["missing"])
        self.assertTrue(r["needs_followup"])

    def test_invalid_numbers_not_returned(self):
        for raw, reason in [("0123456", "not_mobile"), ("+971501234567", "foreign"), ("+962791234567", "foreign"),
                            ("040123456", "not_mobile"), ("07401234567", "unknown_prefix")]:
            with self.subTest(raw=raw):
                r = parse_order("احمد\nبغداد\n" + raw)
                self.assertIsNone(r["phone"])
                self.assertEqual(r["phones"], [])
                self.assertIn("invalid_phone", codes(r))
                self.assertEqual(r["invalid_phones"][0]["reason"], reason)


class TestAT7Robustness(unittest.TestCase):
    def test_junk_never_crashes(self):
        for text in ["", "   ", "😍🔥❤️", "x" * 10240, "‏‎", "٠" * 500, "\n\n\n", "::::", "- - -"]:
            with self.subTest(text=text[:20]):
                r = parse_order(text)
                self.assertEqual(set(r), set(SCHEMA_KEYS))
                json.dumps(r, ensure_ascii=False)

    def test_type_errors(self):
        for bad in (12345, b"bytes", ["list"]):
            with self.assertRaises(TypeError):
                parse_order(bad)

    def test_none_is_empty(self):
        r = parse_order(None)
        self.assertEqual(r["missing"], ["name", "phone", "governorate", "address"])
        self.assertIn("empty_input", codes(r))

    def test_speed(self):
        msg = "محمد جاسم\nالبصرة الجزائر قرب مول البصرة\n07712345678"
        t = time.perf_counter()
        for _ in range(300):
            parse_order(msg)
        mean_ms = (time.perf_counter() - t) / 300 * 1000
        self.assertLess(mean_ms, 50)
        t = time.perf_counter()
        parse_order(("0 0 0 بغداد قرب " * 800)[:10240])
        self.assertLess(time.perf_counter() - t, 0.5)  # 10 KB worst case (truncated to 4,000 chars)


class TestAT8Ambiguity(unittest.TestCase):
    def test_two_phones(self):
        r = parse_order("زينب\n07701234567 او 07801234567\nكربلاء حي الحسين")
        self.assertEqual(r["phone"], P)
        self.assertEqual(r["phones"], [P, "+9647801234567"])
        self.assertIn("multiple_phones", codes(r))

    def test_same_number_twice_is_not_ambiguous(self):
        r = parse_order("علي\nاربيل\n07501234567 ٠٧٥٠١٢٣٤٥٦٧")
        self.assertEqual(r["phones"], ["+9647501234567"])
        self.assertNotIn("multiple_phones", codes(r))

    def test_two_governorates(self):
        r = parse_order("علي\nبغداد\nالنجف حي الامير\n07701234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertEqual(r["confidence"]["governorate"], "low")
        self.assertIn("multiple_governorates", codes(r))
        self.assertTrue(r["needs_followup"])

    def test_labelled_secondary_number(self):
        r = parse_order("الاسم: ام علي\nرقم ثاني: 07701234567\nالرقم: 07901234567\nالمحافظة: ميسان")
        self.assertEqual(r["name"], "ام علي")
        self.assertEqual(r["phone"], "+9647901234567")
        self.assertEqual(r["phones"], ["+9647901234567", P])
        self.assertEqual(r["governorate"], "Maysan")


class TestAT9StableSchema(unittest.TestCase):
    def test_keys_and_json(self):
        for text in ["", "علي", "07701234567", "بغداد", "name: x\nphone: 0770"]:
            r = parse_order(text)
            self.assertEqual(tuple(r), SCHEMA_KEYS)
            self.assertEqual(json.loads(json.dumps(r, ensure_ascii=False)), r)
            for f in ("name", "phone", "governorate", "address"):
                self.assertEqual(r[f] is None, f in r["missing"])
            if r["governorate"]:
                self.assertIn(r["governorate"], GOVERNORATES)


class TestAT10Nisba(unittest.TestCase):
    def test(self):
        r = parse_order("علي حسين البصري\nبغداد زيونة\n07701234567")
        self.assertEqual((r["governorate"], r["name"]), ("Baghdad", "علي حسين البصري"))
        r = parse_order("علي البغدادي\nالبصرة حي الجزائر\n07712345678")
        self.assertEqual((r["governorate"], r["name"]), ("Basra", "علي البغدادي"))
        r = parse_order("مصطفى النجفي\nكربلاء حي الحسين\n07801234567")
        self.assertEqual((r["governorate"], r["name"]), ("Karbala", "مصطفى النجفي"))
        r = parse_order("حجي كربلائي جواد\nالحلة حي بابل\n07501234567")
        self.assertEqual(r["governorate"], "Babil")
        self.assertIn("كربلائي", r["name"])


class TestAT11References(unittest.TestCase):
    def test(self):
        for text, gov in [
            ("زينب كاظم\nبغداد الكرادة قرب كراج النجف\n07712345678", "Baghdad"),
            ("حسن كاظم\nالبصرة شارع بغداد قرب الجسر\n07712345678", "Basra"),
            ("حسن كريم\nبغداد حي بابل\n07901234567", "Baghdad"),
            ("حسين علي\nكربلاء حي العباس قرب شارع بغداد\n07901234567", "Karbala"),
            ("سارة\nبغداد الزعفرانية قرب جسر ديالى\n07701234567", "Baghdad"),
        ]:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertEqual(r["governorate"], gov)
                self.assertNotIn("multiple_governorates", codes(r))


class TestAT12WordCollisions(unittest.TestCase):
    def test(self):
        r = parse_order("اريد الكوت الاسود قياس XL\nزينب علي\nبغداد زيونة\n07701234567")
        self.assertEqual((r["governorate"], r["name"]), ("Baghdad", "زينب علي"))
        r = parse_order("سارة احمد\nبغداد المنصور عمارة 5 الطابق الثاني\n07901234567")
        self.assertEqual(r["governorate"], "Baghdad")


class TestAT13Noise(unittest.TestCase):
    def test(self):
        r = parse_order("السلام عليكم 🌹\nاريد القطعة السودة قياس L\nفاطمة جاسم\nالناصرية الشطرة قرب المستشفى\n"
                        "07801234567\nشكرا")
        self.assertEqual(r["name"], "فاطمة جاسم")
        self.assertEqual(r["confidence"]["name"], "high")
        self.assertNotIn("name_uncertain", codes(r))
        self.assertEqual(r["governorate"], "Dhi Qar")
        self.assertNotIn("قياس", r["address"])
        self.assertTrue(any("قياس" in n for n in r["notes"]))


class TestAT14NoFabrication(unittest.TestCase):
    def test_rejected(self):
        for raw, reason in [("0770123456 7", "ambiguous_grouping"), ("077012345678", "too_long"),
                            ("0770123456", "too_short")]:
            with self.subTest(raw=raw):
                r = parse_order("علي حسين\nبغداد\n" + raw)
                self.assertIsNone(r["phone"])
                self.assertEqual(r["invalid_phones"][0]["reason"], reason)
                self.assertIn("phone", r["missing"])

    def test_accepted(self):
        for raw in ["+964 0770 123 4567", "009640770-123-4567", "‏+964 770 123 4567‏", "07701234567+",
                    "٠٧٧٠۱۲۳٤٥٦٧", "رقمي07701234567", "‏0770 123‎4567", "770 123 4567",
                    "+964 7701234567", "00964 07701234567"]:
            with self.subTest(raw=raw):
                r = parse_order("زينب\nكربلا حي الحسين\n" + raw)
                self.assertEqual(r["phone"], P)
                self.assertTrue(r["phone"].isascii())
                self.assertNotIn("phone_adjacent_digits", codes(r))


class TestAT15AddressNumbers(unittest.TestCase):
    def test(self):
        r = parse_order("بغداد الدورة محلة 906 زقاق 12 دار 7\nالسعر 25000\n07701234567")
        self.assertEqual(r["phones"], [P])
        self.assertIn("محلة 906 زقاق 12 دار 7", r["address"])
        r = parse_order("سارة\nبغداد شارع فلسطين زقاق 7 دار 75\n07701234567")
        self.assertEqual(r["phones"], [P])
        self.assertIn("دار 75", r["address"])
        r = parse_order("محمد علي\nبغداد حي العامل محلة 770 زقاق 12 دار 34567\n07801234567")
        self.assertEqual(r["phones"], ["+9647801234567"])


class TestAT16KurdishArabizi(unittest.TestCase):
    def test(self):
        r = parse_order("ئاراس\nسلێمانی بەختیاری\n۰۷۵۰۱۲۳۴۵۶۷")
        self.assertEqual((r["governorate"], r["phone"]), ("Sulaymaniyah", "+9647501234567"))
        for word, gov in [("هەولێر", "Erbil"), ("کەرکووک", "Kirkuk"), ("دهۆک", "Duhok"), ("هەڵەبجە", "Halabja")]:
            with self.subTest(word=word):
                self.assertEqual(parse_order("کاروان عمر\n%s\n0750 123 4567" % word)["governorate"], gov)
        r = parse_order("3li 7sen\nbaghdad / zayona\n07701234567")
        self.assertEqual((r["name"], r["governorate"], r["phone"]), ("3li 7sen", "Baghdad", P))
        r = parse_order("slm 3likum, ana 3li kareem, slemani, bakhtiari near family mall, 0770-123-4567")
        self.assertEqual((r["governorate"], r["phone"]), ("Sulaymaniyah", P))
        self.assertEqual(r["name"], "3li kareem")
        self.assertNotIn("multiple_governorates", codes(r))


class TestAT17DistrictInference(unittest.TestCase):
    def test(self):
        r = parse_order("مرحبا\nالكرادة داخل قرب ساحة الحرية\n07701234567")
        self.assertIsNone(r["name"])
        self.assertEqual((r["governorate"], r["governorate_source"]), ("Baghdad", "district"))
        self.assertEqual(r["confidence"]["governorate"], "low")
        self.assertIn("governorate_inferred", codes(r))
        self.assertTrue(r["needs_followup"])
        r = parse_order("حسن علي\nحي الجمهورية قرب الجامع\n07712345678")
        self.assertIsNone(r["governorate"])
        self.assertIn("governorate", r["missing"])


class TestAT18Labels(unittest.TestCase):
    def test_full_label_and_spelling_kept(self):
        r = parse_order("الاسم الثلاثي: أسامة عبد الكريم جاسم\nالرقم: ٠٧٧٠١٢٣٤٥٦٧\nالمحافظة: الانبار\n"
                        "العنوان: الرمادي حي التأميم")
        self.assertEqual(r["name"], "أسامة عبد الكريم جاسم")
        self.assertEqual(r["governorate"], "Anbar")
        self.assertEqual(r["phone"], P)

    def test_values_on_next_line(self):
        r = parse_order("الاسم:\nعلي حسين\nالرقم:\n07801234567\nالمحافظة:\nالنجف\nاقرب نقطة دالة: مستشفى الصدر")
        self.assertEqual((r["name"], r["governorate"]), ("علي حسين", "Najaf"))
        self.assertIn("مستشفى الصدر", r["address"])
        self.assertEqual(r["landmark"], "مستشفى الصدر")

    def test_label_wins_with_conflict_warning(self):
        r = parse_order("المحافظة: كربلاء\nالعنوان: النجف شارع الكوفة")
        self.assertEqual(r["governorate"], "Karbala")
        self.assertEqual(r["governorate_source"], "label")
        self.assertIn("multiple_governorates", codes(r))


class TestAT19SingleLine(unittest.TestCase):
    def test(self):
        r = parse_order("علي حسين بغداد الكرادة 07701234567")
        self.assertEqual((r["name"], r["governorate"], r["phone"]), ("علي حسين", "Baghdad", P))
        self.assertIn("الكرادة", r["address"])
        r = parse_order("ام حسين، الديوانية حي العسكري، ٠٧٨٠١٢٣٤٥٦٧")
        self.assertEqual((r["name"], r["governorate"], r["phone"]), ("ام حسين", "Qadisiyah", "+9647801234567"))


class TestAT20GovernorateOnlyAddress(unittest.TestCase):
    def test(self):
        r = parse_order("احمد\nبغداد\n07701234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertIsNone(r["address"])
        self.assertIn("address", r["missing"])
        self.assertTrue(r["needs_followup"])


class TestAT22NameCollisions(unittest.TestCase):
    def test(self):
        cases = [
            ("مثنى حسين\nالكرادة قرب ساحة الحرية\n07701234567", "مثنى حسين", "Baghdad"),
            ("ميسان علي\nبغداد المنصور\n07801234567", "ميسان علي", "Baghdad"),
            ("حمزة كاظم\nالكرادة داخل\n07701234567", "حمزة كاظم", "Baghdad"),
            ("علي حسين الرفاعي\nبغداد زيونة\n07701234567", "علي حسين الرفاعي", "Baghdad"),
            ("حسين عبد الخضر\nبغداد الشعلة\n07701234567", "حسين عبد الخضر", "Baghdad"),
            ("علي عبد الحمزة\nالبصرة الجزائر\n07712345678", "علي عبد الحمزة", "Basra"),
            ("قاسم محمد\nالنجف حي الامير\n07801234567", "قاسم محمد", "Najaf"),
            ("حمزة علي\nالبصرة الجزائر\n07712345678", "حمزة علي", "Basra"),
            ("مثنى حسين بغداد الكرادة 07701234567", "مثنى حسين", "Baghdad"),
            ("ميسان علي بغداد المنصور 07801234567", "ميسان علي", "Baghdad"),
            ("حمزة علي البصرة الجزائر ٠٧٧١٢٣٤٥٦٧٨", "حمزة علي", "Basra"),
            ("ديالا حسن\nبغداد زيونة\n07701234567", "ديالا حسن", "Baghdad"),
        ]
        for text, name, gov in cases:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertEqual(r["name"], name)
                self.assertEqual(r["governorate"], gov)
                self.assertNotIn("multiple_governorates", codes(r))

    def test_yarmouk_is_not_baghdad(self):
        self.assertIsNone(parse_order("حي اليرموك قرب الجامع\n07701234567")["governorate"])

    def test_collision_place_in_strong_position(self):
        r = parse_order("ميسان العمارة قرب الجسر\n07701234567")
        self.assertEqual(r["governorate"], "Maysan")
        r = parse_order("زهراء عادل الزبير حي الرسالة 07802334455")
        self.assertEqual((r["name"], r["governorate"]), ("زهراء عادل", "Basra"))
        self.assertEqual(r["confidence"]["governorate"], "low")

    def test_single_first_name_is_not_a_place(self):
        r = parse_order("مثنى\nالكرادة قرب ساحة الحرية\n07701234567")
        self.assertEqual(r["name"], "مثنى")
        self.assertNotEqual(r["governorate"], "Muthanna")


class TestAT23Acknowledgements(unittest.TestCase):
    def test(self):
        for first in ["صباح الخير", "تمام", "هلا اخي", "زين", "اوكي"]:
            with self.subTest(first=first):
                r = parse_order("%s\nعلي حسين\nبغداد زيونة\n07701234567" % first)
                self.assertEqual(r["name"], "علي حسين")
        self.assertIsNone(parse_order("اوك\nبغداد الكرادة\n07701234567")["name"])

    def test_greeting_words_that_are_names(self):
        for text, name in [
            ("هلا محمد كاظم\nبغداد زيونة\n07701234567", "هلا محمد كاظم"),
            ("زين العابدين علي\nبغداد زيونة\n07701234567", "زين العابدين علي"),
            ("سلام كريم\nالبصرة الجزائر\n07712345678", "سلام كريم"),
            ("salam ali\nbaghdad zayona\n07701234567", "salam ali"),
            ("زين علي\nبغداد زيونة\n07701234567", "زين علي"),
            ("هلا كاظم\nالبصرة الجزائر\n07712345678", "هلا كاظم"),
            ("فاطمة 🌸\nبغداد زيونة\n07701234567", "فاطمة"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_order(text)["name"], name)


class TestAT24PhoneGrouping(unittest.TestCase):
    def test(self):
        r = parse_order("علي\nبغداد\n0770 123 4567 8")
        self.assertIsNone(r["phone"])
        self.assertEqual(r["invalid_phones"][0]["reason"], "ambiguous_grouping")
        r = parse_order("علي\nبغداد\n07701234567 2")
        self.assertEqual((r["phone"], r["confidence"]["phone"]), (P, "medium"))
        self.assertIn("phone_adjacent_digits", codes(r))
        r = parse_order("علي\nبغداد دار 75 0770 123 4567")
        self.assertEqual(r["phones"], [P])
        self.assertNotIn("phone_adjacent_digits", codes(r))
        self.assertEqual(parse_order("mob07701234567")["phone"], P)
        self.assertEqual(parse_order("علي بغداد الكرادة 0770 123 4567 25000")["phone"], P)
        r = parse_order("زينب\nبغداد الدورة رقم الدار 12\n07701234567")
        self.assertEqual(r["phones"], [P])
        self.assertIn("رقم الدار 12", r["address"])

    def test_quantities_next_to_phone(self):
        for text in ["عدد 2 0770 123 4567", "قياس 42 0770 123 4567"]:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertEqual(r["phone"], P)
                self.assertNotIn("phone_adjacent_digits", codes(r))
        r = parse_order("اريد 2 0770 123 4567")
        self.assertEqual((r["phone"], r["confidence"]["phone"]), (P, "medium"))


class TestAT25LabelsWithArea(unittest.TestCase):
    def test(self):
        r = parse_order("المحافظة: البصرة الجزائر\nالرقم: 07712345678\nالاسم: نور علي")
        self.assertEqual((r["governorate"], r["name"]), ("Basra", "نور علي"))
        self.assertIn("الجزائر", r["address"])
        self.assertNotIn("address", r["missing"])
        r = parse_order("علي\nبغداد الجديدة قرب سوق\n07701234567")
        self.assertEqual((r["governorate"], r["governorate_source"]), ("Baghdad", "explicit"))
        self.assertIn("بغداد الجديدة", r["address"])
        self.assertEqual(parse_order("هەولێر")["governorate"], "Erbil")
        self.assertEqual(parse_order("کەرکووک")["governorate"], "Kirkuk")


class TestAT26CommonWordsAndNamePosition(unittest.TestCase):
    def test_grey_is_not_ramadi(self):
        r = parse_order("اريد الجاكيت الرمادي قياس XL\nزينب علي\nحي الجامعة قرب الجامع\n07701234567")
        self.assertIsNone(r["governorate"])
        r = parse_order("لون رمادي\nسارة علي\nبغداد زيونة\n07701234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertNotIn("multiple_governorates", codes(r))

    def test_surname_equal_to_city(self):
        r = parse_order("عمر خالد الرمادي\nحي الجامعة قرب جامع الحسن\n07701234567")
        self.assertTrue(r["needs_followup"])
        self.assertFalse(r["governorate"] == "Anbar" and r["confidence"]["governorate"] in ("high", "medium"))
        r = parse_order("عمر خالد الدليمي\nالرمادي حي الضباط\n07701234567")
        self.assertEqual((r["governorate"], r["confidence"]["governorate"]), ("Anbar", "high"))


class TestIntroMarkers(unittest.TestCase):
    def test(self):
        for text in ["I'm Lana Aziz\nerbil ankawa near the church\n07501234567",
                     "my name is Lana Aziz, erbil ankawa near the church, 07501234567",
                     "اني لانا عزيز\nاربيل عنكاوة قرب الكنيسة\n07501234567"]:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertIn(r["name"], ("Lana Aziz", "لانا عزيز"))
                self.assertEqual(r["governorate"], "Erbil")


class TestJoinedMessages(unittest.TestCase):
    def test_three_dms_joined(self):
        dms = ["علي كاظم", "٠٧٨٠ ١٢٣ ٤٥٦٧", "النجف حي الامير قرب جامع الامير"]
        r = parse_order("\n".join(dms))
        self.assertEqual(r["missing"], [])
        self.assertEqual((r["name"], r["phone"], r["governorate"]), ("علي كاظم", "+9647801234567", "Najaf"))


class TestAT27ReviewRegressions(unittest.TestCase):
    """Findings from council review pass 1 (.council/findings): each input once failed."""

    def test_labelled_or_intro_name_never_swallows_the_place(self):  # F1, F2
        r = parse_order("الاسم: علي حسين بغداد الكرادة\n07701234567")
        self.assertEqual((r["name"], r["governorate"]), ("علي حسين", "Baghdad"))
        r = parse_order("I'm Ahmed from Najaf\n07801234567\nkufa street near the mosque")
        self.assertEqual((r["name"], r["governorate"]), ("Ahmed", "Najaf"))
        r = parse_order("اريد الطلب اسمي مرتضى جبار من الديوانية حي العسكري")  # F29
        self.assertEqual((r["name"], r["governorate"]), ("مرتضى جبار", "Qadisiyah"))

    def test_label_word_never_becomes_the_name(self):  # F21, F22, F26
        r = parse_order("الاسم الثلاثي: مُحَمَّد عَلِيّ حسن\nبغداد الكرادة قرب كهرمانة\n07701234567")
        self.assertEqual(r["name"], "مُحَمَّد عَلِيّ حسن")
        self.assertEqual(parse_order("محمّد علي\nبغداد الكرادة قرب كهرمانة\n07701234567")["name"], "محمّد علي")
        r = parse_order("المحافظة: مدري\nعلي حسين\nبغداد الكرادة قرب كهرمانة\n07701234567")
        self.assertEqual(r["name"], "علي حسين")

    def test_english_landmark_after_place_is_a_reference(self):  # F23
        r = parse_order("name: Ahmed Ali\naddress: Mansour near Babil hotel\nphone: 07701234567")
        self.assertFalse(r["governorate"] == "Babil" and r["confidence"]["governorate"] in ("high", "medium"))
        self.assertTrue(r["needs_followup"])

    def test_intro_words_do_not_bind_chatter(self):  # F8
        for text in ["علي حسن\nاني مستعجل\nبغداد الكرادة قرب ساحة كهرمانة\n07701234567",
                     "im busy\nali hassan\nbaghdad karrada near church\n07701234567"]:
            with self.subTest(text=text):
                self.assertIn(parse_order(text)["name"], ("علي حسن", "ali hassan"))

    def test_city_word_is_not_a_label(self):  # F10
        r = parse_order("علي حسن\nمدينة العامرية قرب السوق\n07701234567")
        self.assertNotEqual(r["governorate_source"], "label")
        self.assertIn("العامرية", r["address"])

    def test_place_names_beat_product_words(self):  # F11
        r = parse_order("علي حسن\nالبصرة ابي الخصيب قرب جامع\n07701234567")
        self.assertEqual(r["governorate"], "Basra")
        self.assertIn("ابي الخصيب", r["address"])

    def test_chatter_and_instructions_are_not_names(self):  # F15, F24, F31, F30, F3
        for first in ["ان شاء الله", "وين صار طلبي", "باجر", "send to my sister mariam", "دزوه لاختي مريم"]:
            with self.subTest(first=first):
                r = parse_order("%s\nبغداد الكرادة قرب كهرمانة\n07701234567" % first)
                self.assertIsNone(r["name"])
                self.assertTrue(r["needs_followup"])
        self.assertEqual(parse_order("مرتضى جبار وشكرا")["name"], "مرتضى جبار")
        r = parse_order("07701234567 و 07801234567\nعلي حسين\nالبصرة الجزائر")
        self.assertEqual(r["name"], "علي حسين")

    def test_chatter_after_governorate_is_not_an_address(self):  # F9
        r = parse_order("علي حسن\nكربلاء\nان شاء الله\n07701234567")
        self.assertIsNone(r["address"])
        self.assertTrue(r["needs_followup"])

    def test_phone_correction_wins(self):  # F25
        r = parse_order("علي حسين\nبغداد الكرادة قرب كهرمانة\n07701234567\nعفوا غلط الرقم الصحيح 07801234567")
        self.assertEqual(r["phone"], "+9647801234567")
        self.assertIn("multiple_phones", codes(r))

    def test_someone_elses_number_is_secondary(self):
        r = parse_order("علي\nبغداد الكرادة / رقم ابني 07801234567 واتساب\n07701234567")
        self.assertEqual(r["phone"], P)
        self.assertEqual(r["address"], "الكرادة")  # F18/F5: no 'رقم ابني' / 'واتساب' in the address

    def test_normalize_phone_follows_grouping_rules(self):  # F32
        from dallal_parser import normalize_phone
        self.assertIsNone(normalize_phone("0770123456 7"))
        self.assertEqual(normalize_phone("(0770) 123-4567"), P)

    def test_gazetteer_additions(self):  # F12, F13, F17
        for line, gov in [("ديالة", "Diyala"), ("نينوة", "Nineveh"), ("سفوان", "Basra"), ("بغداد باب المعظم", "Baghdad")]:
            with self.subTest(line=line):
                self.assertEqual(parse_order("علي حسن\n%s\n07701234567" % line)["governorate"], gov)
        self.assertNotIn("multiple_governorates", codes(parse_order("علي\nالانبار العامرية\n07701234567")))

class TestAT28ReviewPass2Regressions(unittest.TestCase):
    """Findings from council review pass 2."""

    def test_resent_order_is_deduplicated(self):
        r = parse_order("علي حسين\nبغداد الكرادة قرب السوق\n07701234567\n" * 2)
        self.assertEqual((r["name"], r["address"]), ("علي حسين", "الكرادة قرب السوق"))

    def test_one_line_labelled_template(self):
        for text in ["الاسم: علي حسين الرقم: 07801234567 المحافظة: بغداد العنوان: الكرادة قرب جامع براثا",
                     "الاسم علي حسين الرقم 07801234567 المحافظة بغداد العنوان الكرادة قرب جامع براثا"]:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertEqual((r["name"], r["governorate"]), ("علي حسين", "Baghdad"))
                self.assertEqual(r["address"], "الكرادة قرب جامع براثا")
        r = parse_order("name: ali hassan phone: 07701234567 city: basra address: ashar near the river")
        self.assertEqual((r["name"], r["governorate"], r["address"]), ("ali hassan", "Basra", "ashar near the river"))
        r = parse_order("الاسم حسين علي المحافظة كربلاء المنطقة حي العباس الرقم 07801234567")
        self.assertEqual(r["address"], "حي العباس")

    def test_chatter_after_address_is_not_address(self):
        for tail in ["الدفع عند الاستلام", "اتصل بعد الساعة 5", "الله يوفقكم"]:
            with self.subTest(tail=tail):
                r = parse_order("علي حسن\nبغداد\n%s\n07701234567" % tail)
                self.assertIsNone(r["address"])
                self.assertTrue(r["needs_followup"])
        r = parse_order("علي حسين\nبغداد الكرادة\n07812345678\nالدفع عند الاستلام")
        self.assertEqual(r["address"], "الكرادة")
        self.assertIn("address_short", codes(r))

    def test_redirect_to_another_governorate_is_flagged(self):
        r = parse_order("علي حسن\nبغداد الكرادة\nابعثوه لبيت اهلي بالنجف\n07701234567")
        self.assertIn("multiple_governorates", codes(r))
        self.assertTrue(r["needs_followup"])

    def test_intro_lines_with_places(self):
        r = parse_order("علي حسن\nاني ساكن بحي الجامعة قرب الجامع\n07701234567")
        self.assertIn("الجامعة", r["address"])
        for text, gov in [("اني بالكوت\nعلي حسن\n07701234567", "Wasit"),
                          ("اني من الكوت\nعلي حسن\n07701234567", "Wasit"),
                          ("ana mn basra\nali hassan\n07701234567", "Basra"),
                          ("اني ساكن بالكوت حي الحسين\nعلي حسن\n07701234567", "Wasit")]:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertIn(r["name"], ("علي حسن", "ali hassan"))
                self.assertEqual(r["governorate"], gov)

class TestAT29PositiveNameEvidence(unittest.TestCase):
    """Skeptic review pass 2: chatter / sizes must never be a confirmed name."""

    def test_lone_chatter_is_never_a_confident_name(self):
        for x in ["عليكم السلام", "جزاك الله خير", "الدفع عند الاستلام", "انطيني خصم", "فدوه الك", "اسود",
                  "احجزلي", "inshallah", "بالله عليك", "شنو السعر الكلي", "2x", "42xl", "iphone13", "x2 black",
                  "size42", "100k", "A12"]:
            with self.subTest(x=x):
                r = parse_order(x + "\nبغداد الكرادة قرب مطعم\n07701234567")
                self.assertFalse(r["name"] and not r["needs_followup"], r["name"])

    def test_unknown_name_is_kept_but_confirmed(self):
        r = parse_order("زوزو كيكي\nبغداد الكرادة قرب مطعم\n07701234567")
        self.assertEqual(r["name"], "زوزو كيكي")
        self.assertEqual(r["confidence"]["name"], "low")
        self.assertIn("name_unverified", codes(r))
        self.assertTrue(r["needs_followup"])

    def test_arabizi_names_still_work(self):
        for text, name in [("3li 7sen\nbaghdad / zayona\n07701234567", "3li 7sen"),
                           ("m7md kareem\nbasra jazair near mall\n07701234567", "m7md kareem")]:
            with self.subTest(text=text):
                r = parse_order(text)
                self.assertEqual((r["name"], r["confidence"]["name"]), (name, "high"))

    def test_name_correction_wins(self):
        r = parse_order("علي حسين\nبغداد الكرادة قرب مطعم\n07701234567\nلا والله غلطت الاسم احمد كريم")
        self.assertEqual(r["name"], "احمد كريم")

    def test_delivery_line_with_a_place(self):
        r = parse_order("علي حسين\nبغداد\nتوصيل لبيت عمي بالكوت حي الزهراء\n07701234567")
        self.assertIn("multiple_governorates", codes(r))
        self.assertTrue(r["needs_followup"])
        r = parse_order("علي حسين\nالتوصيل للكوت حي الزهراء\n07701234567")
        self.assertEqual(r["governorate"], "Wasit")
        self.assertIn("حي الزهراء", r["address"])

if __name__ == "__main__":
    unittest.main()
