"""Common Iraqi given names (Arabic, Kurdish, Latin/Arabizi spellings).  Pure data.

Used as *positive evidence*: an unlabelled line is accepted as the name with
high confidence only if one of its words is a known given name.  Otherwise
the name comes back with confidence 'low' + warning 'name_unverified', so the
bot confirms it: a word list of chatter can never be complete ('عليكم السلام',
'جزاك الله خير' ...), a list of names covers most customers.  Labelled names
('الاسم: ...') do not need this.  Add names freely; spellings are folded at
import (أ/ا, ة/ه, ى/ي are the same).
"""

ARABIC = """
محمد احمد علي حسين حسن عباس جعفر كاظم جاسم حيدر كرار مصطفى مرتضى منتظر سجاد مهدي ياسر عمار عمر عثمان خالد
وليد سعد سعيد سالم صالح صلاح فلاح فاضل فراس فارس قاسم قيس كريم عبد عبدالله عبدالرحمن عبدالكريم عبدالامير
عبدالحسين عبدالزهرة عبدالرضا رضا هادي هاشم ماجد مجيد حميد رشيد نبيل نزار نصير ناصر منصور ميثم مازن مالك
ابراهيم اسماعيل اسحاق يوسف يعقوب يونس يحيى زكريا موسى عيسى سليمان داود ادريس الياس طه ياسين محسن حسنين
زيد زياد ضياء ضرغام رعد رائد رامي رياض رحيم رزاق جبار ستار غفار قهار عادل عدنان عامر عماد عصام علاء
اياد ايهاد امير انور اسعد ثامر ثائر جمال جلال حامد حازم حاتم حمزة خضر خليل سامي سامر سلام سمير شاكر
شهاب صادق صباح ضاري طارق طلال عزيز عقيل غانم غسان فؤاد فيصل قحطان لؤي لطيف ليث مؤيد محمود مثنى مجتبى
مشتاق معتز مقداد نجم نوري هيثم وسام وائل وحيد ياس يزن بلال باسم بسام بشار بشير توفيق تحسين جواد جليل
حكيم حمادي حمود خلف دريد راضي رسول رافد زاهر زهير سعدون سلمان شوقي صفاء ضياء عبود عواد غازي فالح فرحان
كامل لفتة مطر مناف مهند نعمة نوفل هلال همام ورد يسار باقر صادق كميل اثير عون حارث حيدرة علاوي حمودي
زهراء زينب فاطمة مريم نور نورا هدى سارة رقية ايات اية ايمان امنة امل اسراء اسيل بتول بنين تبارك تقى
حوراء حنين حلا هلا رسل رنا رند رغد رحاب رباب زهرة سجى سلمى سهى شهد شيماء صفا ضحى عذراء علياء غدير
فرح كوثر لمياء لينا ليلى مروة منى مها ميس ميسان نادية نبأ ندى نرجس نسرين هاجر هبة هند وعد ولاء ياسمين
دعاء جنات جنان حنان خديجة ريم زمن سعاد سناء سهام شذى صابرين عبير عهود غادة فاتن فاطمه قمر لبنى لقاء
مياسة نجلاء نهى هيام وفاء اشواق انعام بشرى تهاني حسنة حياة خلود دنيا رجاء رشا رواء زينة سحر سوسن
شروق صبا ضمياء عالية غفران كفاح لانا مأب نغم نوال هالة هيفاء ورود يقين ام ابو ديالا رهف جود
"""

KURDISH = """
ئاراس ئاری ئاسۆ ئازاد ئارام ئەحمەد ئیبراهیم بەختیار بارزان بێستون چیا دلشاد دیار رێبوار رێباز زانا سەرکەوت
شوان کاروان کامەران هاوکار هێمن هێرش هەڤاڵ ڕێبین ژیان ڤیان نەسرین شیلان پەری گوڵاڵە سۆزان ئاوات دلێر
آراس اري ازاد ارام بختيار بارزان دلشاد ريبوار زانا شوان كاروان كامران هاوكار هيمن هيرش سوزان نسرين شيلان
ئاری جوان روژان هەژار سیروان سەروەر ئاکۆ لەیلا
"""

LATIN = """
mohammed muhammad mohamed mohammad mohamad ahmed ahmad ali hussein husain hussain hasan hassan abbas jaafar jafar
kadhim kazim jasim jassim haider hayder karrar mustafa mostafa murtadha murtada muntadhar sajjad mahdi mehdi
yasir yaser ammar omar umar othman khalid walid waleed saad saeed salim salem saleh salah falah fadhil firas
faris qasim kasim qais karim kareem abdullah abdulla abdul abd ridha reda hadi hashim majid hamid rashid nabil
nizar nasir mansour maitham mazin malik ibrahim ismail yousif yusuf yousef yaqoob younis yahya musa moses issa
sulaiman dawood idris taha yaseen yassin muhsin hasanain zaid zayd ziad ziyad dhiya raad raed rami riyadh rahim
razzaq jabbar sattar adil adel adnan amir amer imad isam alaa ayad anwar thamer tariq talal aziz aqeel ghanim
ghassan fuad faisal laith layth muayad mahmoud muthanna mujtaba mushtaq muataz miqdad najm nouri haitham wisam
wael bilal basim bassam bashar jawad hakim rasool baqir kumail athir harith hamza zahraa zahra zainab zaynab
fatima fatimah maryam mariam noor nour nora huda sara sarah ruqaya ayat aya iman eman amal israa aseel batool
baneen tabarak tuqa hawraa hanin haneen hala rusul rana rand raghad rihab zahra saja salma suha shahad shaimaa
safa dhuha athraa alyaa ghadeer farah kawthar lamia lina layla leila marwa muna mona maha mays dua duaa jannat
jinan hanan khadija reem suad sanaa siham shatha abeer ghada fatin qamar lubna liqaa najlaa nuha wafaa bushra
dunya raja rasha zina sahar sawsan shurooq saba ghufran lana noora yasmin yasmeen
aras ari azad aram bakhtiar barzan dilshad rebwar zana shwan karwan kamaran hawkar hemin herish suzan nasreen
shilan jwan rozhan sirwan ako lanya
3li 3ly 7sen 7sn 7usain 7ussein 7assan 7asan 3abbas 3mar 3umar 3adnan 3adel 3aqeel 7aider 7ayder 7amza 7amid
m7md m7mmd mo7ammed mo7amed a7med a7mad 3ali zahra2 7awraa 7awra2 fa6ima fatma ma7di mus6afa 6aha 7anan 7ala
"""

GIVEN_NAMES = sorted(set(ARABIC.split()) | set(KURDISH.split()) | set(LATIN.split()))
