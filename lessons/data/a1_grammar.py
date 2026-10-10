"""Grammar topics for the A1 course.

``GRAMMAR`` maps a topic title to its explanation. Titles are the stable key that
``lessons/data/a1_lessons_*.py`` reference, so rename a title in both places (or not
at all). Every explanation is written for a Persian-speaking learner: the rule first
in Persian, then examples with their Persian meaning, and a one-line English gloss
at the end (marked with ``English:``).

A1.1 topics live in this file, A1.2 topics in ``a1_grammar_b`` -- both are original
material, nothing is copied from a published textbook.
"""

from . import a1_grammar_b

A1_1 = {
    # ------------------------------------------------------------------ lesson 1
    "Personalpronomen und das Verb „sein“": """ضمیرهای شخصی در آلمانی مثل فارسی «من، تو، او…» هستند، ولی آلمانی برای «او» سه شکل دارد: er (مذکر)، sie (مؤنث) و es (خنثی). فعل «sein» یعنی «بودن» و بسیار بی‌قاعده است؛ باید حفظش کنید.

ich bin    من هستم
du bist    تو هستی
er/sie/es ist    او هست
wir sind    ما هستیم
ihr seid    شما (جمع دوستانه) هستید
sie sind    آن‌ها هستند
Sie sind    شما (احترامی) هستید

مثال:
Ich bin Sina. من سینا هستم.
Er ist Lehrer. او معلم است.
Wir sind aus dem Iran. ما اهل ایران هستیم.

نکته: در آلمانی فعل همیشه صرف می‌شود و ضمیر را می‌توان حذف کرد، ولی در سطح A1 همیشه ضمیر را بیاورید.

English: Personal pronouns plus the highly irregular present tense of „sein“ (to be). Note that German has three words for „he/she/it“: er, sie, es.""",

    "W-Fragen: wer, wie, wo, woher": """سؤال‌های W با یک کلمه پرسشی شروع می‌شوند که همیشه با حرف W نوشته می‌شود. بعد از کلمه پرسشی، فعل می‌آید و سپس فاعل.

wer?    چه کسی؟
wie?    چطور؟ / چه‌طور
wo?    کجا؟
woher?    از کجا؟
was?    چه؟
wohin?    به کجا؟
wann?    چه وقت؟
warum?    چرا؟

مثال:
Wer ist das? این چه کسی است؟
Wo wohnst du? کجا زندگی می‌کنی؟
Woher kommen Sie? اهل کجا هستید؟
Wie heißen Sie? اسم شما چیست؟

نکته: «wie» را برای پرسیدن اسم هم استفاده می‌کنیم: Wie heißt du? (اسمت چیست؟)

English: Open questions with a W-word first, then the verb, then the subject. The most useful ones at A1 are wer, wie, wo, woher, was, wann and warum.""",

    "Ja/Nein-Fragen und kurze Antworten": """سؤالی که با «بله یا نه» جواب داده می‌شود، کلمه پرسشی ندارد. در این سؤال فعل به جای اول جمله می‌آید.

Aussage: Du kommst aus dem Iran. (تو اهل ایرانی.)
Frage: Kommst du aus dem Iran? (اهل ایرانی؟)

مثال:
Trinkst du Kaffee? قهوه می‌نوشی؟
Sind Sie Frau Mohammadi? شما خانم محمدی هستید؟
Hast du Zeit? وقت داری؟

پاسخ کوتاه:
Ja, ich trinke Kaffee. بله، قهوه می‌نوشم.
Nein, ich trinke keinen Kaffee. نه، قهوه نمی‌نوشم.
Doch, ich trinke Kaffee. چرا، قهوه می‌نوشم. (پاسخ مثبت به سؤال منفی)

نکته مهم: اگر سؤال منفی باشد و جواب شما مثبت است، از «doch» استفاده کنید، نه «ja».

English: Yes/no questions put the verb first. Answer a negative question with „doch“ when the answer is actually yes: „Trinkst du keinen Kaffee?“ – „Doch, ich trinke Kaffee.“""",

    "du und Sie – wie man jemanden anspricht": """آلمانی دو شکل خطاب دارد:
• «du» برای دوست، خانواده، همکلاسی، بچه‌ها و آدم‌های هم‌سن.
• «Sie» (همیشه با حرف بزرگ) برای غریبه‌ها، آدم‌های بزرگ‌تر، رئیس و در مغازه و اداره.

نکته: با «Sie» فعل مثل سوم‌شخص جمع صرف می‌شود:
Wie heißt du?    اسمت چیست؟ (دوستانه)
Wie heißen Sie?    اسم شما چیست؟ (احترامی)

در امتحان A1 هر دو شکل را می‌آزمایند، ولی در مکالمه اگر شک دارید، «Sie» بگویید که مؤدبانه‌تر است.

English: „du“ for friends, family and peers; „Sie“ (always capitalised) for strangers, officials and polite situations. With „Sie“ the verb takes the third person plural form.""",

    # ------------------------------------------------------------------ lesson 2
    "Regelmäßige Verben im Präsens": """بیشتر فعل‌های آلمانی باقاعده‌اند. ریشه فعل را می‌گیریم و پایانه اضافه می‌کنیم: kommen ← komm-.

ich komm-e    wir komm-en
du komm-st    ihr komm-t
er/sie/es komm-t    sie/Sie komm-en

مثال:
Ich wohne in Berlin. من در برلین زندگی می‌کنم.
Du lernst Deutsch. تو آلمانی یاد می‌گیری.
Wir spielen Fußball. ما فوتبال بازی می‌کنیم.

نکته: اگر ریشه به -t یا -d ختم شود، یک e اضافه می‌شود: du arbeitest، er arbeitet.

English: Regular verbs take the endings -e, -st, -t, -en, -t, -en. Stems ending in -t or -d add an extra e (du arbeitest).""",

    "Satzstellung: Verb an Position 2": """در جمله خبری ساده آلمانی، فعلِ صرف‌شده همیشه در جایگاه دوم می‌آید. اگر جمله با یک قید یا زمان شروع شود، فاعل و فعل جابه‌جا می‌شوند، ولی فعل همچنان دوم است.

Ich trinke morgen Kaffee.
Morgen trinke ich Kaffee. (فردا قهوه می‌نوشم.)

مثال:
Heute arbeite ich nicht. امروز کار نمی‌کنم.
In Berlin wohnt meine Schwester. خواهرم در برلین زندگی می‌کند.

English: The conjugated verb always occupies position 2 in a statement. If another element starts the sentence, the subject moves behind the verb: „Morgen trinke ich Kaffee.“""",

    "Herkunft und Wohnort: kommen aus, wohnen in": """برای گفتن «اهل کجا هستی» از kommen + aus استفاده می‌کنیم و برای «کجا زندگی می‌کنی» از wohnen + in.

Woher kommst du? – Ich komme aus dem Iran.
Wo wohnst du? – Ich wohne in Teheran.

نکته: نام بیشتر کشورها و شهرها بدون حرف تعریف می‌آید:
Ich komme aus Deutschland. (بدون حرف تعریف)
Ich wohne in Berlin. (بدون حرف تعریف)

فقط چند کشور حرف تعریف دارند: die Schweiz، die Türkei، der Iran، die USA.
Die Schweiz → Ich komme aus der Schweiz.
Der Iran → Ich komme aus dem Iran.

English: „kommen aus“ for origin, „wohnen in“ for where you live. Most countries and cities take no article; a few do (der Iran, die Schweiz, die Türkei, die USA).""",

    # ------------------------------------------------------------------ lesson 3
    "Zahlen von 0 bis 1000": """اعداد پایه:
0 null، 1 eins، 2 zwei، 3 drei، 4 vier، 5 fünf، 6 sechs، 7 sieben، 8 acht، 9 neun، 10 zehn
11 elf، 12 zwölf، 13 dreizehn، 14 vierzehn، 15 fünfzehn، 16 sechzehn، 17 siebzehn، 18 achtzehn، 19 neunzehn
20 zwanzig، 30 dreißig، 40 vierzig، 50 fünfzig، 60 sechzig، 70 siebzig، 80 achtzig، 90 neunzig
100 (ein)hundert، 1000 (ein)tausend

از 21 به بعد اول یکان و بعد دهگان می‌آید، و با «und» به هم وصل می‌شوند:
21 einundzwanzig، 32 zweiunddreißig، 45 fünfundvierzig

مثال:
Ich bin fünfundzwanzig Jahre alt. من بیست‌وپنج سال دارم.
Das kostet zwölf Euro fünfzig. این دوازده یورو و پنجاه سنت است.

نکته: «sechzehn» و «siebzehn» بدون حرف s و با حذف e نوشته می‌شوند و «dreißig» با ß است.

English: Numbers 0–1000. From 21 upwards the unit comes first: einundzwanzig (one-and-twenty). Note the spellings sechzehn, siebzehn and dreißig.""",

    "Das Verb „haben“ und die Fragen wie viel / wie alt": """فعل «haben» یعنی «داشتن» و مثل «sein» بی‌قاعده است:

ich habe، du hast، er/sie/es hat، wir haben، ihr habt، sie/Sie haben

با «wie viel» مقدار و قیمت را می‌پرسیم و با «wie alt» سن را:
Wie viel kostet das? این چند است؟
Wie viel Uhr ist es? ساعت چند است؟
Wie alt bist du? چند سال داری؟
Ich bin zwanzig Jahre alt. بیست سال دارم.

نکته: برای سن در آلمانی «sein» به کار می‌رود، نه «haben» (برخلاف فارسی که می‌گوییم «سن دارم»).

English: The irregular verb „haben“. „wie viel“ asks about quantity or price, „wie alt“ about age. German uses „sein“ for age: „Ich bin 20 Jahre alt.“""",

    "Das Alphabet und das Buchstabieren": """حرف الفبا در آلمانی:
a، b، c، d، e، f، g، h، i، j، k، l، m، n، o، p، q، r، s، t، u، v، w، x، y، z
حروف اضافه: ä (a-Umlaut)، ö، ü، ß (Eszett / scharfes s)

چند حرف فرق دارند:
j مثل «ی» (Jahr)، v مثل «ف» (Vater)، w مثل «و» (Wasser)، z مثل «تس» (Zahl)، s در اول کلمه مثل «ز» (Sonne).

برای هجی کردن از این عبارت‌ها استفاده می‌کنیم:
A wie Anton، B wie Berta، … (در مکالمه: „B wie Berta“)

مثال:
Wie schreibt man das? – B-U-C-H.
Buchstabieren Sie bitte Ihren Namen. لطفاً نام خود را هجی کنید.

English: The German alphabet, including the umlauts ä ö ü and ß. Useful phrases for spelling aloud: „Wie schreibt man das?“ and „Buchstabieren Sie bitte Ihren Namen.“""",

    # ------------------------------------------------------------------ lesson 4
    "Artikel: der, die, das und ein, eine, ein": """هر اسم آلمانی جنسیت دستوری دارد: مذکر (der)، مؤنث (die)، خنثی (das). این جنسیت همیشه با معنی کلمه جور نیست: das Mädchen (دختر) خنثی است.

معرفه:    der Mann، die Frau، das Kind
نکره:    ein Mann، eine Frau، ein Kind

نکته: «ein» برای مذکر و خنثی یکسان است و فقط مؤنث «eine» می‌گیرد.

مثال:
Das ist ein Tisch. این یک میز است.
Das ist eine Lampe. این یک چراغ است.
Der Tisch ist neu. میز نو است.

English: All German nouns have a grammatical gender: der (masculine), die (feminine), das (neuter). The indefinite article is „ein“ for masculine and neuter, „eine“ for feminine.""",

    "Possessivartikel: mein, dein, sein, ihr, unser, euer": """این کلمه‌ها مالکیت را نشان می‌دهند و مثل «ein» صرف می‌شوند:

ich → mein/meine    wir → unser/unsere
du → dein/deine    ihr → euer/eure
er/es → sein/seine    sie/Sie → ihr/ihre

مثال:
Das ist mein Bruder. این برادر من است.
Das ist meine Schwester. این خواهر من است.
Wie ist deine Telefonnummer? شماره تلفن تو چیست؟
Das ist sein Auto. این ماشین اوست.

نکته: تابع جنسیتِ اسمِ بعد از خود است، نه جنسیت مالک:
mein Vater (پدرم)، meine Mutter (مادرم).

English: Possessive articles behave like „ein“/„eine“ and follow the gender of the noun they precede: „mein Bruder“, „meine Schwester“, „meine Eltern“.""",

    "Der Plural der Nomen": """در آلمانی راه‌های گوناگونی برای جمع بستن وجود دارد؛ بهترین کار این است که جمع را همراه خود کلمه حفظ کنید.

پایانه‌های رایج:
-e (der Tisch → die Tische)
-en/-n (die Frau → die Frauen، die Lampe → die Lampen)
-er (das Kind → die Kinder)
-s (das Auto → die Autos)
بدون پایانه، فقط Umlaut (der Vater → die Väter)

در جمع، برای همه جنسیت‌ها «die» به کار می‌رود:
der Bruder → die Brüder    das Buch → die Bücher    die Stadt → die Städte

نکته: اسم‌های مختوم به -chen و -lein در جمع تغییری نمی‌کنند: das Mädchen → die Mädchen.

English: German plurals use different endings (-e, -en, -er, -s, …), so learn each plural with its noun. The plural article is always „die“.""",

    "Familienstand und Verwandtschaft ausdrücken": """برای گفتن وضعیت تأهل:
Ich bin ledig. مجردم.
Ich bin verheiratet. متأهلم.
Ich bin geschieden. جدا شده‌ام. (در A1 فقط به‌عنوان واژه می‌شناسیم)

خانواده:
der Vater – die Mutter (پدر – مادر)
der Sohn – die Tochter (پسر – دختر)
der Bruder – die Schwester (برادر – خواهر)
die Großeltern، die Großmutter، der Großvater
Ich habe einen Bruder und zwei Schwestern. یک برادر و دو خواهر دارم.
Das sind meine Eltern. این‌ها والدین من هستند.

نکته: «die Eltern» و «die Geschwister» فقط جمع هستند و شکل مفرد ندارند.

English: Talking about your family and marital status. „die Eltern“ and „die Geschwister“ exist only in the plural.""",

    # ------------------------------------------------------------------ lesson 5
    "Berufe: kein Artikel nach „sein“": """وقتی می‌گوییم کسی چه شغلی دارد، بعد از «sein» حرف تعریف نمی‌آید:

Ich bin Lehrer. معلم هستم. (نه: Ich bin ein Lehrer.)
Sie ist Ärztin. او پزشک است.
Er ist Student. او دانشجو است.

اگر با «arbeiten als» بگوییم، باز هم بدون حرف تعریف است:
Ich arbeite als Ingenieur. به‌عنوان مهندس کار می‌کنم.

فرم مؤنث شغل‌ها معمولاً با -in ساخته می‌شود:
der Lehrer → die Lehrerin، der Arzt → die Ärztin، der Kellner → die Kellnerin

English: After „sein“ a profession takes no article: „Ich bin Lehrer.“ The feminine form of most professions ends in -in.""",

    "Negation: nicht oder kein?": """برای منفی کردن دو کلمه داریم:

• «nicht» برای فعل، صفت، قید و اسمِ معرفه:
Ich arbeite nicht. کار نمی‌کنم.
Das ist nicht mein Buch. این کتاب من نیست.
Sie kommt heute nicht. امروز نمی‌آید.

• «kein/keine/kein» برای اسم ناشناس (مثل «هیچ/هیچ‌کدام» در فارسی):
Ich habe kein Auto. ماشین ندارم.
Ich trinke keine Milch. شیر نمی‌نوشم.
Das ist kein Problem. مشکلی نیست.

قاعده ساده: اگر در جمله مثبت «ein/eine» یا بدون حرف تعریف بود، در جمله منفی «kein» می‌آید؛ در غیر این صورت «nicht».

English: „nicht“ negates verbs, adjectives and definite nouns; „kein/keine“ negates indefinite nouns (the equivalent of „not a / no“).""",

    "Unregelmäßige Verben mit Vokalwechsel: fahren, schlafen, essen, nehmen": """شماری از فعل‌های پرکاربرد در دوم‌شخص و سوم‌شخص مفرد، مصوت ریشه را عوض می‌کنند:

fahren: ich fahre، du fährst، er fährt
schlafen: ich schlafe، du schläfst، er schläft
essen: ich esse، du isst، er isst
nehmen: ich nehme، du nimmst، er nimmt
sprechen: ich spreche، du sprichst، er spricht
lesen: ich lese، du liest، er liest

مثال:
Er fährt nach Berlin. او به برلین می‌رود.
Du isst zu viel. زیادی می‌خوری.
Sie nimmt den Bus. او اتوبوس می‌گیرد.

English: Several common verbs change their stem vowel in the du- and er/sie/es-forms (a→ä, e→i/ie): du fährst, er schläft, du isst, er nimmt.""",

    # ------------------------------------------------------------------ lesson 6
    "Trennbare Verben im Präsens": """بعضی فعل‌ها یک پیشوند جداشدنی دارند. در جمله خبری، پیشوند به انتهای جمله می‌رود:

aufstehen → Ich stehe um sieben Uhr auf. ساعت هفت بلند می‌شوم.
einkaufen → Wir kaufen im Supermarkt ein. در سوپرمارکت خرید می‌کنیم.
anfangen → Der Kurs fängt um neun an. کلاس ساعت نه شروع می‌شود.
anrufen → Ich rufe dich später an. بعداً بهت زنگ می‌زنم.
fernsehen → Abends sehe ich fern. شب‌ها تلویزیون تماشا می‌کنم.

فعل‌های جداشدنی پرکاربرد A1:
aufstehen، aufwachen، einkaufen، einladen، anrufen، anfangen، aufhören، anmachen، ausmachen، mitkommen، mitnehmen، zuhören، fernsehen

نکته: در فرهنگ لغت این فعل‌ها با یک خط جداکننده نشان داده می‌شوند: auf|stehen.

English: Separable verbs split in the present tense: the prefix moves to the end of the sentence. „Ich stehe um sieben Uhr auf.“ The prefix is stressed and marked in dictionaries as auf|stehen.""",

    "Die Uhrzeit: formell und informell": """سؤال: Wie viel Uhr ist es? / Wie spät ist es?

شکل رسمی (۲۴ ساعته):
7:00 → Es ist sieben Uhr.
7:15 → Es ist sieben Uhr fünfzehn.
7:30 → Es ist sieben Uhr dreißig.
7:45 → Es ist sieben Uhr fünfundvierzig.

شکل غیررسمی (رایج در مکالمه):
7:15 → Viertel nach sieben
7:30 → halb acht (نصفِ ساعت هفت → یعنی نیم ساعت مانده به هشت!)
7:45 → Viertel vor acht

نکته بسیار مهم: «halb acht» یعنی ۷:۳۰، نه ۸:۳۰. در آلمانی به «ساعت بعدی» نگاه می‌کنیم.

پرسش ساعت انجام کار: Um wie viel Uhr …? – Um sieben Uhr.

English: Telling the time. In the informal system „halb acht“ means 7:30 (half way to eight) – a classic trap for learners. Use „Um wie viel Uhr …?“ to ask when something happens.""",

    "Zeitangaben: um, am, von … bis": """حرف اضافه‌های زمانی مهم:
um + ساعت: um sieben Uhr (ساعت هفت)
am + روز: am Montag (دوشنبه)، am Wochenende (آخر هفته)
im + ماه/فصل: im Januar، im Sommer
von … bis: von neun bis fünf (از نه تا پنج)

مثال:
Der Unterricht beginnt um neun Uhr. کلاس ساعت نه شروع می‌شود.
Am Samstag arbeite ich nicht. شنبه کار نمی‌کنم.
Im Winter ist es kalt. در زمستان هوا سرد است.
Ich arbeite von acht bis vier. از هشت تا چهار کار می‌کنم.

English: Time prepositions: „um“ with clock times, „am“ with days, „im“ with months and seasons, „von … bis“ for a range.""",

    "Satzstellung mit Zeit- und Ortsangaben": """ترتیب رایج در جمله آلمانی: زمان پیش از مکان می‌آید.

Ich fahre morgen mit dem Bus nach Berlin.
(زمان: morgen → مکان/نحوه: mit dem Bus nach Berlin)

مثال:
Ich gehe heute ins Kino. امروز به سینما می‌روم.
Am Montag arbeite ich im Büro. دوشنبه در دفتر کار می‌کنم.

قیدهای تکرار (immer، oft، manchmal، selten، nie) معمولاً بعد از فعل می‌آیند:
Ich trinke immer Kaffee. همیشه قهوه می‌نوشم.
Er kommt nie zu spät. او هرگز دیر نمی‌آید.

English: German word order prefers time before place. Adverbs of frequency (immer, oft, manchmal, selten, nie) usually stand right after the verb.""",

    # ------------------------------------------------------------------ lesson 7
    "Der Akkusativ: den, die, das, einen, eine": """در جمله، مفعول مستقیم (کسی یا چیزی که فعل رویش انجام می‌شود) در حالت «akkusativ» است. فقط مذکر تغییر می‌کند:

Nominativ → Akkusativ
der → den
ein → einen
die → die (بدون تغییر)
das → das (بدون تغییر)
die (جمع) → die (بدون تغییر)

مثال:
Ich kaufe einen Tisch. یک میز می‌خرم. (der Tisch → einen Tisch)
Ich kaufe eine Lampe. یک چراغ می‌خرم.
Ich nehme das Buch. کتاب را برمی‌دارم.
Ich trinke den Kaffee. قهوه را می‌نوشم.

English: The accusative case marks the direct object. Only masculine forms change: der → den, ein → einen. Feminine, neuter and plural stay the same.""",

    "Verben mit Akkusativ: essen, trinken, nehmen, brauchen": """این فعل‌ها مفعول مستقیم (akkusativ) می‌گیرند:

essen: Ich esse einen Apfel. یک سیب می‌خورم.
trinken: Er trinkt einen Kaffee. او یک قهوه می‌نوشد.
nehmen: Wir nehmen den Bus. اتوبوس می‌گیریم.
brauchen: Ich brauche eine Fahrkarte. یک بلیت لازم دارم.
kaufen: Sie kauft ein Brot. یک نان می‌خرد.
möchten: Ich möchte einen Tee. یک چای می‌خواهم.

نکته: «möchten» بسیار پرکاربرد است و در فروشگاه و رستوران از آن استفاده می‌کنیم.

English: Common verbs that take a direct object in the accusative: essen, trinken, nehmen, brauchen, kaufen, möchten.""",

    "gern, lieber, am liebsten": """برای گفتن «چه چیزی را دوست دارم» از «gern» استفاده می‌کنیم. این کلمه بعد از فعل می‌آید:

Ich trinke gern Tee. چای دوست دارم (با میل می‌نوشم).
Ich koche gern. آشپزی دوست دارم.

مقایسه‌ای:
gern (دوست دارم) → lieber (بیشتر دوست دارم) → am liebsten (از همه بیشتر دوست دارم)
Ich trinke gern Kaffee، aber am liebsten trinke ich Tee.
قهوه دوست دارم، ولی از همه بیشتر چای می‌نوشم.

نکته: «gern» با «mögen» فرق دارد: mögen + اسم (Ich mag Tee.) ولی gern + فعل (Ich trinke gern Tee.).

English: „gern“ (gladly) expresses what you like doing; its comparative ladder is gern – lieber – am liebsten. „mögen“ takes a noun, „gern“ goes with a verb.""",

    # ------------------------------------------------------------------ lesson 8
    "möchten: Wünsche und höfliche Bitten": """«möchten» شکل مؤدبانه «خواستن» است و در رستوران، مغازه و دفتر از آن استفاده می‌کنیم:

ich möchte، du möchtest، er möchte، wir möchten، ihr möchtet، sie/Sie möchten

مثال:
Ich möchte einen Kaffee, bitte. یک قهوه لطفاً.
Wir möchten bestellen. می‌خواهیم سفارش بدهیم.
Möchten Sie noch etwas? چیز دیگری میل دارید؟
Was möchten Sie trinken? چه می‌نوشید؟

نکته: بعد از «möchten» اسم در حالت akkusativ می‌آید: Ich möchte einen Salat (der Salat → einen Salat).

English: „möchten“ is the polite way to express a wish or order: „Ich möchte einen Kaffee, bitte.“ The following noun is in the accusative.""",

    "Im Restaurant: bestellen, bezahlen, Trinkgeld": """جمله‌های کاربردی در رستوران:
Die Speisekarte, bitte. منو لطفاً.
Ich möchte bestellen. می‌خواهم سفارش بدهم.
Ich nehme die Suppe und einen Salat. سوپ و یک سالاد می‌گیرم.
Zusammen oder getrennt? با هم یا جدا؟
Die Rechnung, bitte. صورت‌حساب لطفاً.
Zahlen, bitte. می‌خواهم حساب کنم.
Stimmt so. باقی‌اش برایتان. (انعام)
Das macht 18 Euro 50. می‌شود هجده یورو و پنجاه.

نکته: در آلمان معمولاً ۵ تا ۱۰ درصد انعام (Trinkgeld) می‌دهیم.

English: Ordering and paying in a restaurant: „Ich möchte bestellen“, „Die Rechnung, bitte“, „Zusammen oder getrennt?“ Tipping (Trinkgeld) is around 5–10 %.""",

    # ------------------------------------------------------------------ lesson 9
    "Der Akkusativ mit dem bestimmten Artikel: den, die, das": """اگر اسم معرفه باشد، در حالت akkusativ فقط مذکر عوض می‌شود:

der Tisch → den Tisch
die Lampe → die Lampe
das Buch → das Buch
die Bücher → die Bücher

مثال:
Ich nehme den Bus. اتوبوس را می‌گیرم.
Wo ist die Kasse? صندوق کجاست؟
Ich bezahle das Brot. نان را می‌پردازم.
Ich kaufe die Tomaten. گوجه‌ها را می‌خرم.

نکته: فقط همین یک تغییر کوچک است (der → den)، پس راحت یاد می‌گیرید.

English: In the accusative only the masculine definite article changes: der → den. Feminine, neuter and plural stay the same.""",

    "Mengen und Verpackungen: ein Kilo, eine Flasche, ein Stück": """برای خرید مقدار معین از این ساختار استفاده می‌کنیم: مقدار + اسم.

ein Kilo Tomaten        یک کیلو گوجه
ein halbes Kilo Käse        نیم کیلو پنیر
eine Flasche Wasser        یک بطری آب
ein Glas Milch        یک لیوان شیر
ein Stück Kuchen        یک تکه کیک
eine Tasse Kaffee        یک فنجان قهوه
eine Packung Butter        یک بسته کره
100 Gramm Schinken        صد گرم ژامبون

مثال:
Ich möchte ein Kilo Kartoffeln, bitte. یک کیلو سیب‌زمینی لطفاً.
Wir brauchen eine Flasche Wasser. یک بطری آب لازم داریم.

English: Quantities and containers: ein Kilo, eine Flasche, ein Glas, ein Stück, eine Tasse, eine Packung + noun.""",

    "Imperativ mit Sie": """برای درخواست مؤدبانه از «Sie» استفاده می‌کنیم. شکل ساده است: فعل + Sie.

Kommen Sie bitte herein. لطفاً بفرمایید داخل.
Nehmen Sie den Bus 100. اتوبوس ۱۰۰ را بگیرید.
Warten Sie bitte hier. لطفاً اینجا منتظر بمانید.
Sprechen Sie bitte langsamer. لطفاً آهسته‌تر صحبت کنید.

نکته: فعل و ضمیر جابه‌جا می‌شوند: از «Sie nehmen» به «Nehmen Sie» می‌رسیم.

English: The polite imperative is simply the verb followed by „Sie“: „Nehmen Sie den Bus 100.“""",

    "Der Imperativ mit du": """برای دوست و خانواده از شکل «du» استفاده می‌کنیم. پایانه -st حذف می‌شود و «du» نمی‌آید:

Komm herein! بیا داخل!
Nimm den Bus! اتوبوس را بگیر!
Warte hier! اینجا صبر کن!
Sprich langsam! آهسته حرف بزن!

فعل‌های جداشدنی پیشوند را نگه می‌دارند:
Steh bitte auf! لطفاً بلند شو!
Ruf mich morgen an! فردا بهم زنگ بزن!

نکته: «bitte» جمله را مؤدبانه‌تر می‌کند.

English: The informal imperative drops the ending -st and the pronoun du: „Komm herein!“, „Nimm den Bus!“, „Steh bitte auf!“""",

    # ------------------------------------------------------------------ lesson 10
    "gefallen + Dativ: Das gefällt mir": """برای گفتن «این را دوست دارم/خوشم می‌آید» از فعل «gefallen» استفاده می‌کنیم. شخص در حالت «dativ» می‌آید:

mir، dir، ihm، ihr، uns، euch، ihnen، Ihnen

Das gefällt mir. این را دوست دارم. (خوشم می‌آید)
Die Jacke gefällt mir. ژاکت را دوست دارم.
Gefällt dir die Farbe? رنگ را دوست داری؟
Die Schuhe gefallen mir nicht. کفش‌ها را دوست ندارم.

نکته: فاعل همان چیزی است که خوش می‌آید؛ پس فعل با آن مطابقت می‌کند: die Schuhe gefallen.

English: „gefallen“ takes a dative person: „Das gefällt mir.“ The thing you like is the subject, so the verb agrees with it (die Schuhe gefallen mir).""",

    "Farben und Adjektive vor dem Nomen (Grundlagen)": """رنگ‌ها: rot، blau، gelb، grün، schwarz، weiß، braun، grau، orange، rosa، lila، bunt

وقتی صفت مستقیم پیش از اسم بیاید، پایانه می‌گیرد. در سطح A1 این چهار شکل را بشناسید:
ein rotes Hemd (خنثی)
eine rote Jacke (مؤنث)
der rote Rock (مذکر معرفه)
die blauen Schuhe (جمع)

مثال:
Ich suche ein blaues Hemd. یک پیراهن آبی می‌خواهم.
Die rote Jacke ist zu teuer. ژاکت قرمز خیلی گران است.
Haben Sie diese Hose in Schwarz? این شلوار را در رنگ مشکی دارید؟

English: Colour adjectives. When an adjective stands directly before a noun it takes an ending: „ein rotes Hemd“, „eine rote Jacke“, „die blauen Schuhe“.""",

    "dieser, diese, dieses": """برای اشاره به چیز نزدیک از «dieser» استفاده می‌کنیم:

der/dieser Tisch → dieser Tisch
die/diese Lampe → diese Lampe
das/dieses Buch → dieses Buch
die/diese Schuhe → diese Schuhe
در حالت akkusativ: diesen Tisch

مثال:
Dieses Hemd ist zu klein. این پیراهن خیلی کوچک است.
Wie viel kostet diese Tasche? این کیف چند است؟
Ich nehme diesen Mantel. این پالتو را می‌خرم.

English: Demonstrative articles: dieser/diese/dieses follow the same pattern as der/die/das, with „diesen“ in the masculine accusative.""",

    # ------------------------------------------------------------------ lesson 11
    "Präpositionen des Ortes mit Dativ: in, an, auf, unter, neben …": """برای گفتن «کجاست» بعد از این حرف اضافه‌ها حالت «dativ» می‌آید:

in (در)، an (کنار/روی)، auf (روی)، unter (زیر)، über (بالای)، neben (کنار)، zwischen (بین)، vor (جلوی)، hinter (پشت)

در حالت dativ:
der → dem    die → der    das → dem    die (جمع) → den (+ -n)

مثال:
Das Buch liegt auf dem Tisch. کتاب روی میز است.
Die Lampe steht neben dem Sofa. چراغ کنار کاناپه است.
Der Schlüssel ist in der Tasche. کلید در کیف است.
Die Katze ist unter dem Bett. گربه زیر تخت است.

English: Place prepositions with the dative case: in, an, auf, unter, über, neben, zwischen, vor, hinter + dem/der/dem/den.""",

    "es gibt + Akkusativ": """برای گفتن «وجود دارد / هست» از «es gibt» استفاده می‌کنیم و اسم بعد از آن در حالت akkusativ است:

Es gibt einen Tisch. یک میز هست.
Es gibt eine Küche. یک آشپزخانه هست.
Es gibt ein Bad. یک حمام هست.
Es gibt keine Garage. گاراژ نیست.

مثال:
In meiner Wohnung gibt es drei Zimmer. آپارتمان من سه اتاق دارد.
Gibt es hier einen Supermarkt? اینجا سوپرمارکت هست؟

English: „es gibt“ (there is / there are) is followed by the accusative: „Es gibt einen Tisch.“""",

    "wo? und wohin? – Grundlagen der Wechselpräpositionen": """این حرف اضافه‌ها هم با dativ و هم با akkusativ می‌آیند:

• «wo?» (کجاست، جای ثابت) → dativ
Das Buch liegt auf dem Tisch. کتاب روی میز است.

• «wohin?» (به کجا، حرکت) → akkusativ
Ich lege das Buch auf den Tisch. کتاب را روی میز می‌گذارم.

جمله‌های کلیدی A1:
stehen/stellen (ایستادن / گذاشتن عمودی)، liegen/legen (خوابیدن / گذاشتن افقی)، sitzen / sich setzen (نشستن / نشستن).

English: Two-way prepositions take the dative for position („wo?“) and the accusative for direction („wohin?“): „auf dem Tisch“ vs „auf den Tisch“.""",

    "Möbel und Räume beschreiben": """واژه‌های مهم خانه:
die Wohnung، das Zimmer، das Wohnzimmer، das Schlafzimmer، die Küche، das Bad، der Balkon، der Keller
Möbel: der Tisch، der Stuhl، das Sofa، das Bett، der Schrank، das Regal، die Lampe، der Teppich، der Spiegel

مثال:
Meine Wohnung hat zwei Zimmer, eine Küche und ein Bad. آپارتمان من دو اتاق، یک آشپزخانه و یک حمام دارد.
Im Wohnzimmer steht ein Sofa. در اتاق نشیمن یک کاناپه هست.
Die Küche ist klein, aber hell. آشپزخانه کوچک است ولی روشن.

English: Describing rooms and furniture: die Wohnung, das Zimmer, das Wohnzimmer, das Schlafzimmer, die Küche, das Bad + furniture nouns.""",
}


A1_2 = a1_grammar_b.A1_2

GRAMMAR = {**A1_1, **A1_2}
