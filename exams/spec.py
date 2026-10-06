"""The official A1 exam, written down once as facts instead of as prose.

Every number here comes from the exam's own Durchführungsbestimmungen — the sections, how
long each takes, how many items each asks, what each is worth, how raw points become the
total, and what the pass mark is. ``exams/paper.py`` uses these facts to pick the
questions; ``exams/views.py`` uses them to say what the exam is. Nothing in this module
reads the database.

**What the mock claims, and what it does not.** It reproduces the exam's *shape* — section
order, item counts, minutes, scoring — and not its task types, because the questions are
this product's own drills. It also cannot reproduce the *marking*: the official sections
are marked against criteria by two graders, and SPRECHEN by two examiners. Only HÖREN and
LESEN are a plain count of right answers at all. The mock grades what a stored answer can
be graded on and the page repeats that limitation to the learner, which is the same rule
«آمادگی من» follows.

The spoken part is here too, because it is part of the exam's shape: three parts of about
five minutes each, with the points they carry and the phrases a candidate has to be able
to say. Nothing in this product grades speaking, so the rehearsal is ungraded — and the
page says so instead of inventing a number for it.
"""

from .sections import Section

#: Where every number below comes from. It is quoted on the exam page so a learner can
#: check the arithmetic against the same document.
SOURCE = (
    "Goethe-Zertifikat A1: Start Deutsch 1 – Durchführungsbestimmungen "
    "(goethe.de, Stand 1. September 2025)"
)

#: The written exam's whole duration, taken as one clock by this mock.
DURATION_MINUTES = 65

#: Items asked per section, and the raw points a perfect section is worth. Every official
#: answer is worth one point, so these two numbers are the same number.
ITEMS_PER_SECTION = 15

#: Each section's raw points are multiplied by this before the sections are added up.
SCORE_FACTOR = 1.66

#: What the written part adds up to after the factor (45 × 1.66 = 74.7, rounded).
WRITTEN_MAX_POINTS = 75

#: The oral section's share, and what the four sections add up to.
SPOKEN_MAX_POINTS = 25
MAX_POINTS = 100

#: The official pass mark, and the written subtotal below which the oral section cannot
#: reach it: 34 written points plus a perfect oral section is 59, and 35 plus 25 is exactly
#: 60. The exam states this rule itself, so the page can state it too.
PASS_POINTS = 60
WRITTEN_MINIMUM = 35

SECTION_FACTS = {
    Section.HOEREN: {
        "german": "HÖREN",
        "label": "شنیدن",
        "minutes": 20,
        "items": 15,
        "note": "سه بخش؛ به هر پاسخ یک امتیاز خام.",
    },
    Section.LESEN: {
        "german": "LESEN",
        "label": "خواندن",
        "minutes": 25,
        "items": 15,
        "note": "سه بخش؛ به هر پاسخ یک امتیاز خام.",
    },
    Section.SCHREIBEN: {
        "german": "SCHREIBEN",
        "label": "نوشتن",
        "minutes": 20,
        "items": 15,
        "note": "بخش ۱ پنج امتیاز و بخش ۲ ده امتیاز دارد؛ در آزمون رسمی هر دو را تصحیح‌کنندهٔ انسانی نمره می‌دهد.",
    },
}

#: The order the written sections are administered in.
SECTION_ORDER = [
    Section.HOEREN,
    Section.LESEN,
    Section.SCHREIBEN,
]

#: The instruction words the official task sheets use. A learner who cannot read these is
#: stopped by vocabulary rather than by German, so the exam page lists them and — from
#: real ``Word`` rows, not a hand-written flag — says which ones this course already
#: teaches. The matching is done in ``exams/paper.py``.
INSTRUCTIONS = [
    {"german": "die Aufgabe", "fa": "تمرین / سؤال"},
    {"german": "der Antwortbogen", "fa": "برگهٔ پاسخ"},
    {"german": "ankreuzen", "fa": "علامت زدن گزینهٔ درست"},
    {"german": "ergänzen", "fa": "کامل کردن"},
    {"german": "zuordnen", "fa": "تطبیق دادن"},
    {"german": "der Hörtext", "fa": "متن شنیداری"},
    {"german": "das Bild", "fa": "تصویر"},
    {"german": "die Lösung", "fa": "پاسخ"},
    {"german": "das Alphabet", "fa": "الفبا"},
    {"german": "richtig / falsch", "fa": "درست / غلط"},
]

#: The oral section, as the exam describes it: three parts of about five minutes, 15 points
#: in total, no preparation time, two examiners. The phrases are the functions a candidate
#: has to be able to perform — not a script, because the exam supplies the keywords.
SPRECHEN = {
    "minutes": 15,
    "points": 15,
    "note": "۱۵ دقیقه در گروه؛ هر بخش حدود ۵ دقیقه. هیچ زمان آماده‌سازی‌ای وجود ندارد و کارت‌ها را همان‌جا می‌دهند.",
    "parts": [
        {
            "number": 1,
            "title": "خودت را معرفی کن",
            "german": "Sich vorstellen",
            "minutes": 5,
            "points": 3,
            "what": "با تکیه بر کلیدواژه‌های روی کارت خودت را معرفی می‌کنی؛ بعد از تو می‌خواهند یک واژه را هجی کنی و یک عدد را بگویی.",
            "phrases": [
                {"de": "Ich heiße … / Mein Name ist …", "fa": "اسمم … است."},
                {"de": "Ich bin 24 Jahre alt.", "fa": "۲۴ سال دارم."},
                {"de": "Ich komme aus dem Iran.", "fa": "اهل ایرانم."},
                {"de": "Ich wohne in Isfahan.", "fa": "در اصفهان زندگی می‌کنم."},
                {"de": "Ich spreche Persisch, Englisch und ein bisschen Deutsch.", "fa": "فارسی، انگلیسی و کمی آلمانی حرف می‌زنم."},
                {"de": "Ich arbeite als … / Ich bin Student.", "fa": "کار می‌کنم به‌عنوان … / دانشجو هستم."},
                {"de": "Mein Hobby ist Musik.", "fa": "سرگرمی‌ام موسیقی است."},
                {"de": "Mein Name ist … / B-E-N.", "fa": "اسم من … است؛ آن را هجی می‌کنم: B-E-N."},
                {"de": "Meine Nummer ist 0176 12345678.", "fa": "شماره‌ام … است."},
            ],
        },
        {
            "number": 2,
            "title": "سؤال بساز و جواب بده",
            "german": "Fragen stellen und darauf reagieren",
            "minutes": 5,
            "points": 6,
            "what": "با بقیهٔ شرکت‌کننده‌ها حرف می‌زنی: از کارت‌ها سؤال می‌سازی و به سؤال دیگران جواب می‌دهی.",
            "phrases": [
                {"de": "Wie heißt du?", "fa": "اسمت چیست؟"},
                {"de": "Woher kommst du?", "fa": "اهل کجایی؟"},
                {"de": "Wo wohnst du?", "fa": "کجا زندگی می‌کنی؟"},
                {"de": "Wie alt bist du?", "fa": "چند سال داری؟"},
                {"de": "Was machst du gern?", "fa": "چه کاری را دوست داری بکنی؟"},
                {"de": "Hast du Geschwister?", "fa": "خواهر یا برادر داری؟"},
                {"de": "Ich auch.", "fa": "من هم همین‌طور."},
                {"de": "Nein, leider nicht.", "fa": "نه، متأسفانه نه."},
            ],
        },
        {
            "number": 3,
            "title": "درخواست کن و واکنش بده",
            "german": "Bitten formulieren und darauf reagieren",
            "minutes": 5,
            "points": 6,
            "what": "از کارت‌ها یک درخواست یا امر می‌سازی و طرف مقابل جواب می‌دهد؛ بعد جای‌تان عوض می‌شود.",
            "phrases": [
                {"de": "Kannst du mir bitte helfen?", "fa": "می‌شود لطفاً کمکم کنی؟"},
                {"de": "Können Sie das bitte wiederholen?", "fa": "می‌شود لطفاً تکرار کنید؟"},
                {"de": "Gib mir bitte das Buch.", "fa": "لطفاً کتاب را به من بده."},
                {"de": "Kann ich dein Handy haben?", "fa": "می‌توانم گوشی‌ات را داشته باشم؟"},
                {"de": "Ja, gern.", "fa": "بله، با کمال میل."},
                {"de": "Ja, natürlich.", "fa": "بله، البته."},
                {"de": "Tut mir leid, das geht nicht.", "fa": "متأسفم، نمی‌شود."},
            ],
        },
    ],
}
