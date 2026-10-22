"""End-to-end tests on realistic DM messages."""

import unittest

from dallal_parser import GOVERNORATES, parse_order


class Base(unittest.TestCase):
    def assertOrder(self, text, **expected):
        result = parse_order(text)
        for key, value in expected.items():
            self.assertEqual(result[key], value, f"{key!r} for message:\n{text}\nresult: {result}")
        return result


class LabelledForms(Base):
    def test_arabic_labelled_multiline(self):
        r = self.assertOrder(
            "الاسم: زينب حسين\nالرقم: ٠٧٨١٢٣٤٥٦٧٨\nالمحافظة: البصرة\n"
            "العنوان: الزبير حي الشهداء قرب مدرسة الفارابي",
            name="زينب حسين",
            phone="+9647812345678",
            governorate="Basra",
            governorate_ar="البصرة",
            address="الزبير حي الشهداء قرب مدرسة الفارابي",
            landmark="قرب مدرسة الفارابي",
            missing=[],
            is_complete=True,
            needs_review=False,
        )
        self.assertEqual(r["confidence"]["name"], "high")

    def test_arabic_labelled_single_line_without_colons(self):
        self.assertOrder(
            "الاسم احمد المحافظة كربلاء العنوان حي الحسين قرب المستشفى الرقم 07712345678",
            name="احمد",
            phone="+9647712345678",
            governorate="Karbala",
            address="حي الحسين قرب المستشفى",
        )

    def test_english_labelled(self):
        self.assertOrder(
            "Name: Sara Ahmed\nPhone: +964 750 123 4567\nCity: Erbil\nAddress: Ankawa, near Family Mall",
            name="Sara Ahmed",
            phone="+9647501234567",
            governorate="Erbil",
            address="Ankawa - near Family Mall",
            landmark="near Family Mall",
        )

    def test_english_labelled_single_line(self):
        self.assertOrder(
            "name: omar khalid phone: 07901234567 city: basra address: ashar, near the corniche",
            name="Omar Khalid",
            phone="+9647901234567",
            governorate="Basra",
            address="ashar - near the corniche",
        )

    def test_landmark_label(self):
        self.assertOrder(
            "الاسم: حسين علي\n07701234567\nبغداد الشعلة\nاقرب نقطة دالة: جامع الشعلة الكبير",
            name="حسين علي",
            governorate="Baghdad",
            address="الشعلة - جامع الشعلة الكبير",
            landmark="جامع الشعلة الكبير",
        )

    def test_name_label_followed_by_place_on_same_line(self):
        self.assertOrder(
            "الاسم علي حسين بغداد الكرادة 07701234567",
            name="علي حسين",
            governorate="Baghdad",
            address="الكرادة",
        )

    def test_my_name_is(self):
        self.assertOrder(
            "اسمي فاطمة كريم\nالسليمانية\n٠٧٥٠-١٢٣-٤٥٦٧",
            name="فاطمة كريم",
            phone="+9647501234567",
            governorate="Sulaymaniyah",
            address=None,
            missing=["address"],
            needs_review=True,
        )


class UnlabelledForms(Base):
    def test_three_lines(self):
        self.assertOrder(
            "احمد علي\nبغداد الكرادة قرب جامع الرحمن\n0770 123 4567",
            name="احمد علي",
            phone="+9647701234567",
            governorate="Baghdad",
            address="الكرادة قرب جامع الرحمن",
            landmark="قرب جامع الرحمن",
            needs_review=False,
        )

    def test_everything_on_one_line(self):
        self.assertOrder(
            "السلام عليكم اني حيدر كاظم من بغداد زيونة شارع الربيعي 07901234567",
            name="حيدر كاظم",
            phone="+9647901234567",
            governorate="Baghdad",
            address="زيونة شارع الربيعي",
        )

    def test_dash_separated(self):
        self.assertOrder(
            "مصطفى - ذي قار - الناصرية - قرب ساحة الحبوبي - 9647812345678",
            name="مصطفى",
            phone="+9647812345678",
            governorate="Dhi Qar",
            address="الناصرية - قرب ساحة الحبوبي",
        )

    def test_slash_separated_address(self):
        self.assertOrder(
            "علي حسن\nبغداد/الاعظمية/قرب ساحة عنتر\n07701234567",
            governorate="Baghdad",
            address="الاعظمية - قرب ساحة عنتر",
            landmark="قرب ساحة عنتر",
        )

    def test_address_first_name_last(self):
        self.assertOrder(
            "بغداد الكرادة داخل\nعلي حسين\n07701234567",
            name="علي حسين",
            governorate="Baghdad",
            address="الكرادة داخل",
        )

    def test_name_and_phone_on_one_line(self):
        self.assertOrder(
            "رقم الدار 12 زقاق 5\nبغداد حي الجهاد\nعلي حسين 07701234567",
            name="علي حسين",
            phone="+9647701234567",
            governorate="Baghdad",
            address="رقم الدار 12 زقاق 5 - حي الجهاد",
        )

    def test_english_unlabelled(self):
        self.assertOrder(
            "Hussein Ali, Karbala, Hay Al-Askari, near Al-Hussein hospital, 07812345678",
            name="Hussein Ali",
            phone="+9647812345678",
            governorate="Karbala",
            address="Hay Al-Askari - near Al-Hussein hospital",
        )

    def test_english_sentence(self):
        self.assertOrder(
            "hi i want to order. my name is ali hassan, i live in najaf, al-ameer neighborhood "
            "near the hospital, 07801234567",
            name="Ali Hassan",
            phone="+9647801234567",
            governorate="Najaf",
            address="al-ameer neighborhood near the hospital",
            notes="i want to order",
        )

    def test_mixed_arabic_english(self):
        self.assertOrder(
            "Mustafa Kareem\nالبصرة العشار near the corniche\n0780 123 4567",
            name="Mustafa Kareem",
            governorate="Basra",
            address="العشار near the corniche",
        )

    def test_greeting_and_product_notes(self):
        self.assertOrder(
            "مرحبا\nمحمد جاسم\nالموصل حي الزهور مقابل جامع الزهور\n07711112222\n"
            "اريد القطعة السودة قياس L",
            name="محمد جاسم",
            governorate="Nineveh",
            address="الموصل حي الزهور مقابل جامع الزهور",
            notes="اريد القطعة السودة قياس L",
        )

    def test_emoji(self):
        self.assertOrder(
            "👤 نور الهدى\n📍 النجف حي الأنصار\n📞 07801234567 ❤️",
            name="نور الهدى",
            governorate="Najaf",
            address="حي الأنصار",
            phone="+9647801234567",
        )

    def test_kurdish(self):
        self.assertOrder(
            "ناوم: هیوا ئەحمەد\nهەولێر، گەڕەکی ئازادی\n0750 111 2233",
            name="هیوا ئەحمەد",
            governorate="Erbil",
            address="گەڕەکی ئازادی",
            phone="+9647501112233",
        )


class Governorates(Base):
    def test_city_infers_governorate_and_stays_in_address(self):
        r = self.assertOrder("علي حسين\nالموصل حي الزهور\n07701234567",
                             governorate="Nineveh", address="الموصل حي الزهور")
        self.assertEqual(r["confidence"]["governorate"], "medium")

    def test_neighbourhood_infers_baghdad(self):
        r = self.assertOrder("علي حسين\nالكرادة قرب ساحة كهرمانة\n07701234567",
                             governorate="Baghdad", address="الكرادة قرب ساحة كهرمانة")
        self.assertEqual(r["confidence"]["governorate"], "medium")

    def test_governorate_word_is_removed(self):
        self.assertOrder("زينب علي\nمحافظة ديالى بعقوبة حي المعلمين\n07701234567",
                         governorate="Diyala", address="بعقوبة حي المعلمين")

    def test_attached_prepositions(self):
        for text, gov in [
            ("ساكن ببغداد حي العدل", "Baghdad"),
            ("بالبصرة الجبيلة", "Basra"),
            ("من كربلاء حي النقيب", "Karbala"),
            ("وبالنجف قرب الحرم", "Najaf"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_order(text)["governorate"], gov)

    def test_spelling_variants(self):
        for text, gov in [
            ("البصره", "Basra"), ("basrah", "Basra"), ("Mosul", "Nineveh"), ("نينوى", "Nineveh"),
            ("hawler", "Erbil"), ("أربيل", "Erbil"), ("Slemani", "Sulaymaniyah"),
            ("دهوك", "Duhok"), ("Dohuk", "Duhok"), ("حلبجة", "Halabja"), ("Kirkuk", "Kirkuk"),
            ("ديالى", "Diyala"), ("الانبار", "Anbar"), ("الرمادي", "Anbar"), ("الفلوجة", "Anbar"),
            ("الحلة", "Babil"), ("Babylon", "Babil"), ("كربلا", "Karbala"), ("Kerbala", "Karbala"),
            ("النجف الاشرف", "Najaf"), ("الكوفة", "Najaf"), ("الكوت", "Wasit"),
            ("ميسان", "Maysan"), ("العمارة", "Maysan"), ("الناصرية", "Dhi Qar"),
            ("Thi Qar", "Dhi Qar"), ("السماوة", "Muthanna"), ("الديوانية", "Qadisiyyah"),
            ("صلاح الدين", "Saladin"), ("تكريت", "Saladin"), ("سامراء", "Saladin"),
            ("بَغْدَاد", "Baghdad"), ("بغـــداد", "Baghdad"), ("هەولێر", "Erbil"),
            ("سلێمانی", "Sulaymaniyah"), ("دهۆک", "Duhok"), ("مدينة الصدر", "Baghdad"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_order(text)["governorate"], gov)

    def test_street_named_after_another_city(self):
        r = self.assertOrder("زينب\nالبصرة شارع بغداد\n07801234567",
                             governorate="Basra", address="شارع بغداد")
        self.assertEqual(r["warnings"], [])

    def test_garage_named_after_another_city(self):
        self.assertOrder("حسن محمد\nكراج النجف - بغداد العلاوي\n07801234567",
                         governorate="Baghdad", address="كراج النجف - العلاوي")

    def test_hay_named_after_governorate(self):
        self.assertOrder("07712345678 بابل الحلة حي بابل",
                         governorate="Babil", address="الحلة حي بابل")

    def test_conflicting_governorates_warn(self):
        r = parse_order("علي حسين\nبغداد\nالبصرة الجزائر\n07701234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertTrue(any("more than one governorate" in w for w in r["warnings"]))
        self.assertTrue(r["needs_review"])

    def test_typo_is_guessed_with_warning(self):
        r = parse_order("علي حسين\nبغدااد حي الزهراء قرب الجامع\n07701234567")
        self.assertEqual(r["governorate"], "Baghdad")
        self.assertEqual(r["confidence"]["governorate"], "low")
        self.assertTrue(any("misspelled" in w for w in r["warnings"]))
        self.assertTrue(r["needs_review"])
        self.assertEqual(r["address"], "حي الزهراء قرب الجامع")

    def test_typo_agreeing_with_district_is_removed(self):
        self.assertOrder("علي حسين\nبغدااد حي العامل الثاني\n07701234567",
                         governorate="Baghdad", address="حي العامل الثاني")

    def test_unknown_two_word_place_goes_to_address_not_notes(self):
        # Kept (it is a real Baghdad area) but flagged, since it was not recognised.
        self.assertOrder("علي حسين\nبغداد\nكمب سارة\n07701234567",
                         name="علي حسين", address="كمب سارة", notes=None, needs_review=True)

    def test_unknown_place_leaves_governorate_missing(self):
        r = self.assertOrder("علي حسين\nحي الزهراء قرب الجامع\n07701234567",
                             governorate=None, address="حي الزهراء قرب الجامع")
        self.assertIn("governorate", r["missing"])

    def test_all_19_governorates_listed(self):
        self.assertEqual(len(GOVERNORATES), 19)
        for gov, data in GOVERNORATES.items():
            # Every governorate's canonical Arabic name resolves to itself.
            self.assertEqual(parse_order(data["ar"])["governorate"], gov)
            self.assertEqual(parse_order(gov)["governorate"], gov)


class Names(Base):
    def test_surname_with_article(self):
        self.assertOrder("علي الربيعي\nبغداد المنصور\n07701234567",
                         name="علي الربيعي", governorate="Baghdad", address="المنصور")

    def test_kunya(self):
        self.assertOrder("ام حسين\nالنجف حي الحنانة\n07801234567", name="ام حسين")

    def test_name_that_is_also_a_district(self):
        # "منصور" (no article) is a person, "المنصور" a Baghdad district.
        self.assertOrder("منصور كاظم\nالبصرة التنومة\n07701234567",
                         name="منصور كاظم", governorate="Basra")

    def test_name_muthanna_is_not_the_governorate(self):
        self.assertOrder("مثنى احمد\nالديوانية حي العروبة\n07701234567",
                         name="مثنى احمد", governorate="Qadisiyyah")

    def test_salam_as_a_name(self):
        self.assertOrder("مرحبا\nسلام عادل\nالكوت\n07701234567", name="سلام عادل")

    def test_greeting_salam_is_dropped(self):
        self.assertOrder("سلام\nحسن محمد\nبغداد الدورة\n07801234567", name="حسن محمد")

    def test_baghdadi_surname_is_not_a_place(self):
        self.assertOrder("علي البغدادي\nالبصرة العشار\n07701234567",
                         name="علي البغدادي", governorate="Basra")

    def test_latin_name_is_title_cased(self):
        self.assertOrder("ahmed ali\nbaghdad karrada\n07701234567", name="Ahmed Ali")

    def test_missing_name(self):
        r = self.assertOrder("07712345678 بغداد الكرادة", name=None)
        self.assertEqual(r["missing"], ["name"])
        self.assertFalse(r["is_complete"])


class Phones(Base):
    def test_alt_phone(self):
        self.assertOrder("حسن محمد\nبغداد الدورة\n07801234567 / 07701234567",
                         phone="+9647801234567", alt_phones=["+9647701234567"])

    def test_duplicate_phone_written_twice(self):
        self.assertOrder("علي\nبغداد الكرادة\n07701234567\n+964 770 123 4567",
                         phone="+9647701234567", alt_phones=[])

    def test_short_phone_is_flagged_not_guessed(self):
        r = self.assertOrder("علي حسين\nبغداد الكرادة\n0770123456",
                             phone=None, needs_review=True)
        self.assertIn("phone", r["missing"])
        self.assertTrue(any("wrong number of digits" in w for w in r["warnings"]))
        self.assertNotIn("0770123456", r["address"] or "")

    def test_foreign_phone_is_flagged(self):
        r = parse_order("علي حسين\nبغداد الكرادة\n+971 50 123 4567")
        self.assertIsNone(r["phone"])
        self.assertTrue(any("not an Iraqi number" in w for w in r["warnings"]))

    def test_uncommon_prefix_is_accepted_but_flagged(self):
        r = parse_order("علي حسين\nبغداد الكرادة قرب الجامع\n07401234567")
        self.assertEqual(r["phone"], "+9647401234567")
        self.assertEqual(r["confidence"]["phone"], "medium")
        self.assertTrue(r["needs_review"])

    def test_phone_label_words_do_not_leak(self):
        self.assertOrder("علي حسين رقمي 07701234567\nبغداد الكرادة",
                         name="علي حسين", phone="+9647701234567")

    def test_house_number_next_to_phone(self):
        self.assertOrder("علي حسين\nبغداد الكرادة زقاق 12 دار 5 07701234567",
                         phone="+9647701234567", address="الكرادة زقاق 12 دار 5")


class SilentErrorRegressions(Base):
    """Cases found by stress-testing where the output used to be wrong while
    ``needs_review`` was False. Each must now be right, or at least flagged."""

    def test_chatter_lines_go_to_notes_not_address(self):
        for text, address in [
            ("هسه انطيك المعلومات\nسجاد فلاح\nبغداد مدينة الصدر قطاع ٤٤\n07723456789",
             "مدينة الصدر قطاع 44"),
            ("ان شاء الله\nعلي حسن\nبغداد الدورة قرب السوق\n07701234567", "الدورة قرب السوق"),
            ("اوكي حبي تمام\nعلي حسن\nبغداد الدورة قرب السوق\n07701234567", "الدورة قرب السوق"),
            ("شكرا الكم\nعلي حسن\nبغداد الدورة قرب السوق\n07701234567", "الدورة قرب السوق"),
            ("علي حسن\nبغداد الدورة قرب السوق\n07701234567\nاتصل قبل لا توصل", "الدورة قرب السوق"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_order(text)["address"], address)

    def test_product_line_with_number_is_a_note(self):
        r = self.assertOrder("اريد العطر الي بالستوري رقم 3\nاسمي حنين\nبغداد الزعفرانية\n07701234567",
                             name="حنين", address="الزعفرانية",
                             notes="اريد العطر الي بالستوري رقم 3")
        self.assertTrue(r["needs_review"])  # bare neighbourhood, no street/landmark

    def test_labelled_name_stops_at_function_words(self):
        r = self.assertOrder("ok so my name is ali and im in basra 07723456789",
                             name="Ali", governorate="Basra", address=None)
        self.assertTrue(r["needs_review"])
        self.assertOrder("اسمي علي وهذا رقم اخوي 07723456789 لان رقمي عاطل، النجف",
                         name="علي", governorate="Najaf", address=None)
        self.assertOrder("اسمي هو حسن\nبغداد الكرادة قرب الجامع\n07701234567", name="حسن")

    def test_recipient_label(self):
        r = self.assertOrder(
            "المستلم: سيف\nالرقم: 07723456789\nالعنوان: بغداد الشعب\nالاسم صاحب الطلب: نادية",
            name="سيف", address="الشعب", notes="نادية")
        self.assertTrue(r["needs_review"])

    def test_city_after_mantiqa_is_kept(self):
        self.assertOrder("اسمي باقر ساكن بابل منطقة المحاويل 07801239870",
                         governorate="Babil", address="منطقة المحاويل")

    def test_map_link_goes_to_notes(self):
        r = self.assertOrder("Location: https://maps.app.goo.gl/abc123\nعلي\nبغداد\n07723456789",
                             address=None, notes="https://maps.app.goo.gl/abc123")
        self.assertTrue(r["needs_review"])

    def test_proclitic_removed_from_kept_city(self):
        r = self.assertOrder("اسمي كوثر 07701234565 ساكنين بالديوانية",
                             governorate="Qadisiyyah", address="الديوانية")
        self.assertTrue(r["needs_review"])  # city only

    def test_neighbourhood_named_after_governorate_in_english(self):
        self.assertOrder("hello! I'm Yusuf, Mosul, Al-Muthanna neighborhood, 07709998877",
                         name="Yusuf", governorate="Nineveh", address="Mosul - Al-Muthanna neighborhood")

    def test_residence_beats_origin(self):
        r = self.assertOrder("اني من النجف بس ساكن ببغداد الحرية\nاسمي حسين\n07701236666",
                             governorate="Baghdad")
        self.assertTrue(r["needs_review"])
        r = self.assertOrder("اسمي عباس من الكوت بس اشتغل بالبصرة وابي التوصيل للكوت حي الكفاءات "
                             "07801234583", governorate="Wasit")
        self.assertTrue(r["needs_review"])

    def test_name_after_place_on_same_line(self):
        self.assertOrder("بغداد الكرادة احمد فاضل 07701235678",
                         name="احمد فاضل", governorate="Baghdad", address="الكرادة")
        # "حي الحسين" ends in a name but is an address
        self.assertOrder("علي\nكربلاء حي الحسين\n07701234567", name="علي", address="حي الحسين")

    def test_single_unknown_word_address_is_flagged(self):
        r = parse_order("علي حسن\nبغداد الشعب\n07701234567")
        self.assertEqual(r["address"], "الشعب")
        self.assertTrue(r["needs_review"])

    def test_honorific_name_is_recognised(self):
        self.assertOrder("الست هدى\nبغداد الكرادة داخل\n07701234765", name="الست هدى")


class Robustness(Base):
    def test_empty(self):
        r = parse_order("")
        self.assertEqual(r["missing"], ["name", "phone", "governorate", "address"])
        self.assertTrue(r["needs_review"])

    def test_only_greeting(self):
        r = parse_order("السلام عليكم")
        self.assertEqual(r["missing"], ["name", "phone", "governorate", "address"])

    def test_type_error(self):
        with self.assertRaises(TypeError):
            parse_order(None)

    def test_output_shape(self):
        r = parse_order("احمد علي\nبغداد الكرادة\n07701234567")
        self.assertEqual(
            set(r),
            {"name", "phone", "governorate", "address", "governorate_ar", "landmark", "alt_phones",
             "notes", "missing", "warnings", "confidence", "is_complete", "needs_review"},
        )

    def test_crlf_and_extra_whitespace(self):
        self.assertOrder("  احمد علي  \r\n\r\n  بغداد   الكرادة  \r\n 07701234567 ",
                         name="احمد علي", address="الكرادة")


if __name__ == "__main__":
    unittest.main()
