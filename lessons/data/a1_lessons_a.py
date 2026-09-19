"""Lesson material for A1.1 (lessons 1-12).

Every lesson is a dict understood by ``lessons/management/commands/seed_a1_course.py``:

* ``contents`` -- ``(TYPE, title, body)`` tuples in display order. ``TYPE`` is one of
  ``EXPLANATION``, ``VOCABULARY``, ``GRAMMAR``, ``EXAMPLE``, ``DIALOGUE``, ``NOTE``.
  Bodies are written for a Persian-speaking learner and end with an ``English:`` gloss.
* ``words_new`` / ``words_review`` -- German headwords exactly as stored in
  ``vocabulary.Word``. A row is created per entry, so an entry must appear only once
  per lesson (``unique_word_per_lesson``).
* ``grammar`` -- titles that must exist in ``lessons/data/a1_grammar.py``.
* ``sentences`` -- ``(German, Persian, ROLE, speaker)`` tuples. ROLE is one of
  ``EXAMPLE``, ``DIALOGUE``, ``READING``, ``LISTENING``; ``speaker`` may be "".

Sentences are deduplicated by their German text, so repeating a sentence in a later
lesson (a review lesson, for instance) reuses the same ``Sentence`` row instead of
creating a second one.
"""

LESSONS: list[dict] = []

# --------------------------------------------------------------------- lesson 1
LESSONS.append(
    {
        "order": 1,
        "title": "Hallo! Begrüßung und Vorstellung",
        "description": "سلام و خداحافظی، معرفی خود، پرسیدن اسم. English: greetings, introductions, asking for a name.",
        "estimated_time": 45,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس یاد می‌گیرید به کسی سلام کنید، خداحافظی کنید، اسم خود را بگویید و اسم طرف مقابل را بپرسید. این‌ها اولین جمله‌هایی هستند که در آلمان هر روز به کار می‌آیند.

هدف درس: می‌توانم خودم را معرفی کنم، اسم کسی را بپرسم و مؤدبانه جواب بدهم.

English: In this lesson you greet people, say goodbye, give your own name and ask for someone else's name.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Begrüßung und Verabschiedung",
                """سلام کردن بر اساس ساعت روز:
guten Morgen (صبح بخیر، تا حدود ساعت ۱۱)
guten Tag (روز بخیر، از حدود ۱۱ تا ۱۸)
guten Abend (شب بخیر، هنگام ورود)
hallo (سلام؛ دوستانه، در هر ساعتی)

خداحافظی:
auf Wiedersehen (خداحافظ؛ رسمی)
tschüss (خداحافظ؛ دوستانه)
bis bald (به‌زودی می‌بینمت)
bis morgen (تا فردا)

واژه‌های ادب:
danke (متشکرم) · bitte (لطفاً / خواهش می‌کنم) · gern geschehen (خواهش می‌کنم) · Entschuldigung (ببخشید) · kein Problem (مشکلی نیست) · willkommen (خوش آمدید)

English: Greetings by time of day, ways of saying goodbye, and the courtesy words danke, bitte, Entschuldigung.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: sich vorstellen",
                """دو جمله کلیدی برای معرفی خود:
Ich bin …    من … هستم.
Ich heiße …    اسم من … است.

پرسیدن اسم:
Wie heißt du?    اسمت چیه؟ (دوستانه)
Wie heißen Sie?    اسم شما چیست؟ (مؤدبانه)

نکته ساختاری: در جمله خبری آلمانی فعل همیشه در جایگاه دوم می‌آید:
Ich (۱) bin (۲) Sina. · Ich (۱) heiße (۲) Sara.

English: The two key sentences are „Ich bin …“ and „Ich heiße …“. The conjugated verb is always the second element.""",
            ),
            (
                "DIALOGUE",
                "Dialog: Anna und Ben lernen sich kennen",
                """Anna: Guten Morgen!  (صبح بخیر!)
Ben: Guten Morgen! Wie geht's?  (صبح بخیر! چطوری؟)
Anna: Danke, gut. Und dir?  (ممنون، خوبم. تو چطوری؟)
Ben: Auch gut, danke.  (من هم خوبم، ممنون.)
Ben: Wie heißt du?  (اسمت چیه؟)
Anna: Ich heiße Anna. Und du?  (اسم من آناست. تو؟)
Ben: Ich bin Ben.  (من بن هستم.)
Anna: Wie bitte?  (ببخشید، چی گفتید؟)
Ben: B-E-N.  (بِ - اِ - اِن.)   ← در درس ۳ هجی کردن را کامل یاد می‌گیرید.
Anna: Auf Wiedersehen!  (خداحافظ!)
Ben: Tschüss! Bis bald!  (خداحافظ! به‌زودی می‌بینمت!)

English: A short first meeting: greeting, asking how someone is, exchanging names, saying goodbye.""",
            ),
            (
                "NOTE",
                "Achtung: du oder Sie?",
                """با دوست، همکلاسی، خانواده و هم‌سن‌ها du می‌گوییم؛ با غریبه‌ها، افراد بزرگ‌تر، رئیس و در مغازه و اداره Sie. ضمیر Sie همیشه با حرف بزرگ نوشته می‌شود.

اگر چیزی را نفهمیدید: Wie bitte?
اگر اشتباه کردید: Entschuldigung! یا Es tut mir leid.
برای تشکر از کسی که کاری برایتان کرده: Danke! – Gern geschehen.

English: „du“ for friends, family and peers; „Sie“ (always capitalised) for strangers and formal situations.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Personen vorstellen",
                """Ich bin Ali.  (من علی هستم.)
Das ist Frau Schmidt.  (این خانم اشمیت است.)
Er ist Herr Weber.  (او آقای وبر است.)
Sind Sie Frau Mohammadi?  (شما خانم محمدی هستید؟)
Ja, ich bin Frau Mohammadi.  (بله، من خانم محمدی هستم.)
Nein, ich bin nicht Frau Mohammadi.  (نه، من خانم محمدی نیستم.)

English: Introducing other people and confirming or denying an identity.""",
            ),
        ],
        "words_new": [
            "hallo",
            "guten Morgen",
            "guten Tag",
            "guten Abend",
            "gute Nacht",
            "auf Wiedersehen",
            "tschüss",
            "bis bald",
            "bis morgen",
            "willkommen",
            "wie geht's",
            "Wie heißt du?",
            "Wie bitte?",
            "entschuldigung",
            "es tut mir leid",
            "danke",
            "bitte",
            "gern geschehen",
            "kein Problem",
            "ja",
            "nein",
            "doch",
            "ich",
            "du",
            "Sie",
            "er",
            "sie",
            "es",
            "sein",
            "heißen",
            "Name",
            "Vorname",
            "Familienname",
            "Herr",
            "Frau",
            "wie",
            "wer",
            "wo",
            "was",
        ],
        "words_review": [],
        "grammar": [
            "Personalpronomen und das Verb „sein“",
            "W-Fragen: wer, wie, wo, woher",
            "Ja/Nein-Fragen und kurze Antworten",
            "du und Sie – wie man jemanden anspricht",
        ],
        "sentences": [
            ("Guten Morgen!", "صبح بخیر!", "DIALOGUE", "Anna"),
            ("Guten Morgen! Wie geht's?", "صبح بخیر! چطوری؟", "DIALOGUE", "Ben"),
            ("Danke, gut. Und dir?", "ممنون، خوبم. تو چطوری؟", "DIALOGUE", "Anna"),
            ("Auch gut, danke.", "من هم خوبم، ممنون.", "DIALOGUE", "Ben"),
            ("Wie heißt du?", "اسمت چیه؟", "DIALOGUE", "Ben"),
            ("Ich heiße Anna. Und du?", "اسم من آناست. تو؟", "DIALOGUE", "Anna"),
            ("Ich bin Ben.", "من بن هستم.", "DIALOGUE", "Ben"),
            ("Wie bitte?", "ببخشید، چی گفتید؟", "DIALOGUE", "Anna"),
            ("B-E-N.", "بِ - اِ - اِن.", "DIALOGUE", "Ben"),
            ("Auf Wiedersehen!", "خداحافظ!", "DIALOGUE", "Anna"),
            ("Tschüss! Bis bald!", "خداحافظ! به‌زودی می‌بینمت!", "DIALOGUE", "Ben"),
            ("Ich bin Ali.", "من علی هستم.", "EXAMPLE", ""),
            ("Das ist Frau Schmidt.", "این خانم اشمیت است.", "EXAMPLE", ""),
            ("Er ist Herr Weber.", "او آقای وبر است.", "EXAMPLE", ""),
            ("Sind Sie Frau Mohammadi?", "شما خانم محمدی هستید؟", "EXAMPLE", ""),
            ("Ja, ich bin Frau Mohammadi.", "بله، من خانم محمدی هستم.", "EXAMPLE", ""),
            ("Nein, ich bin nicht Frau Mohammadi.", "نه، من خانم محمدی نیستم.", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 2
LESSONS.append(
    {
        "order": 2,
        "title": "Länder, Sprachen und Herkunft",
        "description": "از کجا آمدن، کجا زندگی کردن، زبان‌ها. English: countries, languages and where you are from.",
        "estimated_time": 60,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس یاد می‌گیرید بگویید اهل کجا هستید، کجا زندگی می‌کنید و چه زبان‌هایی حرف می‌زنید. همچنین اولین فعل‌های باقاعده را در جمله به کار می‌برید.

هدف درس: می‌توانم درباره کشور، شهر و زبان‌هایم حرف بزنم.

English: You learn to say where you come from, where you live and which languages you speak.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Länder und Sprachen",
                """کشورها: Deutschland (آلمان) · der Iran (ایران) · Österreich (اتریش) · die Schweiz (سوئیس)
زبان‌ها: Deutsch · Englisch · Persisch
شهر و مکان: die Stadt · das Land · hier (اینجا) · dort (آنجا)

نکته مهم: بیشتر نام کشورها و همه نام شهرها بدون حرف تعریف می‌آیند:
Ich wohne in Berlin. · Ich komme aus Deutschland.
ولی این چهار کشور حرف تعریف دارند: der Iran، die Schweiz، die Türkei، die USA:
Ich komme aus dem Iran. · Ich komme aus der Schweiz.

English: Country and language names. Most countries and all cities take no article; der Iran, die Schweiz, die Türkei and die USA do.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: regelmäßige Verben und Satzstellung",
                """فعل‌های باقاعده پایانه می‌گیرند. نمونه: kommen

ich komm-e    wir komm-en
du komm-st    ihr komm-t
er/sie/es komm-t    sie/Sie komm-en

همین پایانه‌ها برای wohnen، lernen و leben به کار می‌روند؛ sprechen نیز این پایانه‌ها را می‌گیرد، اما در du sprichst و er/sie/es spricht مصوت ریشه تغییر می‌کند.

نکته: در جمله خبری فعل در جایگاه دوم است. اگر جمله با مکان شروع شود، فاعل بعد از فعل می‌آید:
Ich wohne in Teheran.
In Teheran wohne ich. (در تهران زندگی می‌کنم.)

English: Regular verb endings (-e, -st, -t, -en, -t, -en) and the position-2 rule for the verb.""",
            ),
            (
                "NOTE",
                "Achtung: kommen und sprechen",
                """kommen، wohnen، lernen و leben کاملاً قاعده‌مند هستند و هیچ مصوتی عوض نمی‌کنند:
ich komme، du kommst، er kommt

ولی sprechen مصوت ریشه را عوض می‌کند:
ich spreche، du sprichst، er spricht

و در «woher» به معنی «از کجا» جایگاه کلمه پرسشی اول جمله است:
Woher kommst du? · Wo wohnst du?

English: kommen/wohnen/lernen/leben are fully regular; sprechen changes its stem vowel (du sprichst, er spricht).""",
            ),
            (
                "DIALOGUE",
                "Dialog: Woher kommst du?",
                """Sara: Hallo! Ich heiße Sara.  (سلام! اسم من ساراست.)
Timo: Hallo Sara. Ich bin Timo. Woher kommst du?  (سلام سارا. من تیمو هستم. اهل کجایی؟)
Sara: Ich komme aus dem Iran und wohne jetzt in Köln.  (من اهل ایرانم و الان در کلن زندگی می‌کنم.)
Timo: Welche Sprachen sprichst du?  (چه زبان‌هایی حرف می‌زنی؟)
Sara: Persisch, Englisch und ein bisschen Deutsch.  (فارسی، انگلیسی و کمی آلمانی.)
Timo: Das ist gut. Ich spreche kein Persisch.  (خوبه. من فارسی حرف نمی‌زنم.)
Sara: Kein Problem. Wir lernen zusammen.  (مشکلی نیست. با هم یاد می‌گیریم.)

English: Asking about origin, place of residence and languages spoken.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Herkunft und Wohnort",
                """Ich komme aus dem Iran.  (من اهل ایرانم.)
Meine Familie lebt in Isfahan.  (خانواده‌ام در اصفهان زندگی می‌کند.)
Wir wohnen in Berlin.  (ما در برلین زندگی می‌کنیم.)
Berlin ist eine Stadt in Deutschland.  (برلین شهری در آلمان است.)
Sie wohnt in der Schweiz.  (او در سوئیس زندگی می‌کند.)
Ich spreche Persisch und ein bisschen Englisch.  (فارسی و کمی انگلیسی صحبت می‌کنم.)

English: Sentences about origin, home town and languages.""",
            ),
        ],
        "words_new": [
            "kommen",
            "wohnen",
            "leben",
            "sprechen",
            "lernen",
            "Land",
            "Stadt",
            "Sprache",
            "Heimat",
            "Ausland",
            "Ausländer",
            "ausländisch",
            "international",
            "Deutschland",
            "Iran",
            "Österreich",
            "Schweiz",
            "Deutsch",
            "Englisch",
            "Persisch",
            "woher",
            "hier",
            "dort",
            "aus",
            "in",
            "Woher kommst du?",
            "Sprechen Sie Englisch?",
        ],
        "words_review": ["hallo", "ich", "du", "sein", "wie", "wo", "was", "Name", "heißen"],
        "grammar": [
            "Regelmäßige Verben im Präsens",
            "Satzstellung: Verb an Position 2",
            "Herkunft und Wohnort: kommen aus, wohnen in",
        ],
        "sentences": [
            ("Hallo! Ich heiße Sara.", "سلام! اسم من ساراست.", "DIALOGUE", "Sara"),
            ("Hallo Sara. Ich bin Timo. Woher kommst du?", "سلام سارا. من تیمو هستم. اهل کجایی؟", "DIALOGUE", "Timo"),
            (
                "Ich komme aus dem Iran und wohne jetzt in Köln.",
                "من اهل ایرانم و الان در کلن زندگی می‌کنم.",
                "DIALOGUE",
                "Sara",
            ),
            ("Welche Sprachen sprichst du?", "چه زبان‌هایی حرف می‌زنی؟", "DIALOGUE", "Timo"),
            (
                "Persisch, Englisch und ein bisschen Deutsch.",
                "فارسی، انگلیسی و کمی آلمانی.",
                "DIALOGUE",
                "Sara",
            ),
            ("Das ist gut. Ich spreche kein Persisch.", "خوبه. من فارسی حرف نمی‌زنم.", "DIALOGUE", "Timo"),
            ("Kein Problem. Wir lernen zusammen.", "مشکلی نیست. با هم یاد می‌گیریم.", "DIALOGUE", "Sara"),
            ("Woher kommst du?", "اهل کجایی؟", "EXAMPLE", ""),
            ("Wo wohnen Sie?", "کجا زندگی می‌کنید؟", "EXAMPLE", ""),
            ("Ich komme aus dem Iran.", "من اهل ایرانم.", "EXAMPLE", ""),
            ("Meine Familie lebt in Isfahan.", "خانواده‌ام در اصفهان زندگی می‌کند.", "EXAMPLE", ""),
            ("Wir wohnen in Berlin.", "ما در برلین زندگی می‌کنیم.", "EXAMPLE", ""),
            ("Ich spreche Persisch, Deutsch und Englisch.", "فارسی، آلمانی و انگلیسی صحبت می‌کنم.", "EXAMPLE", ""),
            ("Sprichst du Deutsch?", "آلمانی حرف می‌زنی؟", "EXAMPLE", ""),
            ("Ich lerne Deutsch.", "آلمانی یاد می‌گیرم.", "EXAMPLE", ""),
            ("Berlin ist eine Stadt in Deutschland.", "برلین شهری در آلمان است.", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 3
LESSONS.append(
    {
        "order": 3,
        "title": "Zahlen, Alphabet und Telefonnummern",
        "description": "شماره‌ها، سن، قیمت و هجی کردن. English: numbers, age, prices, spelling and phone numbers.",
        "estimated_time": 60,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس عددها را از صفر تا هزار یاد می‌گیرید، می‌گویید چند سال دارید، قیمت را می‌پرسید و اسم خود را هجی می‌کنید.

هدف درس: می‌توانم شماره تلفن، سن و قیمت را بگویم و بفهمم.

English: Numbers 0–1000, telling your age, asking prices, spelling your name.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Zahlen von 0 bis 1000",
                """0 null · 1 eins · 2 zwei · 3 drei · 4 vier · 5 fünf · 6 sechs · 7 sieben · 8 acht · 9 neun · 10 zehn
11 elf · 12 zwölf · 13 dreizehn · 14 vierzehn · 15 fünfzehn · 16 sechzehn · 17 siebzehn · 18 achtzehn · 19 neunzehn
20 zwanzig · 30 dreißig · 40 vierzig · 50 fünfzig · 60 sechzig · 70 siebzig · 80 achtzig · 90 neunzig
100 (ein)hundert · 1000 (ein)tausend

از ۲۱ به بعد اول یکان می‌آید و بعد دهگان، با «und» به هم وصل می‌شوند:
21 einundzwanzig (یک‌و‌بیست) · 32 zweiunddreißig · 45 fünfundvierzig

نکته املا: sechzehn (بدون s)، siebzehn (با حذف en از sieben)، dreißig (با ß).

English: The numbers 0–1000. From 21 upwards the unit comes first (einundzwanzig).""",
            ),
            (
                "GRAMMAR",
                "Grammatik: haben und wie viel / wie alt",
                """فعل «haben» (داشتن) بی‌قاعده است:
ich habe · du hast · er/sie/es hat · wir haben · ihr habt · sie/Sie haben

با «wie viel» مقدار یا قیمت را می‌پرسیم و با «wie alt» سن را:
Wie viel kostet das?    این چند است؟
Wie alt bist du?    چند سال داری؟

نکته بسیار مهم: در آلمانی برای سن «sein» به کار می‌رود، نه «haben»:
Ich bin dreißig Jahre alt.    (نه: Ich habe dreißig Jahre.)

English: Present tense of „haben“ plus „wie viel“ (quantity/price) and „wie alt“ (age). Age uses „sein“.""",
            ),
            (
                "NOTE",
                "Achtung: das Alphabet und die Umlaute",
                """حرف‌های مخصوص آلمانی: ä (اِ با Umlaut)، ö، ü، ß (Eszett، مثل «س» تیز).

چند حرف با فارسی فرق دارد:
j = «ی» (Jahr) · v در واژه‌های بومی مانند Vater = «ف»، در واژه‌هایی مانند Video = /v/ · w = «و» (Wasser) · z = «تس» (Zahl) · s در آغاز واژه پیش از مصوت مانند Sonne معمولاً «ز»؛ sp/st آغازین مانند Spiel/Stein با /ʃ/ شروع می‌شوند

برای هجی کردن هم می‌توانید فقط حرف‌ها را پشت سر هم بگویید، هم با کلمه راهنما:
B wie Berta · A wie Anton

English: The German alphabet with ä, ö, ü and ß. Note that j, v, w, z and s sound different from English.""",
            ),
            (
                "DIALOGUE",
                "Dialog: am Telefon",
                """Herr Braun: Guten Tag! Wie ist Ihre Telefonnummer?  (روز بخیر! شماره تلفن شما چیست؟)
Frau Ahmadi: Meine Nummer ist 0176 45 67 89.  (شماره من ۰۱۷۶ ۴۵ ۶۷ ۸۹ است.)
Herr Braun: Danke. Und wie alt sind Sie?  (ممنون. و چند سال دارید؟)
Frau Ahmadi: Ich bin dreißig Jahre alt.  (سی سال دارم.)
Herr Braun: Wie schreibt man Ihren Namen?  (نام شما را چطور می‌نویسند؟)
Frau Ahmadi: A-H-M-A-D-I.  (اِی-اِچ-اِم-اِی-دِ-ای.)

English: A short telephone conversation with a phone number, an age and a spelled surname.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Zahlen im Alltag",
                """Das kostet zwölf Euro.  (این دوازده یورو است.)
Das kostet hundert Euro.  (این صد یورو است.)
Er ist zwanzig Jahre alt.  (او بیست سال دارد.)
Meine Handynummer ist 0176 12345678.  (شماره موبایلم ۰۱۷۶ ۱۲۳۴۵۶۷۸ است.)
Buchstabieren Sie bitte Ihren Namen.  (لطفاً نام خود را هجی کنید.)

English: Asking and giving prices, ages and phone numbers.""",
            ),
        ],
        "words_new": [
            "null",
            "eins",
            "zwei",
            "drei",
            "vier",
            "fünf",
            "sechs",
            "sieben",
            "acht",
            "neun",
            "zehn",
            "elf",
            "zwölf",
            "dreizehn",
            "vierzehn",
            "fünfzehn",
            "sechzehn",
            "siebzehn",
            "achtzehn",
            "neunzehn",
            "zwanzig",
            "einundzwanzig",
            "dreißig",
            "vierzig",
            "fünfzig",
            "sechzig",
            "siebzig",
            "achtzig",
            "neunzig",
            "hundert",
            "tausend",
            "Nummer",
            "Telefon",
            "Handy",
            "Buchstabe",
            "buchstabieren",
            "wie viel",
            "Alter",
            "Jahr",
            "Euro",
            "haben",
        ],
        "words_review": [
            "ich",
            "du",
            "Sie",
            "sein",
            "heißen",
            "Name",
            "Vorname",
            "Familienname",
            "wie",
            "wo",
            "was",
        ],
        "grammar": [
            "Zahlen von 0 bis 1000",
            "Das Verb „haben“ und die Fragen wie viel / wie alt",
            "Das Alphabet und das Buchstabieren",
        ],
        "sentences": [
            ("Wie ist Ihre Telefonnummer?", "شماره تلفن شما چیست؟", "DIALOGUE", "Herr Braun"),
            ("Meine Nummer ist 0176 45 67 89.", "شماره من ۰۱۷۶ ۴۵ ۶۷ ۸۹ است.", "DIALOGUE", "Frau Ahmadi"),
            ("Danke. Und wie alt sind Sie?", "ممنون. و چند سال دارید؟", "DIALOGUE", "Herr Braun"),
            ("Ich bin dreißig Jahre alt.", "سی سال دارم.", "DIALOGUE", "Frau Ahmadi"),
            ("Wie schreibt man Ihren Namen?", "نام شما را چطور می‌نویسند؟", "DIALOGUE", "Herr Braun"),
            ("A-H-M-A-D-I.", "آ - ها - اِم - آ - دِ - ای.", "DIALOGUE", "Frau Ahmadi"),
            ("Wie alt bist du?", "چند سال داری؟", "EXAMPLE", ""),
            ("Wie viel kostet das Buch?", "کتاب چند است؟", "EXAMPLE", ""),
            ("Das kostet zwölf Euro.", "این دوازده یورو است.", "EXAMPLE", ""),
            ("Das kostet hundert Euro.", "این صد یورو است.", "EXAMPLE", ""),
            ("Er ist zwanzig Jahre alt.", "او بیست سال دارد.", "EXAMPLE", ""),
            ("Meine Handynummer ist 0176 12345678.", "شماره موبایلم ۰۱۷۶ ۱۲۳۴۵۶۷۸ است.", "EXAMPLE", ""),
            ("Buchstabieren Sie bitte Ihren Namen.", "لطفاً نام خود را هجی کنید.", "EXAMPLE", ""),
            ("Wie schreibt man das?", "این را چطور می‌نویسند؟", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 4
LESSONS.append(
    {
        "order": 4,
        "title": "Familie und Personen",
        "description": "خانواده، وضعیت تأهل و مالکیت. English: family, marital status and possessive articles.",
        "estimated_time": 60,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس درباره خانواده‌تان حرف می‌زنید: چند نفر هستند، چه نسبتی دارند و متأهل هستند یا مجرد.

هدف درس: می‌توانم اعضای خانواده‌ام را معرفی کنم و درباره آن‌ها سؤال بپرسم.

English: You talk about your family: who they are, how old they are and their marital status.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Familie und Verwandte",
                """der Vater – die Mutter → die Eltern (پدر – مادر → والدین)
der Sohn – die Tochter (پسر – دختر)
der Bruder – die Schwester (برادر – خواهر)
die Geschwister (خواهر و برادرها – فقط جمع)
die Großmutter – der Großvater → die Großeltern
die Oma – der Opa (مادربزرگ – بابابزرگ؛ دوستانه)
der Onkel – die Tante (عمو/دایی – عمه/خاله)
der Mann – die Frau · der Junge – das Mädchen · das Kind · das Baby
der Freund – die Freundin · der Partner – die Partnerin

English: Family vocabulary, including the plural-only words die Eltern and die Geschwister.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: Artikel, Possessivartikel und Plural",
                """هر اسم آلمانی جنسیت دستوری دارد: der (مذکر)، die (مؤنث)، das (خنثی).
معرفه: der Mann · die Frau · das Kind
نکره: ein Mann · eine Frau · ein Kind

کلمه‌های مالکیت مثل «ein» صرف می‌شوند و تابع جنسیت اسم بعد از خود هستند:
ich → mein Vater / meine Mutter
du → dein Bruder / deine Schwester
wir → unser Kind / unsere Kinder
ihr → euer Sohn / eure Tochter

جمع همیشه با «die» می‌آید:
der Bruder → die Brüder · das Kind → die Kinder · die Frau → die Frauen

English: Definite and indefinite articles, possessive articles (mein/dein/unser/euer) and plural forms.""",
            ),
            (
                "DIALOGUE",
                "Dialog: ein Familienfoto",
                """Nina: Ist das deine Familie?  (این خانواده توست؟)
Omar: Ja, das sind meine Eltern und meine Schwester.  (بله، این‌ها پدر و مادرم و خواهرم هستند.)
Nina: Hast du auch Geschwister?  (تو هم خواهر و برادر داری؟)
Omar: Nein, ich habe keine Geschwister.  (نه، خواهر و برادر ندارم.)
Nina: Und wie alt ist deine Schwester?  (و خواهرت چند سال دارد؟)
Omar: Sie ist fünf Jahre alt.  (پنج سال دارد.)

English: Talking about a family photo: who is in it, siblings and ages.""",
            ),
            (
                "NOTE",
                "Achtung: Familienstand",
                """وضعیت تأهل را با «sein» می‌گوییم:
Ich bin ledig. (مجردم) · Ich bin verheiratet. (متأهلم)

نکته: der Mann هم «مرد» است و هم «شوهر»؛ die Frau هم «زن» و هم «همسر»:
Das ist mein Mann. (این شوهر من است.)

دقت کنید: برای «خواهر و برادر» کلمه جمع «die Geschwister» را به کار ببرید، نه شکل مفرد.

English: Marital status with „sein“: ledig / verheiratet. „der Mann“ and „die Frau“ also mean husband and wife.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: meine Familie",
                """Das ist meine Familie.  (این خانواده من است.)
Mein Vater heißt Reza.  (اسم پدرم رضاست.)
Meine Mutter ist Lehrerin.  (مادرم معلم است.)
Ich habe einen Bruder und eine Schwester.  (یک برادر و یک خواهر دارم.)
Meine Großeltern wohnen in Isfahan.  (پدربزرگ و مادربزرگم در اصفهان زندگی می‌کنند.)
Mein Onkel und meine Tante leben in Hamburg.  (عمو و عمه‌ام در هامبورگ زندگی می‌کنند.)

English: Describing your own family.""",
            ),
        ],
        "words_new": [
            "Familie",
            "Vater",
            "Mutter",
            "Eltern",
            "Sohn",
            "Tochter",
            "Kind",
            "Baby",
            "Bruder",
            "Schwester",
            "Geschwister",
            "Großmutter",
            "Großvater",
            "Großeltern",
            "Oma",
            "Opa",
            "Onkel",
            "Tante",
            "Mann",
            "Junge",
            "Mädchen",
            "Mensch",
            "Leute",
            "Freund",
            "Freundin",
            "Partner",
            "Partnerin",
            "Ehefrau",
            "Ehemann",
            "Familienstand",
            "verheiratet",
            "ledig",
            "mein",
            "dein",
            "unser",
            "euer",
            "alt",
            "jung",
            "geboren",
        ],
        "words_review": ["ich", "du", "sein", "haben", "wie viel", "Alter", "Jahr", "heißen", "Name", "wer"],
        "grammar": [
            "Artikel: der, die, das und ein, eine, ein",
            "Possessivartikel: mein, dein, sein, ihr, unser, euer",
            "Der Plural der Nomen",
            "Familienstand und Verwandtschaft ausdrücken",
        ],
        "sentences": [
            ("Ist das deine Familie?", "این خانواده توست؟", "DIALOGUE", "Nina"),
            (
                "Ja, das sind meine Eltern und meine Schwester.",
                "بله، این‌ها پدر و مادرم و خواهرم هستند.",
                "DIALOGUE",
                "Omar",
            ),
            ("Hast du auch Geschwister?", "تو هم خواهر و برادر داری؟", "DIALOGUE", "Nina"),
            ("Nein, ich habe keine Geschwister.", "نه، خواهر و برادر ندارم.", "DIALOGUE", "Omar"),
            ("Und wie alt ist deine Schwester?", "و خواهرت چند سال دارد؟", "DIALOGUE", "Nina"),
            ("Sie ist fünf Jahre alt.", "پنج سال دارد.", "DIALOGUE", "Omar"),
            ("Das ist meine Familie.", "این خانواده من است.", "EXAMPLE", ""),
            ("Mein Vater heißt Reza.", "اسم پدرم رضاست.", "EXAMPLE", ""),
            ("Meine Mutter ist Lehrerin.", "مادرم معلم است.", "EXAMPLE", ""),
            ("Ich habe einen Bruder und eine Schwester.", "یک برادر و یک خواهر دارم.", "EXAMPLE", ""),
            ("Mein Bruder ist verheiratet.", "برادرم متأهل است.", "EXAMPLE", ""),
            ("Meine Schwester ist ledig.", "خواهرم مجرد است.", "EXAMPLE", ""),
            ("Wir haben zwei Kinder.", "ما دو فرزند داریم.", "EXAMPLE", ""),
            ("Meine Großeltern wohnen in Isfahan.", "پدربزرگ و مادربزرگم در اصفهان زندگی می‌کنند.", "EXAMPLE", ""),
            (
                "Mein Onkel und meine Tante leben in Hamburg.",
                "عمو و عمه‌ام در هامبورگ زندگی می‌کنند.",
                "EXAMPLE",
                "",
            ),
        ],
    }
)

# --------------------------------------------------------------------- lesson 5
LESSONS.append(
    {
        "order": 5,
        "title": "Beruf und Arbeit",
        "description": "شغل‌ها، محل کار و منفی کردن جمله. English: jobs, workplaces, and how to negate a sentence.",
        "estimated_time": 60,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس می‌گویید چه کار می‌کنید، کجا کار می‌کنید و چه شغلی دارید. همچنین یاد می‌گیرید جمله را منفی کنید.

هدف درس: می‌توانم شغل خودم و دیگران را بگویم و درباره محل کار سؤال بپرسم.

English: Saying what you do for a living, where you work, and negating sentences with nicht and kein.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Berufe",
                """der Arzt – die Ärztin · der Lehrer – die Lehrerin · der Student
der Verkäufer · der Fahrer · der Kellner – die Kellnerin · der Koch
der Ingenieur · der Polizist · der Friseur · der Bäcker · der Doktor
der Beamte · der Kollege · der Chef · die Hausfrau – der Hausmann

der Beruf (شغل) · die Arbeit (کار) · der Job · die Stelle (پست) · die Firma (شرکت) · das Büro (دفتر) · das Praktikum (کارآموزی)
arbeitslos (بیکار) · selbstständig (خودکفا، مستقل)

English: The most common A1 professions, plus words for workplace and employment status.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: Berufe und Negation",
                """بعد از «sein» شغل بدون حرف تعریف می‌آید:
Ich bin Lehrer. (نه: Ich bin ein Lehrer.)
Sie ist Ärztin.

منفی کردن جمله دو راه دارد:
• nicht برای فعل، صفت و اسم معرفه:
Ich arbeite nicht. · Das ist nicht mein Chef.
• kein/keine/kein برای اسم ناشناس:
Ich habe kein Auto. · Sie hat keine Arbeit.

قاعده ساده: اگر در جمله مثبت «ein/eine» یا بدون حرف تعریف بود، در منفی «kein» می‌آید.

English: No article after „sein“ with professions. Negate with „nicht“ (verbs, adjectives) or „kein/keine“ (indefinite nouns).""",
            ),
            (
                "DIALOGUE",
                "Dialog: Was sind Sie von Beruf?",
                """Frau Klein: Was sind Sie von Beruf?  (شغل شما چیست؟)
Herr Ahmadi: Ich bin Ingenieur.  (من مهندسم.)
Frau Klein: Und wo arbeiten Sie?  (و کجا کار می‌کنید؟)
Herr Ahmadi: Ich arbeite bei einer Firma in München.  (در یک شرکت در مونیخ کار می‌کنم.)
Frau Klein: Arbeiten Sie gern dort?  (از کار در آنجا راضی هستید؟)
Herr Ahmadi: Ja, ich arbeite gern.  (بله، با میل کار می‌کنم.)

English: Asking about someone's job and workplace.""",
            ),
            (
                "NOTE",
                "Achtung: machen, arbeiten, tun",
                """این سه فعل شبیه هم نیستند:
• arbeiten: کار کردن، یعنی شغل داشتن: Ich arbeite in einem Büro.
• machen: انجام دادن یک کار مشخص: Was machst du? (چه کار می‌کنی؟)
• tun: معنی نزدیک به machen است ولی در A1 کم به کار می‌رود: Was kann ich tun? (چه کار می‌توانم بکنم؟)

نکته شغلی: برای پرسیدن شغل رسمی می‌گوییم «Was sind Sie von Beruf?» و دوستانه: «Was machst du?»

English: arbeiten = to have a job, machen = to do something, tun = to do (rarer at A1).""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Arbeit und Beruf",
                """Mein Vater ist Arzt.  (پدرم پزشک است.)
Mein Bruder ist Student.  (برادرم دانشجوست.)
Meine Mutter ist Hausfrau.  (مادرم خانه‌دار است.)
Ich habe keine Arbeit.  (کار ندارم.)
Er arbeitet nicht.  (او کار نمی‌کند.)
Die Ärztin arbeitet in Berlin.  (پزشک (زن) در برلین کار می‌کند.)
Der Friseur arbeitet hier.  (آرایشگر اینجا کار می‌کند.)

English: Simple sentences about jobs, unemployment and where people work.""",
            ),
        ],
        "words_new": [
            "Beruf",
            "Arbeit",
            "Job",
            "Stelle",
            "Firma",
            "Chef",
            "Kollege",
            "Büro",
            "Praktikum",
            "arbeitslos",
            "selbstständig",
            "Beamte",
            "Arzt",
            "Ärztin",
            "Lehrer",
            "Lehrerin",
            "Student",
            "Verkäufer",
            "Fahrer",
            "Hausfrau",
            "Hausmann",
            "Kellner",
            "Kellnerin",
            "Koch",
            "Ingenieur",
            "Polizist",
            "Friseur",
            "Bäcker",
            "Doktor",
            "arbeiten",
            "verdienen",
            "machen",
            "nicht",
            "kein",
        ],
        "words_review": [
            "ich",
            "du",
            "Sie",
            "sein",
            "haben",
            "mein",
            "dein",
            "Familie",
            "Vater",
            "Mutter",
            "Frau",
            "Mann",
        ],
        "grammar": [
            "Berufe: kein Artikel nach „sein“",
            "Negation: nicht oder kein?",
            "Unregelmäßige Verben mit Vokalwechsel: fahren, schlafen, essen, nehmen",
        ],
        "sentences": [
            ("Was sind Sie von Beruf?", "شغل شما چیست؟", "DIALOGUE", "Frau Klein"),
            ("Ich bin Ingenieur.", "من مهندسم.", "DIALOGUE", "Herr Ahmadi"),
            ("Und wo arbeiten Sie?", "و کجا کار می‌کنید؟", "DIALOGUE", "Frau Klein"),
            (
                "Ich arbeite bei einer Firma in München.",
                "در یک شرکت در مونیخ کار می‌کنم.",
                "DIALOGUE",
                "Herr Ahmadi",
            ),
            ("Arbeiten Sie gern dort?", "از کار در آنجا راضی هستید؟", "DIALOGUE", "Frau Klein"),
            ("Ja, ich arbeite gern.", "بله، با میل کار می‌کنم.", "DIALOGUE", "Herr Ahmadi"),
            ("Mein Vater ist Arzt.", "پدرم پزشک است.", "EXAMPLE", ""),
            ("Mein Bruder ist Student.", "برادرم دانشجوست.", "EXAMPLE", ""),
            ("Meine Mutter ist Hausfrau.", "مادرم خانه‌دار است.", "EXAMPLE", ""),
            ("Ich habe keine Arbeit.", "کار ندارم.", "EXAMPLE", ""),
            ("Er arbeitet nicht.", "او کار نمی‌کند.", "EXAMPLE", ""),
            ("Die Ärztin arbeitet in Berlin.", "پزشک (زن) در برلین کار می‌کند.", "EXAMPLE", ""),
            ("Der Friseur arbeitet hier.", "آرایشگر اینجا کار می‌کند.", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 6
LESSONS.append(
    {
        "order": 6,
        "title": "Tagesablauf und Uhrzeit",
        "description": "روزمرگی، ساعت، روزهای هفته و فعل‌های جداشدنی. English: daily routine, telling the time and separable verbs.",
        "estimated_time": 75,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس از صبح تا شب خود را توصیف می‌کنید: چه ساعتی بیدار می‌شوید، چه وقت کار می‌کنید و چه وقت می‌خوابید.

هدف درس: می‌توانم ساعت را بگویم و برنامه روزانه‌ام را تعریف کنم.

English: Describing your day from morning to night and telling the time.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Tageszeiten und Wochentage",
                """der Morgen · der Mittag · der Nachmittag · der Abend · die Nacht
der Tag – die Woche – der Monat – das Wochenende · der Wochentag

روزهای هفته:
der Montag · der Dienstag · der Mittwoch · der Donnerstag · der Freitag · der Samstag (یا Sonnabend) · der Sonntag

ساعت و زمان:
die Uhr (ساعت؛ وسیله) · die Stunde (ساعت؛ مدت) · die Minute · halb · das Viertel
früh (زود) · spät (دیر) · pünktlich (وقت‌شناس)

قیدهای تکرار:
immer (همیشه) · oft (اغلب) · manchmal (بعضی وقت‌ها) · selten (به‌ندرت) · nie (هرگز)

English: Times of day, days of the week, time words and adverbs of frequency.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: Uhrzeit, Zeitangaben und trennbare Verben",
                """شکل رسمی: Es ist sieben Uhr. · sieben Uhr fünfzehn (۷:۱۵) · sieben Uhr dreißig (۷:۳۰)
شکل غیررسمی: Viertel nach sieben (۷:۱۵) · halb acht (۷:۳۰) · Viertel vor acht (۷:۴۵)

⚠️ «halb acht» یعنی ۷:۳۰، نه ۸:۳۰! در آلمانی به ساعت بعدی نگاه می‌کنیم.

حرف اضافه‌های زمانی: um sieben Uhr · am Montag · von neun bis fünf

فعل‌های جداشدنی: پیشوند به انتهای جمله می‌رود:
aufstehen → Ich stehe um sechs Uhr auf.
anfangen → Der Kurs fängt um neun an.
fernsehen → Manchmal sehe ich fern.

English: Clock times (formal and informal), time prepositions (um, am, von … bis) and separable verbs.""",
            ),
            (
                "DIALOGUE",
                "Dialog: Wie ist dein Tag?",
                """Kollege: Wie viel Uhr ist es?  (ساعت چند است؟)
Kollegin: Es ist halb acht.  (ساعت هفت و نیم است.)
Kollege: Wann stehst du auf?  (چه وقت بیدار می‌شوی؟)
Kollegin: Ich stehe um sechs Uhr auf.  (ساعت شش بیدار می‌شوم.)
Kollege: Und wann fängst du an?  (و چه وقت شروع می‌کنی؟)
Kollegin: Um acht. Ich arbeite von acht bis vier.  (ساعت هشت. از هشت تا چهار کار می‌کنم.)

English: Asking the time and talking about when you get up and start work.""",
            ),
            (
                "NOTE",
                "Achtung: trennbare Verben",
                """پیشوندِ فعل‌های جداشدنی در جمله خبری جدا می‌شود و به آخر می‌رود:
aufstehen → Ich stehe auf.
aufwachen → Ich wache auf.
einschlafen → Ich schlafe ein.

فعل‌های جداشدنی پرکاربرد A1:
aufstehen · aufwachen · einschlafen · anfangen · aufhören · einkaufen · einladen · anrufen · mitkommen · mitnehmen · zuhören · fernsehen

در کتاب لغت این فعل‌ها با خط جداکننده نوشته می‌شوند: auf|stehen

English: Separable verbs split in a main clause – the prefix moves to the end of the sentence.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: mein Tag",
                """Ich frühstücke um halb sieben.  (ساعت شش و نیم صبحانه می‌خورم.)
Zuerst dusche ich, dann frühstücke ich.  (اول دوش می‌گیرم، بعد صبحانه می‌خورم.)
Am Montag arbeite ich nicht.  (دوشنبه کار نمی‌کنم.)
Am Wochenende schlafe ich bis zehn Uhr.  (آخر هفته تا ساعت ده می‌خوابم.)
Ich fange um neun Uhr an.  (ساعت نه شروع می‌کنم.)
Manchmal sehe ich fern.  (بعضی وقت‌ها تلویزیون تماشا می‌کنم.)
Er kommt immer pünktlich.  (او همیشه وقت‌شناس است.)
Er kommt nie zu spät.  (او هرگز دیر نمی‌آید.)
Ich schlafe um elf Uhr ein.  (ساعت یازده به خواب می‌روم.)

English: A typical day, with times, frequency words and separable verbs.""",
            ),
        ],
        "words_new": [
            "aufstehen",
            "aufwachen",
            "einschlafen",
            "anfangen",
            "aufhören",
            "duschen",
            "sich waschen",
            "frühstücken",
            "fernsehen",
            "schlafen",
            "Tag",
            "Morgen",
            "Mittag",
            "Nachmittag",
            "Abend",
            "Nacht",
            "Montag",
            "Dienstag",
            "Mittwoch",
            "Donnerstag",
            "Freitag",
            "Samstag",
            "Sonntag",
            "Woche",
            "Wochenende",
            "Wochentag",
            "Uhr",
            "Stunde",
            "Minute",
            "halb",
            "Viertel",
            "früh",
            "spät",
            "pünktlich",
            "immer",
            "oft",
            "manchmal",
            "selten",
            "nie",
            "zuerst",
            "dann",
        ],
        "words_review": [
            "ich",
            "du",
            "Sie",
            "sein",
            "haben",
            "arbeiten",
            "machen",
            "nicht",
            "Beruf",
            "Arbeit",
        ],
        "grammar": [
            "Trennbare Verben im Präsens",
            "Die Uhrzeit: formell und informell",
            "Zeitangaben: um, am, von … bis",
            "Satzstellung mit Zeit- und Ortsangaben",
        ],
        "sentences": [
            ("Wie viel Uhr ist es?", "ساعت چند است؟", "DIALOGUE", "Kollege"),
            ("Es ist halb acht.", "ساعت هفت و نیم است.", "DIALOGUE", "Kollegin"),
            ("Wann stehst du auf?", "چه وقت بیدار می‌شوی؟", "DIALOGUE", "Kollege"),
            ("Ich stehe um sechs Uhr auf.", "ساعت شش بیدار می‌شوم.", "DIALOGUE", "Kollegin"),
            ("Und wann fängst du an?", "و چه وقت شروع می‌کنی؟", "DIALOGUE", "Kollege"),
            (
                "Um acht. Ich arbeite von acht bis vier.",
                "ساعت هشت. از هشت تا چهار کار می‌کنم.",
                "DIALOGUE",
                "Kollegin",
            ),
            ("Ich frühstücke um halb sieben.", "ساعت شش و نیم صبحانه می‌خورم.", "EXAMPLE", ""),
            ("Zuerst dusche ich, dann frühstücke ich.", "اول دوش می‌گیرم، بعد صبحانه می‌خورم.", "EXAMPLE", ""),
            ("Am Montag arbeite ich nicht.", "دوشنبه کار نمی‌کنم.", "EXAMPLE", ""),
            ("Am Wochenende schlafe ich bis zehn Uhr.", "آخر هفته تا ساعت ده می‌خوابم.", "EXAMPLE", ""),
            ("Ich fange um neun Uhr an.", "ساعت نه شروع می‌کنم.", "EXAMPLE", ""),
            ("Manchmal sehe ich fern.", "بعضی وقت‌ها تلویزیون تماشا می‌کنم.", "EXAMPLE", ""),
            ("Er kommt immer pünktlich.", "او همیشه وقت‌شناس است.", "EXAMPLE", ""),
            ("Er kommt nie zu spät.", "او هرگز دیر نمی‌آید.", "EXAMPLE", ""),
            ("Ich schlafe um elf Uhr ein.", "ساعت یازده به خواب می‌روم.", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 7
LESSONS.append(
    {
        "order": 7,
        "title": "Essen und Trinken",
        "description": "غذا، نوشیدنی و علاقه‌ها. English: food, drinks and saying what you like eating.",
        "estimated_time": 65,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس غذاها و نوشیدنی‌های روزمره را یاد می‌گیرید و می‌گویید چه چیزی را دوست دارید بخورید یا بنوشید.

هدف درس: می‌توانم بگویم چه می‌خورم و چه می‌نوشم و چه چیزی را بیشتر دوست دارم.

English: Everyday food and drink, plus saying what you like to eat and drink.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Essen und Getränke",
                """وعده‌های غذا: das Frühstück (صبحانه) · das Mittagessen (ناهار) · das Abendessen (شام) · das Essen (غذا)
غذا: das Brot · das Brötchen · die Butter · der Käse · das Ei · das Fleisch · der Fisch · die Wurst
der Reis · die Nudeln · die Suppe · der Salat · das Gemüse
der Kuchen · die Torte · das Eis · die Schokolade
نوشیدنی: das Wasser · die Milch · der Kaffee · der Tee · der Saft · der Orangensaft · das Bier · der Wein · das Getränk
چاشنی: das Salz · der Zucker

Hunger haben (گرسنه بودن) · Durst haben (تشنه بودن) · Appetit haben (اشتها داشتن)

English: Meals, food, drinks and the expressions Hunger/Durst/Appetit haben.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: Akkusativ und gern",
                """مفعول مستقیم در حالت akkusativ است. فقط مذکر تغییر می‌کند:
der → den · ein → einen · die/das/die bleiben gleich
Ich esse einen Apfel. · Ich trinke den Kaffee. · Ich nehme das Brot.

برای علاقه از «gern» استفاده می‌کنیم و بعد از آن فعل می‌آید:
Ich esse gern Fisch. (ماهی دوست دارم بخورم.)
Im Vergleich: gern → lieber → am liebsten
Ich trinke gern Tee, am liebsten trinke ich Wasser.

English: Accusative objects (der → den, ein → einen) and the ladder gern – lieber – am liebsten.""",
            ),
            (
                "DIALOGUE",
                "Dialog: Hunger am Abend",
                """Lea: Ich habe Hunger. Und du?  (گرسنه‌ام. تو؟)
Ben: Ich auch. Ich mache eine Suppe.  (من هم. یک سوپ درست می‌کنم.)
Lea: Isst du gern Suppe?  (سوپ دوست داری بخوری؟)
Ben: Ja, sehr gern. Am liebsten esse ich Salat.  (بله، خیلی دوست دارم. از همه بیشتر سالاد دوست دارم.)
Lea: Dann koche ich Reis und Fisch.  (پس من برنج و ماهی می‌پزم.)
Ben: Guten Appetit!  (نوش جان!)

English: Talking about being hungry and about favourite food.""",
            ),
            (
                "NOTE",
                "Achtung: mögen oder gern?",
                """این دو کلمه را قاطی نکنید:
• mögen + اسم: Ich mag Fisch. (ماهی دوست دارم.)
• gern + فعل: Ich esse gern Fisch. (ماهی دوست دارم بخورم.)

شکل قوی‌تر «gern haben» است: Ich habe Fisch gern.

نکته: Hunger و Durst اسم هستند، پس با «haben» می‌آیند:
Ich habe Hunger. · Hast du Durst?

English: mögen takes a noun, gern goes with a verb. Hunger and Durst combine with „haben“.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Ich esse …",
                """Was isst du gern?  (چه چیزی دوست داری بخوری؟)
Ich esse gern Reis mit Fleisch.  (برنج با گوشت دوست دارم بخورم.)
Ich trinke gern Tee.  (چای دوست دارم بنوشم.)
Am liebsten trinke ich Wasser.  (از همه بیشتر آب دوست دارم بنوشم.)
Zum Frühstück esse ich Brot mit Käse.  (برای صبحانه نان با پنیر می‌خورم.)
Meine Frau isst kein Fleisch.  (همسرم گوشت نمی‌خورد.)
Ich habe Hunger.  (گرسنه‌ام.)

English: Saying what you eat and drink, and what you never eat.""",
            ),
        ],
        "words_new": [
            "essen",
            "trinken",
            "kochen",
            "Essen",
            "Getränk",
            "Frühstück",
            "Mittagessen",
            "Abendessen",
            "Hunger",
            "Durst",
            "Appetit",
            "Brot",
            "Brötchen",
            "Butter",
            "Käse",
            "Ei",
            "Milch",
            "Kaffee",
            "Tee",
            "Wasser",
            "Saft",
            "Orangensaft",
            "Bier",
            "Wein",
            "Fleisch",
            "Fisch",
            "Wurst",
            "Zucker",
            "Salz",
            "Reis",
            "Nudeln",
            "Suppe",
            "Salat",
            "Kuchen",
            "Torte",
            "Eis",
            "Schokolade",
            "gern",
            "lieber",
            "mögen",
            "gern haben",
        ],
        "words_review": [
            "ich",
            "du",
            "Sie",
            "sein",
            "haben",
            "nicht",
            "kein",
            "Morgen",
            "Mittag",
            "Abend",
            "Nacht",
            "immer",
            "oft",
            "manchmal",
            "nie",
        ],
        "grammar": [
            "Der Akkusativ: den, die, das, einen, eine",
            "Verben mit Akkusativ: essen, trinken, nehmen, brauchen",
            "gern, lieber, am liebsten",
        ],
        "sentences": [
            ("Ich habe Hunger. Und du?", "گرسنه‌ام. تو؟", "DIALOGUE", "Lea"),
            ("Ich auch. Ich mache eine Suppe.", "من هم. یک سوپ درست می‌کنم.", "DIALOGUE", "Ben"),
            ("Isst du gern Suppe?", "سوپ دوست داری بخوری؟", "DIALOGUE", "Lea"),
            (
                "Ja, sehr gern. Am liebsten esse ich Salat.",
                "بله، خیلی دوست دارم. از همه بیشتر سالاد دوست دارم.",
                "DIALOGUE",
                "Ben",
            ),
            ("Dann koche ich Reis und Fisch.", "پس من برنج و ماهی می‌پزم.", "DIALOGUE", "Lea"),
            ("Guten Appetit!", "نوش جان!", "DIALOGUE", "Ben"),
            ("Was isst du gern?", "چه چیزی دوست داری بخوری؟", "EXAMPLE", ""),
            ("Ich esse gern Reis mit Fleisch.", "برنج با گوشت دوست دارم بخورم.", "EXAMPLE", ""),
            ("Ich trinke gern Tee.", "چای دوست دارم بنوشم.", "EXAMPLE", ""),
            ("Am liebsten trinke ich Wasser.", "از همه بیشتر آب دوست دارم بنوشم.", "EXAMPLE", ""),
            (
                "Zum Frühstück esse ich Brot mit Käse.",
                "برای صبحانه نان با پنیر می‌خورم.",
                "EXAMPLE",
                "",
            ),
            ("Meine Frau isst kein Fleisch.", "همسرم گوشت نمی‌خورد.", "EXAMPLE", ""),
            ("Ich habe Durst.", "تشنه‌ام.", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 8
LESSONS.append(
    {
        "order": 8,
        "title": "Im Restaurant und im Café",
        "description": "سفارش دادن، صورت‌حساب و انعام. English: ordering, paying and tipping.",
        "estimated_time": 65,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس وارد یک رستوران می‌شوید، سفارش می‌دهید، سؤال می‌پرسید و حساب می‌کنید. این درس کاملاً مکالمه‌محور است.

هدف درس: می‌توانم در رستوران سفارش بدهم و حساب کنم.

English: A fully conversation-based lesson: entering a restaurant, ordering, asking questions and paying.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: im Restaurant",
                """das Restaurant · das Lokal · das Café
die Speisekarte (منو) · der Kellner – die Kellnerin · der Gast
die Rechnung (صورت‌حساب) · die Quittung (رسید) · die Kasse (صندوق) · das Trinkgeld (انعام)
der Teller · die Tasse · das Glas · die Flasche · der Löffel · die Gabel · das Messer · die Serviette
der Schinken · das Hähnchen · das Öl · das Gemüse
lecker · süß · sauer · bitter

English: Restaurant vocabulary: menu, staff, dishes, cutlery and bill.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: möchten und höfliche Fragen",
                """«möchten» شکل مؤدبانه «خواستن» است و بعد از آن اسم در حالت akkusativ می‌آید:
ich möchte · du möchtest · er/sie/es möchte · wir möchten · ihr möchtet · sie/Sie möchten
Ich möchte einen Kaffee, bitte.
Ich möchte eine Suppe und einen Salat.

جمله‌های ثابت رستوران:
Die Speisekarte, bitte. · Ich möchte bestellen. · Die Rechnung, bitte. · Stimmt so.

English: The polite form „möchten“ with an accusative object, plus the fixed phrases used in a restaurant.""",
            ),
            (
                "DIALOGUE",
                "Dialog: im Restaurant",
                """Gast: Die Speisekarte, bitte.  (منو لطفاً.)
Kellner: Hier bitte. Möchten Sie schon bestellen?  (بفرمایید. می‌خواهید سفارش بدهید؟)
Gast: Ja, ich möchte eine Suppe und einen Salat.  (بله، یک سوپ و یک سالاد می‌خواهم.)
Kellner: Und was möchten Sie trinken?  (و چه می‌نوشید؟)
Gast: Ein Wasser, bitte.  (یک آب لطفاً.)
Kellner: Möchten Sie noch etwas?  (چیز دیگری میل دارید؟)
Gast: Nein, danke. Die Rechnung, bitte.  (نه ممنون. صورت‌حساب لطفاً.)
Kellner: Das macht achtzehn Euro fünfzig.  (می‌شود هجده یورو و پنجاه.)
Gast: Stimmt so.  (باقی‌اش برایتان.)

English: A complete restaurant scene from the menu to the tip.""",
            ),
            (
                "NOTE",
                "Achtung: Rechnung, Quittung, Trinkgeld",
                """این سه واژه را با هم قاطی نکنید:
die Rechnung = صورت‌حساب رستوران یا مغازه
die Quittung = رسید رسمی (مثلاً برای مغازه که معمولاً لازم دارید)
das Trinkgeld = انعام؛ در آلمان معمولاً ۵ تا ۱۰ درصد

جمله‌های کلیدی هنگام پرداخت:
Zusammen oder getrennt? (با هم یا جدا حساب کنیم؟)
Ich möchte bezahlen. · Kann ich mit Karte bezahlen? (می‌توانم با کارت بپردازم؟)

English: Rechnung (bill) vs Quittung (receipt) vs Trinkgeld (tip, usually 5–10 % in Germany).""",
            ),
            (
                "EXAMPLE",
                "Beispiele: bestellen und bezahlen",
                """Der Kellner bringt die Rechnung.  (پیشخدمت صورت‌حساب را می‌آورد.)
Ich nehme die Suppe.  (سوپ را می‌گیرم.)
Was empfehlen Sie?  (چه پیشنهاد می‌کنید؟)
Der Salat ist sehr lecker.  (سالاد خیلی خوشمزه است.)
Der Kuchen ist süß.  (کیک شیرین است.)
Zusammen oder getrennt?  (با هم یا جدا؟)
Ich möchte bezahlen.  (می‌خواهم حساب کنم.)

English: Useful sentences for ordering, recommending and paying.""",
            ),
        ],
        "words_new": [
            "möchten",
            "bestellen",
            "bezahlen",
            "zahlen",
            "Rechnung",
            "Speisekarte",
            "Restaurant",
            "Lokal",
            "Café",
            "Trinkgeld",
            "Quittung",
            "Kasse",
            "Serviette",
            "Löffel",
            "Gabel",
            "Messer",
            "Teller",
            "Tasse",
            "Glas",
            "Flasche",
            "bringen",
            "nehmen",
            "geben",
            "empfehlen",
            "Schinken",
            "Öl",
            "Hähnchen",
            "Gemüse",
            "lecker",
            "süß",
            "sauer",
            "bitter",
        ],
        "words_review": [
            "Kellner",
            "Kellnerin",
            "Koch",
            "essen",
            "trinken",
            "Essen",
            "Brot",
            "Brötchen",
            "Suppe",
            "Salat",
            "Kaffee",
            "Tee",
            "Wasser",
            "Bier",
            "Wein",
            "Saft",
            "Kuchen",
            "Hunger",
            "Durst",
            "gern",
            "lieber",
        ],
        "grammar": [
            "möchten: Wünsche und höfliche Bitten",
            "Im Restaurant: bestellen, bezahlen, Trinkgeld",
        ],
        "sentences": [
            ("Die Speisekarte, bitte.", "منو لطفاً.", "DIALOGUE", "Gast"),
            (
                "Hier bitte. Möchten Sie schon bestellen?",
                "بفرمایید. می‌خواهید سفارش بدهید؟",
                "DIALOGUE",
                "Kellner",
            ),
            (
                "Ja, ich möchte eine Suppe und einen Salat.",
                "بله، یک سوپ و یک سالاد می‌خواهم.",
                "DIALOGUE",
                "Gast",
            ),
            ("Und was möchten Sie trinken?", "و چه می‌نوشید؟", "DIALOGUE", "Kellner"),
            ("Ein Wasser, bitte.", "یک آب لطفاً.", "DIALOGUE", "Gast"),
            ("Möchten Sie noch etwas?", "چیز دیگری میل دارید؟", "DIALOGUE", "Kellner"),
            ("Nein, danke. Die Rechnung, bitte.", "نه ممنون. صورت‌حساب لطفاً.", "DIALOGUE", "Gast"),
            (
                "Das macht achtzehn Euro fünfzig.",
                "می‌شود هجده یورو و پنجاه.",
                "DIALOGUE",
                "Kellner",
            ),
            ("Stimmt so.", "باقی‌اش برایتان.", "DIALOGUE", "Gast"),
            ("Der Kellner bringt die Rechnung.", "پیشخدمت صورت‌حساب را می‌آورد.", "EXAMPLE", ""),
            ("Ich nehme die Suppe.", "سوپ را می‌گیرم.", "EXAMPLE", ""),
            ("Was empfehlen Sie?", "چه پیشنهاد می‌کنید؟", "EXAMPLE", ""),
            ("Der Salat ist sehr lecker.", "سالاد خیلی خوشمزه است.", "EXAMPLE", ""),
            ("Zusammen oder getrennt?", "با هم یا جدا؟", "EXAMPLE", ""),
            ("Ich möchte bezahlen.", "می‌خواهم حساب کنم.", "EXAMPLE", ""),
        ],
    }
)

# --------------------------------------------------------------------- lesson 9
LESSONS.append(
    {
        "order": 9,
        "title": "Einkaufen und Preise",
        "description": "خرید کردن، مقدار و پرداخت. English: shopping, quantities and paying.",
        "estimated_time": 65,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس خرید می‌کنید: مغازه‌ها را می‌شناسید، مقدار می‌خواهید، قیمت را می‌پرسید و پرداخت می‌کنید.

هدف درس: می‌توانم خرید کنم، مقدار بخواهم و بفهمم چند باید بپردازم.

English: You learn to shop: name the shops, ask for quantities, ask prices and pay.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Geschäfte und Mengen",
                """مغازه‌ها: der Supermarkt · der Markt · der Laden · das Geschäft · der Kiosk · die Bäckerei · die Apotheke · die Post · die Bank
der Preis (قیمت) · das Angebot (پیشنهاد، تخفیف) · das Geld · das Kilo · das Stück · die Karte · die Kreditkarte
billig (ارزان) · günstig (به‌صرفه) · teuer (گران) · bar (نقدی)

میوه و سبزی: das Obst · der Apfel · die Banane · die Orange · die Zitrone · die Traube · die Erdbeere · die Birne
die Tomate · die Kartoffel · die Gurke · die Lebensmittel

ein Kilo Tomaten · ein halbes Kilo Käse · 100 Gramm Schinken · ein Stück Kuchen

English: Shops, prices, quantities, fruit and vegetables.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: Akkusativ, Mengen und der Imperativ mit Sie",
                """در حالت akkusativ فقط مذکر تغییر می‌کند:
der → den · ein → einen (die/das/die bleiben gleich)
Ich nehme den Bus. · Ich kaufe einen Apfel. · Ich bezahle das Brot.

مقدار + اسم: ein Kilo · eine Flasche · ein Glas · ein Stück · eine Tasse
Ich möchte ein Kilo Kartoffeln, bitte.

درخواست مؤدبانه (Imperativ mit Sie): فعل + Sie
Geben Sie mir bitte eine Quittung. · Nehmen Sie den Bus 10. · Warten Sie bitte hier.

English: Accusative articles, quantity expressions and the polite imperative with „Sie“.""",
            ),
            (
                "DIALOGUE",
                "Dialog: im Supermarkt",
                """Verkäufer: Guten Tag! Was möchten Sie?  (روز بخیر! چه می‌خواهید؟)
Kundin: Ich möchte ein Kilo Kartoffeln und ein Kilo Tomaten.  (یک کیلو سیب‌زمینی و یک کیلو گوجه می‌خواهم.)
Verkäufer: Möchten Sie auch Obst?  (میوه هم میل دارید؟)
Kundin: Ja, drei Bananen und eine Orange, bitte.  (بله، سه موز و یک پرتقال لطفاً.)
Verkäufer: Das macht neun Euro zwanzig.  (می‌شود نه یورو و بیست.)
Kundin: Hier bitte.  (بفرمایید.)

English: A short shopping dialogue with quantities and a price.""",
            ),
            (
                "NOTE",
                "Achtung: bar, Karte, Quittung",
                """پرداخت:
Bar oder mit Karte? (نقدی یا با کارت؟)
Ich bezahle bar. (نقدی می‌پردازم.) · Ich bezahle mit Karte.

Kann ich mit Karte bezahlen? یک جمله ثابت بسیار پرکاربرد است؛ در درس ۱۳ فعل «können» را کامل یاد می‌گیرید.

رسید: در آلمان برای خریدهایی که ممکن است پس بدهید، Quittung بگیرید.
در مغازه‌های بزرگ: an der Kasse (در صندوق) پرداخت می‌کنید.

English: Bar oder mit Karte? plus the fixed request „Kann ich mit Karte bezahlen?“.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Preise und Mengen",
                """Was kostet das?  (این چند است؟)
Das kostet drei Euro neunzig.  (این سه یورو و نود است.)
Das ist zu teuer.  (این خیلی گران است.)
Das ist günstig.  (این به‌صرفه است.)
Ich kaufe ein Brot und zwei Brötchen.  (یک نان و دو نان کوچک می‌خرم.)
Bitte geben Sie mir eine Quittung.  (لطفاً یک رسید به من بدهید.)
Wo ist die Kasse, bitte?  (صندوق کجاست، لطفاً؟)

English: Asking for prices and quantities, and asking where the checkout is.""",
            ),
        ],
        "words_new": [
            "einkaufen",
            "kaufen",
            "verkaufen",
            "kosten",
            "Geschäft",
            "Laden",
            "Supermarkt",
            "Markt",
            "Kiosk",
            "Bäckerei",
            "Apotheke",
            "Post",
            "Bank",
            "Preis",
            "Angebot",
            "Geld",
            "Cent",
            "Million",
            "Milliarde",
            "Kilo",
            "Stück",
            "Karte",
            "Kreditkarte",
            "billig",
            "teuer",
            "günstig",
            "bar",
            "Obst",
            "Apfel",
            "Banane",
            "Orange",
            "Zitrone",
            "Traube",
            "Erdbeere",
            "Birne",
            "Tomate",
            "Kartoffel",
            "Gurke",
            "Lebensmittel",
            "Tasche",
        ],
        "words_review": [
            "Kasse",
            "Quittung",
            "Rechnung",
            "Euro",
            "wie viel",
            "Brot",
            "Brötchen",
            "Käse",
            "Milch",
            "möchten",
            "nehmen",
            "geben",
        ],
        "grammar": [
            "Der Akkusativ mit dem bestimmten Artikel: den, die, das",
            "Mengen und Verpackungen: ein Kilo, eine Flasche, ein Stück",
            "Imperativ mit Sie",
        ],
        "sentences": [
            ("Guten Tag! Was möchten Sie?", "روز بخیر! چه می‌خواهید؟", "DIALOGUE", "Verkäufer"),
            (
                "Ich möchte ein Kilo Kartoffeln und ein Kilo Tomaten.",
                "یک کیلو سیب‌زمینی و یک کیلو گوجه می‌خواهم.",
                "DIALOGUE",
                "Kundin",
            ),
            ("Möchten Sie auch Obst?", "میوه هم میل دارید؟", "DIALOGUE", "Verkäufer"),
            (
                "Ja, drei Bananen und eine Orange, bitte.",
                "بله، سه موز و یک پرتقال لطفاً.",
                "DIALOGUE",
                "Kundin",
            ),
            ("Das macht neun Euro zwanzig.", "می‌شود نه یورو و بیست.", "DIALOGUE", "Verkäufer"),
            ("Hier bitte.", "بفرمایید.", "DIALOGUE", "Kundin"),
            ("Was kostet das?", "این چند است؟", "EXAMPLE", ""),
            ("Das kostet drei Euro neunzig.", "این سه یورو و نود است.", "EXAMPLE", ""),
            ("Das ist zu teuer.", "این خیلی گران است.", "EXAMPLE", ""),
            ("Ich kaufe ein Brot und zwei Brötchen.", "یک نان و دو نان کوچک می‌خرم.", "EXAMPLE", ""),
            ("Ich bezahle bar.", "نقدی می‌پردازم.", "EXAMPLE", ""),
            ("Kann ich mit Karte bezahlen?", "می‌توانم با کارت بپردازم؟", "EXAMPLE", ""),
            ("Bitte geben Sie mir eine Quittung.", "لطفاً یک رسید به من بدهید.", "EXAMPLE", ""),
            ("Wo ist die Kasse, bitte?", "صندوق کجاست، لطفاً؟", "EXAMPLE", ""),
        ],
    }
)

# -------------------------------------------------------------------- lesson 10
LESSONS.append(
    {
        "order": 10,
        "title": "Kleidung und Farben",
        "description": "لباس، رنگ‌ها و اندازه. English: clothes, colours, sizes and saying what you like.",
        "estimated_time": 65,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس لباس‌ها و رنگ‌ها را یاد می‌گیرید، در مغازه لباس اندازه می‌خواهید و می‌گویید چه چیزی به شما می‌آید یا خوشتان می‌آید.

هدف درس: می‌توانم لباس بخرم و بگویم چه رنگ و اندازه‌ای می‌خواهم.

English: Buying clothes: saying your size, naming colours and expressing what you like.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Kleidung und Farben",
                """لباس‌ها: die Kleidung · das Kleid · die Hose · der Rock · das Hemd · die Bluse · die Jacke · der Mantel
der Pullover · das T-Shirt · der Schuh · die Socke · die Mütze · der Hut · der Schal · der Handschuh · der Gürtel
der Ring · die Brille · die Tasche · die Größe

رنگ‌ها: rot · blau · gelb · grün · schwarz · weiß · braun · grau · orange · rosa · lila · bunt

فعلي‌های مربوط: anziehen (پوشیدن) · ausziehen (درآوردن) · tragen (به تن داشتن) · passen (اندازه بودن)

English: Clothing, accessories, colours and the verbs anziehen, ausziehen, tragen, passen.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: gefallen + Dativ, Farben und dieser",
                """فعل «gefallen» شخص را در حالت dativ می‌گیرد:
mir · dir · ihm · ihr · uns · euch · ihnen · Ihnen
Das gefällt mir. · Die Schuhe gefallen mir nicht.

صفت قبل از اسم پایانه می‌گیرد:
ein rotes Hemd · eine rote Jacke · der rote Rock · die blauen Schuhe

اشاره به چیز نزدیک:
dieser Tisch · diese Lampe · dieses Hemd · diese Schuhe (در akkusativ: diesen Tisch)

English: „gefallen“ with the dative, adjective endings before nouns, and the demonstrative dieser/diese/dieses.""",
            ),
            (
                "DIALOGUE",
                "Dialog: im Geschäft",
                """Verkäuferin: Guten Tag! Was suchen Sie?  (روز بخیر! دنبال چه هستید؟)
Kundin: Ich suche ein blaues Hemd.  (دنبال یک پیراهن آبی هستم.)
Verkäuferin: Welche Größe haben Sie?  (چه اندازه‌ای دارید؟)
Kundin: Größe 40.  (اندازه ۴۰.)
Verkäuferin: Hier, bitte.  (بفرمایید.)
Kundin: Das gefällt mir. Der Rock passt mir nicht, aber das Hemd ist gut.  (این را دوست دارم. دامن اندازه‌ام نیست، ولی پیراهن خوب است.)

English: Shopping for clothes: size, colour and whether something fits.""",
            ),
            (
                "NOTE",
                "Achtung: anziehen, ausziehen, tragen",
                """این سه فعل نزدیک‌اند ولی یکی نیستند:
anziehen = لباس را به تن کردن (عمل): Zieh die Jacke an!
ausziehen = لباس را درآوردن: Zieh die Schuhe aus!
tragen = به تن داشتن (حالت): Ich trage eine blaue Hose.

شکل انعکاسی: sich anziehen (لباس پوشیدن) · sich ausziehen (لباس درآوردن)

gefallen یا passen؟
Das gefällt mir = خوشم می‌آید (سلیقه)
Das passt mir = اندازه‌ام است (اندازه)

English: anziehen/ausziehen are actions, tragen is a state; gefallen is taste, passen is fit.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: Kleidung",
                """Das gefällt mir.  (این را دوست دارم.)
Die Jacke gefällt mir nicht.  (ژاکت را دوست ندارم.)
Gefällt dir die Farbe?  (رنگ را دوست داری؟)
Ich trage eine blaue Hose.  (شلوار آبی می‌پوشم.)
Ich nehme das weiße Hemd.  (پیراهن سفید را می‌خرم.)
Der Mantel ist zu klein.  (پالتو خیلی کوچک است.)
Die Socken sind bunt.  (جوراب‌ها رنگارنگ هستند.)

English: Colours, sizes and likes.""",
            ),
        ],
        "words_new": [
            "Kleidung",
            "Kleid",
            "Hose",
            "Rock",
            "Hemd",
            "Bluse",
            "Jacke",
            "Mantel",
            "Pullover",
            "T-Shirt",
            "Schuh",
            "Socke",
            "Mütze",
            "Hut",
            "Schal",
            "Handschuh",
            "Gürtel",
            "Brille",
            "Ring",
            "Größe",
            "Farbe",
            "rot",
            "blau",
            "gelb",
            "grün",
            "schwarz",
            "weiß",
            "braun",
            "grau",
            "orange",
            "rosa",
            "lila",
            "bunt",
            "gefallen",
            "dieser",
            "welcher",
            "anziehen",
            "ausziehen",
            "sich anziehen",
            "sich ausziehen",
            "tragen",
            "passen",
        ],
        "words_review": [
            "kaufen",
            "verkaufen",
            "teuer",
            "billig",
            "günstig",
            "Karte",
            "Tasche",
            "Preis",
            "gern",
        ],
        "grammar": [
            "gefallen + Dativ: Das gefällt mir",
            "Farben und Adjektive vor dem Nomen (Grundlagen)",
            "dieser, diese, dieses",
            "Der Imperativ mit du",
        ],
        "sentences": [
            ("Guten Tag! Was suchen Sie?", "روز بخیر! دنبال چه هستید؟", "DIALOGUE", "Verkäuferin"),
            ("Ich suche ein blaues Hemd.", "دنبال یک پیراهن آبی هستم.", "DIALOGUE", "Kundin"),
            ("Welche Größe haben Sie?", "چه اندازه‌ای دارید؟", "DIALOGUE", "Verkäuferin"),
            ("Größe 40.", "اندازه ۴۰.", "DIALOGUE", "Kundin"),
            (
                "Das gefällt mir. Der Rock passt mir nicht, aber das Hemd ist gut.",
                "این را دوست دارم. دامن اندازه‌ام نیست، ولی پیراهن خوب است.",
                "DIALOGUE",
                "Kundin",
            ),
            ("Das gefällt mir.", "این را دوست دارم.", "EXAMPLE", ""),
            ("Die Jacke gefällt mir nicht.", "ژاکت را دوست ندارم.", "EXAMPLE", ""),
            ("Gefällt dir die Farbe?", "رنگ را دوست داری؟", "EXAMPLE", ""),
            ("Die rote Jacke ist zu teuer.", "ژاکت قرمز خیلی گران است.", "EXAMPLE", ""),
            ("Ich trage eine blaue Hose.", "شلوار آبی می‌پوشم.", "EXAMPLE", ""),
            ("Ich nehme das weiße Hemd.", "پیراهن سفید را می‌خرم.", "EXAMPLE", ""),
            ("Ich brauche einen Mantel.", "یک پالتو لازم دارم.", "EXAMPLE", ""),
            ("Diese Schuhe sind zu klein.", "این کفش‌ها خیلی کوچک هستند.", "EXAMPLE", ""),
            ("Die Socken sind bunt.", "جوراب‌ها رنگارنگ هستند.", "EXAMPLE", ""),
        ],
    }
)

# -------------------------------------------------------------------- lesson 11
LESSONS.append(
    {
        "order": 11,
        "title": "Wohnen und Möbel",
        "description": "خانه، اتاق‌ها، اثاثیه و اجاره. English: home, rooms, furniture and rent.",
        "estimated_time": 70,
        "contents": [
            (
                "EXPLANATION",
                "Was lernst du in dieser Lektion?",
                """در این درس خانه‌تان را توصیف می‌کنید: چند اتاق دارد، چه اثاثیه‌ای دارد و اجاره‌اش چقدر است. همچنین یاد می‌گیرید بگویید چیزی کجاست.

هدف درس: می‌توانم آپارتمان یا خانه‌ام را توصیف کنم و جای وسایل را بگویم.

English: Describing your home: rooms, furniture, rent and where things are.""",
            ),
            (
                "VOCABULARY",
                "Wortschatz: Wohnung und Möbel",
                """خانه: die Wohnung · das Haus · das Zimmer · das Wohnzimmer · das Schlafzimmer · die Küche · das Bad · die Toilette
der Balkon · der Keller · der Garten · der Aufzug · die Treppe · die Tür · das Fenster · die Wand · der Boden · der Schlüssel

اثاثیه: die Möbel · der Tisch · der Stuhl · das Sofa · der Sessel · das Bett · der Schrank · das Regal · die Lampe
der Teppich · der Spiegel · das Kissen · die Badewanne · die Dusche · der Fernseher · der Herd · der Kühlschrank

اجاره: die Miete · der Vermieter · mieten · vermieten

English: Rooms, furniture, household appliances and words about renting.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: Präpositionen des Ortes und es gibt",
                """برای گفتن «کجاست» بعد از این حروف اضافه حالت dativ می‌آید:
in · an · auf · unter · über · neben · zwischen · vor · hinter
der → dem · die → der · das → dem · die (جمع) → den
Das Buch liegt auf dem Tisch. · Die Lampe steht neben dem Sofa.

«es gibt» یعنی «هست/وجود دارد» و بعد از آن akkusativ می‌آید:
Es gibt einen Balkon. · In der Küche gibt es einen Herd.

حرکت یا جای ثابت؟
wo? (جای ثابت) → dativ: Das Buch liegt auf dem Tisch.
wohin? (حرکت) → akkusativ: Ich lege das Buch auf den Tisch.

English: Place prepositions with the dative, „es gibt“ + accusative, and wo/wohin with liegen/legen and stehen/stellen.""",
            ),
            (
                "DIALOGUE",
                "Dialog: eine Wohnung suchen",
                """Interessent: Guten Tag. Ich suche eine Wohnung.  (روز بخیر. دنبال یک آپارتمان هستم.)
Vermieter: Ja, gern. Die Wohnung hat zwei Zimmer.  (بله، حتماً. آپارتمان دو اتاق دارد.)
Interessent: Hat die Wohnung einen Balkon?  (آپارتمان بالکن دارد؟)
Vermieter: Ja, und auch einen Keller.  (بله، و یک زیرزمین هم دارد.)
Interessent: Was kostet die Miete?  (اجاره چقدر است؟)
Vermieter: Die Miete kostet 600 Euro.  (اجاره ۶۰۰ یورو است.)

English: Asking about a flat: rooms, balcony, cellar and rent.""",
            ),
            (
                "NOTE",
                "Achtung: stehen oder liegen?",
                """آلمانی به شکل وسایل دقت می‌کند:
• stehen / stellen برای چیزهای ایستاده: Die Lampe steht auf dem Tisch. / Ich stelle die Lampe auf den Tisch.
• liegen / legen برای چیزهای خوابیده: Das Buch liegt auf dem Bett. / Ich lege das Buch auf das Bett.

اشتباه رایج فارسی‌زبانان: برای «کتاب روی میز است» از «stehen» استفاده نکنید؛ چون کتاب خوابیده است، «liegen» درست است.

English: German distinguishes standing (stehen/stellen) from lying (liegen/legen) objects.""",
            ),
            (
                "EXAMPLE",
                "Beispiele: meine Wohnung",
                """Ich wohne in einer Wohnung.  (در یک آپارتمان زندگی می‌کنم.)
Meine Wohnung hat zwei Zimmer, eine Küche und ein Bad.  (آپارتمان‌ام دو اتاق، یک آشپزخانه و یک حمام دارد.)
Im Wohnzimmer steht ein Sofa.  (در اتاق نشیمن یک کاناپه هست.)
Der Tisch steht vor dem Fenster.  (میز جلوی پنجره است.)
Das Buch liegt auf dem Tisch.  (کتاب روی میز است.)
Ich lege das Buch auf den Tisch.  (کتاب را روی میز می‌گذارم.)
In der Küche gibt es einen Herd und einen Kühlschrank.  (در آشپزخانه اجاق گاز و یخچال هست.)

English: Describing a flat, using place prepositions and „es gibt“.""",
            ),
        ],
        "words_new": [
            "Wohnung",
            "Haus",
            "Zimmer",
            "Wohnzimmer",
            "Schlafzimmer",
            "Küche",
            "Bad",
            "Toilette",
            "Balkon",
            "Keller",
            "Garten",
            "Aufzug",
            "Treppe",
            "Tür",
            "Fenster",
            "Wand",
            "Boden",
            "Schlüssel",
            "Wohnungsschlüssel",
            "Blick",
            "Möbel",
            "Tisch",
            "Stuhl",
            "Sofa",
            "Sessel",
            "Bett",
            "Schrank",
            "Regal",
            "Lampe",
            "Teppich",
            "Spiegel",
            "Kissen",
            "Badewanne",
            "Dusche",
            "Fernseher",
            "Herd",
            "Kühlschrank",
            "Miete",
            "Vermieter",
            "mieten",
            "liegen",
            "stehen",
            "legen",
            "stellen",
        ],
        "words_review": [
            "wohnen",
            "leben",
            "Familie",
            "Stadt",
            "Land",
            "hier",
            "dort",
            "mein",
            "unser",
            "haben",
            "sein",
        ],
        "grammar": [
            "Präpositionen des Ortes mit Dativ: in, an, auf, unter, neben …",
            "es gibt + Akkusativ",
            "wo? und wohin? – Grundlagen der Wechselpräpositionen",
            "Möbel und Räume beschreiben",
        ],
        "sentences": [
            ("Guten Tag. Ich suche eine Wohnung.", "روز بخیر. دنبال یک آپارتمان هستم.", "DIALOGUE", "Interessent"),
            ("Ja, gern. Die Wohnung hat zwei Zimmer.", "بله، حتماً. آپارتمان دو اتاق دارد.", "DIALOGUE", "Vermieter"),
            ("Hat die Wohnung einen Balkon?", "آپارتمان بالکن دارد؟", "DIALOGUE", "Interessent"),
            ("Ja, und auch einen Keller.", "بله، و یک زیرزمین هم دارد.", "DIALOGUE", "Vermieter"),
            ("Was kostet die Miete?", "اجاره چقدر است؟", "DIALOGUE", "Interessent"),
            ("Die Miete kostet 600 Euro.", "اجاره ۶۰۰ یورو است.", "DIALOGUE", "Vermieter"),
            ("Ich wohne in einer Wohnung.", "در یک آپارتمان زندگی می‌کنم.", "EXAMPLE", ""),
            (
                "Meine Wohnung hat zwei Zimmer, eine Küche und ein Bad.",
                "آپارتمان‌ام دو اتاق، یک آشپزخانه و یک حمام دارد.",
                "EXAMPLE",
                "",
            ),
            ("Im Wohnzimmer steht ein Sofa.", "در اتاق نشیمن یک کاناپه هست.", "EXAMPLE", ""),
            ("Der Tisch steht vor dem Fenster.", "میز جلوی پنجره است.", "EXAMPLE", ""),
            ("Das Buch liegt auf dem Tisch.", "کتاب روی میز است.", "EXAMPLE", ""),
            ("Ich lege das Buch auf den Tisch.", "کتاب را روی میز می‌گذارم.", "EXAMPLE", ""),
            ("Die Lampe steht neben dem Sofa.", "چراغ کنار کاناپه است.", "EXAMPLE", ""),
            ("Es gibt einen Balkon.", "یک بالکن وجود دارد.", "EXAMPLE", ""),
            (
                "In der Küche gibt es einen Herd und einen Kühlschrank.",
                "در آشپزخانه اجاق گاز و یخچال هست.",
                "EXAMPLE",
                "",
            ),
        ],
    }
)

# -------------------------------------------------------------------- lesson 12
LESSONS.append(
    {
        "order": 12,
        "title": "Wiederholung A1.1: Das kann ich jetzt",
        "description": "مرور درس‌های ۱ تا ۱۱ با متن خواندن. English: review of lessons 1-11 with a reading text.",
        "estimated_time": 50,
        "contents": [
            (
                "EXPLANATION",
                "Was kannst du nach A1.1?",
                """در این درس چیز تازه‌ای یاد نمی‌گیرید؛ تمرین می‌کنید. حالا می‌توانید:
• سلام کنید، خودتان را معرفی کنید و اسم بپرسید
• از کشور، شهر و زبان‌ها حرف بزنید
• سن، شماره تلفن و قیمت بگویید
• خانواده‌تان را معرفی کنید و از شغل حرف بزنید
• روزتان را با ساعت توصیف کنید
• در رستوران سفارش بدهید و خرید کنید
• لباس و خانه‌تان را توصیف کنید

English: Nothing new – consolidation. By now you can introduce yourself, talk about family, work, your day, food, shopping and your home.""",
            ),
            (
                "EXAMPLE",
                "Lesetext: Sara stellt sich vor",
                """Ich heiße Sara und ich komme aus dem Iran.
Ich wohne jetzt in Hamburg und arbeite dort als Ärztin.
Meine Wohnung hat zwei Zimmer, eine Küche und ein Bad.
Am Montag stehe ich um sechs Uhr auf.
Zum Frühstück esse ich Brot mit Käse und trinke Tee.
Ich arbeite von acht bis vier Uhr.
Am Abend kaufe ich im Supermarkt ein.
Meine Familie lebt in Isfahan.

ترجمه: اسم من ساراست و اهل ایرانم. الان در هامبورگ زندگی می‌کنم و آنجا به‌عنوان پزشک کار می‌کنم. آپارتمان‌ام دو اتاق، یک آشپزخانه و یک حمام دارد. دوشنبه ساعت شش بیدار می‌شوم. برای صبحانه نان با پنیر می‌خورم و چای می‌نوشم. از هشت تا چهار کار می‌کنم. شب در سوپرمارکت خرید می‌کنم. خانواده‌ام در اصفهان زندگی می‌کند.

English: A short reading text that brings the whole of A1.1 together.""",
            ),
            (
                "GRAMMAR",
                "Grammatik: die wichtigsten Regeln auf einer Seite",
                """فعل در جمله خبری همیشه جایگاه دوم است: Ich wohne in Berlin.
در سؤال بله/خیر فعل اول می‌آید: Wohnst du in Berlin?
در سؤال W کلمه پرسشی اول و فعل دوم می‌آید: Wo wohnst du?

مفعول مستقیم (akkusativ): فقط مذکر عوض می‌شود – der → den، ein → einen.
منفی: nicht برای فعل و صفت، kein/keine برای اسم ناشناس.
جمع همیشه با die: die Bücher، die Frauen، die Kinder.
فعل جداشدنی: پیشوند به آخر جمله می‌رود – Ich stehe um sechs Uhr auf.

English: The A1.1 rules in one place: position of the verb, yes/no and W-questions, accusative, negation, plural, separable verbs.""",
            ),
            (
                "NOTE",
                "Achtung: typische Fehler",
                """اشتباه‌های رایج فارسی‌زبانان در A1:
• ❌ Ich bin 20 Jahre. → ✅ Ich bin 20 Jahre alt. (سن در آلمانی با sein می‌آید.)
• ❌ Ich bin ein Lehrer. → ✅ Ich bin Lehrer. (شغل بدون حرف تعریف)
• ❌ Ich trinke nicht Kaffee. → ✅ Ich trinke keinen Kaffee. (اسم ناشناس با kein منفی می‌شود)
• ❌ Ich aufstehe um 6 Uhr. → ✅ Ich stehe um 6 Uhr auf. (پیشوند به آخر جمله می‌رود)
• ❌ Ich gehe in Berlin. → ✅ Ich wohne in Berlin. (wohnen برای زندگی، gehen برای رفتن)

English: Typical A1 mistakes: age with sein, no article after sein with jobs, kein with nouns, separable prefixes at the end.""",
            ),
            (
                "EXAMPLE",
                "Beispiele zum Wiederholen",
                """Wie heißen Sie? – Ich heiße Sara.  (اسم شما چیست؟ – اسم من ساراست.)
Woher kommst du? – Ich komme aus dem Iran.  (اهل کجایی؟ – اهل ایرانم.)
Was sind Sie von Beruf? – Ich bin Ärztin.  (شغل شما چیست؟ – پزشک هستم.)
Wie viel Uhr ist es? – Es ist halb acht.  (ساعت چند است؟ – هفت و نیم.)
Was kostet das? – Das kostet zwölf Euro.  (این چند است؟ – دوازده یورو.)
Das gefällt mir.  (این را دوست دارم.)

English: A quick round of the most important A1.1 questions and answers.""",
            ),
        ],
        "words_new": [],
        "words_review": [
            "hallo",
            "danke",
            "ich",
            "sein",
            "haben",
            "heißen",
            "Name",
            "kommen",
            "wohnen",
            "Deutschland",
            "Iran",
            "Familie",
            "Vater",
            "Mutter",
            "Bruder",
            "Schwester",
            "Arbeit",
            "Beruf",
            "Arzt",
            "Ärztin",
            "Morgen",
            "Uhr",
            "halb",
            "aufstehen",
            "frühstücken",
            "Essen",
            "Brot",
            "Käse",
            "Tee",
            "Kaffee",
            "Supermarkt",
            "einkaufen",
            "Wohnung",
            "Zimmer",
            "Küche",
            "Bad",
            "Möbel",
            "Preis",
            "kosten",
            "Euro",
        ],
        "grammar": [
            "Personalpronomen und das Verb „sein“",
            "Regelmäßige Verben im Präsens",
            "Satzstellung: Verb an Position 2",
            "Negation: nicht oder kein?",
            "Trennbare Verben im Präsens",
            "Der Akkusativ: den, die, das, einen, eine",
            "Präpositionen des Ortes mit Dativ: in, an, auf, unter, neben …",
        ],
        "sentences": [
            ("Ich heiße Sara und ich komme aus dem Iran.", "اسم من ساراست و اهل ایرانم.", "READING", ""),
            (
                "Ich wohne jetzt in Hamburg und arbeite dort als Ärztin.",
                "الان در هامبورگ زندگی می‌کنم و آنجا به‌عنوان پزشک کار می‌کنم.",
                "READING",
                "",
            ),
            (
                "Meine Wohnung hat zwei Zimmer, eine Küche und ein Bad.",
                "آپارتمان‌ام دو اتاق، یک آشپزخانه و یک حمام دارد.",
                "READING",
                "",
            ),
            ("Am Montag stehe ich um sechs Uhr auf.", "دوشنبه ساعت شش بیدار می‌شوم.", "READING", ""),
            (
                "Zum Frühstück esse ich Brot mit Käse und trinke Tee.",
                "برای صبحانه نان با پنیر می‌خورم و چای می‌نوشم.",
                "READING",
                "",
            ),
            ("Ich arbeite von acht bis vier Uhr.", "از هشت تا چهار کار می‌کنم.", "READING", ""),
            ("Am Abend kaufe ich im Supermarkt ein.", "شب در سوپرمارکت خرید می‌کنم.", "READING", ""),
            ("Meine Familie lebt in Isfahan.", "خانواده‌ام در اصفهان زندگی می‌کند.", "READING", ""),
            ("Wie heißen Sie?", "اسم شما چیست؟", "EXAMPLE", ""),
            ("Was sind Sie von Beruf?", "شغل شما چیست؟", "EXAMPLE", ""),
            ("Was kostet das?", "این چند است؟", "EXAMPLE", ""),
            ("Das gefällt mir.", "این را دوست دارم.", "EXAMPLE", ""),
        ],
    }
)

# === APPEND HERE ===
