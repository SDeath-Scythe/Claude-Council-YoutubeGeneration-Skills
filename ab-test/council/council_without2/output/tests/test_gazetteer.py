import unittest

from dallal_parser import GOVERNORATES
from dallal_parser.gazetteer import find_places
from dallal_parser.normalize import clean_text, make_key


def govs(text):
    return [(h.governorate, h.kind) for h in find_places(make_key(clean_text(text)))]


class GazetteerTest(unittest.TestCase):
    def test_all_19_governorates(self):
        self.assertEqual(len(GOVERNORATES), 19)

    def test_every_governorate_matches_its_arabic_and_english_name(self):
        for en, ar in GOVERNORATES.items():
            with self.subTest(gov=en):
                self.assertEqual(govs(ar), [(en, "governorate")])
                self.assertEqual(govs(en), [(en, "governorate")])

    def test_spelling_variants(self):
        cases = {
            "البصره": "Basra", "بصرة": "Basra", "Basrah": "Basra", "اربيل": "Erbil", "هولير": "Erbil",
            "Hawler": "Erbil", "السليمانيه": "Sulaymaniyah", "Slemani": "Sulaymaniyah", "Dohuk": "Duhok",
            "كربلا": "Karbala", "Kerbala": "Karbala", "ذيقار": "Dhi Qar", "Thi Qar": "Dhi Qar",
            "الانبار": "Anbar", "ديالي": "Diyala", "صلاح الدين": "Saladin", "Salahuddin": "Saladin",
            "نينوه": "Nineveh", "Ninawa": "Nineveh",
        }
        for text, gov in cases.items():
            with self.subTest(text=text):
                self.assertEqual(govs(text)[0][0], gov)

    def test_arabic_clitics(self):
        for text in ["بالبصرة", "للبصرة", "والبصرة", "فالبصرة", "ببغداد", "لبغداد", "وبغداد"]:
            with self.subTest(text=text):
                self.assertEqual(len(govs(text)), 1)

    def test_cities_map_to_governorate(self):
        cases = {
            "الموصل": "Nineveh", "Mosul": "Nineveh", "الحلة": "Babil", "الكوت": "Wasit",
            "الناصرية": "Dhi Qar", "السماوة": "Muthanna", "الديوانية": "Qadisiyyah", "بعقوبة": "Diyala",
            "تكريت": "Saladin", "الرمادي": "Anbar", "الفلوجة": "Anbar", "الزبير": "Basra", "الكوفة": "Najaf",
            "زاخو": "Duhok", "عنكاوة": "Erbil", "رانية": "Sulaymaniyah", "الكرادة": "Baghdad",
            "مدينة الصدر": "Baghdad", "Sadr City": "Baghdad", "al-Mansour": "Baghdad", "العمارة": "Maysan",
        }
        for text, gov in cases.items():
            with self.subTest(text=text):
                self.assertEqual(govs(text), [(gov, "city")])

    def test_names_and_words_that_are_not_places(self):
        # Bare forms that are personal names or everyday words.
        for text in ["منصور", "Mansour", "زبير", "Zubair", "عمارة 5", "كوت جلد", "شعلة", "حمزة", "Hit",
                     "سعدية", "Samara", "ميمونة", "قرنة", "بياع", "باسم", "السلام عليكم"]:
            with self.subTest(text=text):
                self.assertEqual(govs(text), [])

    def test_longest_match_wins(self):
        self.assertEqual(govs("بغداد الجديدة"), [("Baghdad", "city")])

    def test_word_boundaries(self):
        self.assertEqual(govs("محله 905"), [])  # contains حله (Hilla) inside a word
        self.assertEqual(govs("Kutaiba"), [])


if __name__ == "__main__":
    unittest.main()
