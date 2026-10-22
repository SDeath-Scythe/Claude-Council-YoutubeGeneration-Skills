"""Generates set C (600 seeded template DMs) into cases_c.py. Written blind to both implementations."""
import random
R = random.Random(20261021)
AD = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
# place -> (gov key, spelled forms); cities/districts with an unambiguous governorate
PLACES = [
 ('baghdad', ['بغداد', 'Baghdad']), ('baghdad', ['الكرادة']), ('baghdad', ['الدورة']), ('baghdad', ['الكاظمية']), ('baghdad', ['زيونة']),
 ('basra', ['البصرة', 'Basra', 'البصره']), ('basra', ['الزبير']), ('basra', ['العشار']),
 ('nineveh', ['الموصل', 'Mosul', 'نينوى']), ('erbil', ['أربيل', 'اربيل', 'Erbil']), ('erbil', ['عينكاوة']),
 ('sulaymaniyah', ['السليمانية', 'Sulaymaniyah']), ('duhok', ['دهوك', 'Duhok']), ('duhok', ['زاخو']),
 ('kirkuk', ['كركوك', 'Kirkuk']), ('diyala', ['بعقوبة', 'ديالى']), ('anbar', ['الرمادي', 'الانبار', 'الفلوجة']),
 ('saladin', ['تكريت', 'صلاح الدين', 'سامراء']), ('babil', ['الحلة', 'بابل']), ('karbala', ['كربلاء', 'Karbala']),
 ('najaf', ['النجف', 'Najaf', 'الكوفة']), ('wasit', ['الكوت', 'واسط']), ('dhiqar', ['الناصرية', 'ذي قار']),
 ('maysan', ['العمارة', 'ميسان']), ('muthanna', ['السماوة', 'المثنى']), ('qadisiyyah', ['الديوانية', 'القادسية']),
 ('halabja', ['حلبجة']),
]
AREAS = ['حي الزهراء', 'حي الحسين', 'شارع الجمهورية', 'حي العامل', 'شارع المطار', 'حي الاطباء', 'حي الصناعي', 'شارع الجامعة', 'حي الشرطة', 'حي النصر']
LAND = ['قرب جامع الرحمن', 'مقابل مدرسة الفارابي', 'قرب صيدلية الشفاء', 'خلف سوق الخضار', 'قرب مستشفى الجمهوري', 'جنب فرن الامل']
NAMES = ['علي حسين', 'محمد كاظم', 'زينب عباس', 'فاطمة جواد', 'حيدر سلمان', 'مريم خالد', 'احمد ستار', 'نور محمد', 'سجاد علي', 'رقية حسن', 'Ali Hassan', 'Sara Kareem', 'مصطفى عادل', 'هبة فاضل', 'ام زهراء', 'ابو مهدي']
PREF = ['770', '771', '772', '773', '774', '750', '751', '780', '781', '790', '791', '775', '782']
GREET = ['', 'السلام عليكم', 'مرحبا', 'هلو', 'اريد اطلب', 'Hi', 'اريد القطعة الي بالصورة', 'شلونكم']
def phone_forms(d):  # d = 10 digits starting with 7
    a, b, c = d[:3], d[3:6], d[6:]
    return ['0' + d, '0%s %s %s' % (a, b, c), '0%s-%s-%s' % (a, b, c), '+964' + d, '+964 %s %s %s' % (a, b, c), '00964' + d,
            ('0' + d).translate(AD), ('0%s %s %s' % (a, b, c)).translate(AD), '964' + d, d]
cases = []
for i in range(600):
    gov, forms = R.choice(PLACES); place = R.choice(forms)
    area = R.choice(AREAS + [''] * 2); land = R.choice(LAND + [''] * 3)
    name = R.choice(NAMES); digits = R.choice(PREF) + ''.join(R.choice('0123456789') for _ in range(7))
    ph = R.choice(phone_forms(digits)); greet = R.choice(GREET)
    labeled = R.random() < 0.5
    addr_txt = ' '.join(x for x in [place, area, land] if x)
    if labeled:
        parts = ['الاسم: ' + name, 'الرقم: ' + ph, 'العنوان: ' + addr_txt]
    else:
        parts = [name, ph, addr_txt]
    R.shuffle(parts)
    if greet: parts.insert(0, greet)
    sep = R.choice(['\n', '\n', '، ', ' - ', ' '])
    text = sep.join(parts)
    key = (area or land or None)
    keyword = None
    if area: keyword = area.split()[-1]
    elif land: keyword = land.split()[-1]
    cases.append((text, '+964' + digits, gov, name, keyword))
with open(__file__.replace('gen_c.py', 'cases_c.py'), 'w') as f:
    f.write('CASES = ' + repr(cases) + '\n')
print(len(cases))
