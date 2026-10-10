"""Seed active production drills and convert pseudo-multiple-choice cloze drills.

Stage 2.1 of the pedagogical roadmap:
1. Action 1: Converts 36 authored cloze questions across 13 lessons from choice to typed
   by removing false distractors.
2. Action 2: Adds 2 active exercises (+14 questions) to Lesson 12 to resolve its 95% passive
   imbalance (8 scramble questions + 6 typed cloze questions).
3. Action 3: Adds 3 targeted SCRAMBLE exercises (+18 questions) to high-grammar lessons:
   - Lesson 04: Possessive pronouns in sentence structures (6 questions)
   - Lesson 19: Perfekt sentence bracket / Satzklammer (6 questions)
   - Lesson 20: Modal verbs, invitations and dative celebrations (6 questions)

Idempotent and supports --dry-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, Question
from lessons.models import Lesson


CLOZE_LESSONS = [2, 4, 5, 8, 10, 11, 13, 14, 18, 20, 21, 22, 23]


L12_SCRAMBLE_ITEMS = [
    (
        "Ich heiße Sara und ich komme aus dem Iran.",
        "جملهٔ زیر را مرتب کنید: (اسم من ساراست و اهل ایرانم.)",
        "جمله از دو بخش تشکیل شده که با حرف ربط «und» به هم وصل شده‌اند؛ در هر بخش فعل در جایگاه دوم است («heiße» و «komme»).",
    ),
    (
        "Ich wohne jetzt in Hamburg und arbeite dort als Ärztin.",
        "جملهٔ زیر را مرتب کنید: (الان در هامبورگ زندگی می‌کنم و آنجا به‌عنوان پزشک کار می‌کنم.)",
        "فعل «wohne» در جایگاه دوم است؛ پس از حرف ربط «und»، فعل «arbeite» نیز جایگاه دوم بخش دوم را دارد.",
    ),
    (
        "Meine Wohnung hat zwei Zimmer, eine Küche und ein Bad.",
        "جملهٔ زیر را مرتب کنید: (آپارتمان‌ام دو اتاق، یک آشپزخانه و یک حمام دارد.)",
        "فاعل «Meine Wohnung» در ابتدا و فعل «hat» در جایگاه دوم قرار می‌گیرد.",
    ),
    (
        "Meine Familie lebt in Isfahan.",
        "جملهٔ زیر را مرتب کنید: (خانواده‌ام در اصفهان زندگی می‌کند.)",
        "«Meine Familie» فاعل مفرد است و فعل «lebt» با آن تطابق دارد و در جایگاه دوم قرار می‌گیرد.",
    ),
    (
        "Wie heißen Sie?",
        "جملهٔ زیر را مرتب کنید: (اسم شما چیست؟)",
        "در سؤال‌های با کلمهٔ پرسشی (W-Frage)، کلمهٔ پرسشی «Wie» در جایگاه اول و فعل «heißen» در جایگاه دوم می‌آید.",
    ),
    (
        "Was sind Sie von Beruf?",
        "جملهٔ زیر را مرتب کنید: (شغل شما چیست؟)",
        "کلمهٔ پرسشی «Was» در ابتدا و فعل «sind» در جایگاه دوم قرار دارد.",
    ),
    (
        "Was kostet das?",
        "جملهٔ زیر را مرتب کنید: (این چند است؟ / قیمتش چقدر است؟)",
        "کلمهٔ پرسشی «Was» و فعل «kostet» در جایگاه دوم قرار دارد.",
    ),
    (
        "Das gefällt mir.",
        "جملهٔ زیر را مرتب کنید: (این را دوست دارم. / از این خوشم می‌آید.)",
        "فعل «gefallen» با ضمیر مفعولی داتیو «mir» به کار می‌رود؛ «Das» فاعل و در جایگاه اول است.",
    ),
]

L12_CLOZE_ITEMS = [
    (
        'جایگزین _____ در جمله زیر شود:\n"Woher _____ du? – Ich komme aus dem Iran."',
        "kommst",
        "صرف فعل «kommen» برای ضمیر «du» با پسوند st- می‌شود: «kommst».",
    ),
    (
        'جایگزین _____ در جمله زیر شود:\n"Ich _____ zwei Zimmer und eine Küche."',
        "habe",
        "برای بیان داشتن اتاق یا خانه از فعل «haben» استفاده می‌شود: «Ich habe».",
    ),
    (
        'جایگزین _____ در جمله زیر شود:\n"Ich habe _____ Zeit."',
        "keine",
        "کلمهٔ «Zeit» اسم مؤنث است و برای منفی کردن اسم نکرهٔ مؤنث از «keine» استفاده می‌شود.",
    ),
    (
        'جایگزین _____ در جمله زیر شود:\n"Ich trinke _____ Kaffee, sondern Tee."',
        "nicht",
        "برای منفی کردن قید یا کل عبارت در این بافت از قید منفی‌ساز «nicht» استفاده می‌شود.",
    ),
    (
        'جایگزین _____ در جمله زیر شود:\n"Am Morgen _____ ich um sieben Uhr auf."',
        "stehe",
        "فعل جداشدنی «aufstehen» است؛ بخش اصلی «stehe» در جایگاه دوم و پیشوند «auf» در پایان جمله قرار می‌گیرد.",
    ),
    (
        'جایگزین _____ در جمله زیر شود:\n"Ich _____ heute nach Hause gehen."',
        "muss",
        "فعل وجهی «müssen» برای ضمیر «ich» به شکل «muss» صرف می‌شود و در جایگاه دوم می‌آید.",
    ),
]

L04_SCRAMBLE_ITEMS = [
    (
        "Das ist meine Familie.",
        "جملهٔ زیر را مرتب کنید: (این خانوادهٔ من است.)",
        "«Familie» مؤنث است و با ضمیر ملکی مؤنث «meine» می‌آید؛ فعل «ist» در جایگاه دوم است.",
    ),
    (
        "Mein Vater heißt Reza und meine Mutter heißt Maryam.",
        "جملهٔ زیر را مرتب کنید: (پدرم رضا نام دارد و مادرم مریم نام دارد.)",
        "«Vater» مذکر است (mein Vater) و «Mutter» مؤنث است (meine Mutter)؛ دو جمله با «und» متصل شده‌اند.",
    ),
    (
        "Das sind meine Eltern.",
        "جملهٔ زیر را مرتب کنید: (این‌ها پدر و مادرم هستند.)",
        "«Eltern» اسم جمع است، بنابراین فعل جمع «sind» و ضمیر ملکی جمع «meine» به کار می‌رود.",
    ),
    (
        "Ich habe eine Schwester und einen Bruder.",
        "جملهٔ زیر را مرتب کنید: (من یک خواهر و یک برادر دارم.)",
        "فعل «haben» مفعول آکوزاتیو می‌گیرد: «eine Schwester» (مؤنث) و «einen Bruder» (مذکر در آکوزاتیو).",
    ),
    (
        "Meine Schwester wohnt in Berlin.",
        "جملهٔ زیر را مرتب کنید: (خواهرم در برلین زندگی می‌کند.)",
        "فاعل «Meine Schwester» در ابتدا و فعل «wohnt» در جایگاه دوم می‌آید.",
    ),
    (
        "Wie alt sind deine Kinder?",
        "جملهٔ زیر را مرتب کنید: (بچه‌هایت چند ساله‌اند؟)",
        "کلمهٔ پرسشی مرکب «Wie alt» در جایگاه اول، فعل جمع «sind» در جایگاه دوم و فاعل جمع «deine Kinder» بعد از آن می‌آید.",
    ),
]

L19_SCRAMBLE_ITEMS = [
    (
        "Was hast du am Wochenende gemacht?",
        "جملهٔ زیر را مرتب کنید: (آخر هفته چه کار کردی؟)",
        "در سؤال با Perfekt، فعل کمکی «hast» در جایگاه دوم و اسم مفعول «gemacht» در انتهای جمله (قوس فعل) می‌آید.",
    ),
    (
        "Ich habe gestern Deutsch gelernt.",
        "جملهٔ زیر را مرتب کنید: (من دیروز آلمانی یاد گرفتم.)",
        "قوس فعل در Perfekt: فعل کمکی «habe» در جایگاه دوم و صفت مفعولی «gelernt» در پایان جمله قرار می‌گیرد.",
    ),
    (
        "Wir haben zusammen im Restaurant gegessen.",
        "جملهٔ زیر را مرتب کنید: (ما با هم در رستوران غذا خوردیم.)",
        "فعل کمکی «haben» در جایگاه دوم و اسم مفعول نامنظم «gegessen» در انتهای جمله می‌آید.",
    ),
    (
        "Am Sonntag habe ich lange geschlafen.",
        "جملهٔ زیر را مرتب کنید: (روز یکشنبه طولانی خوابیدم.)",
        "با شروع جمله با قید زمان «Am Sonntag»، فعل کمکی «habe» در جایگاه دوم و فاعل «ich» بلافاصله بعد از آن می‌آید؛ «geschlafen» در انتها قرار دارد.",
    ),
    (
        "Ich habe meine Hausaufgaben gemacht.",
        "جملهٔ زیر را مرتب کنید: (من تکالیفم را انجام دادم.)",
        "فعل کمکی «habe» در جایگاه دوم و اسم مفعول «gemacht» در انتهای جمله می‌آید.",
    ),
    (
        "Hast du gestern Musik gehört?",
        "جملهٔ زیر را مرتب کنید: (دیروز موسیقی گوش دادی؟)",
        "در سؤال بله/خیر (Ja/Nein-Frage)، فعل کمکی «Hast» در جایگاه اول و اسم مفعول «gehört» در انتهای جمله قرار می‌گیرد.",
    ),
]

L20_SCRAMBLE_ITEMS = [
    (
        "Ich lade dich zu meiner Party ein.",
        "جملهٔ زیر را مرتب کنید: (من تو را به مهمانی‌ام دعوت می‌کنم.)",
        "فعل جداشدنی «einladen» است؛ بخش «lade» در جایگاه دوم و پیشوند «ein» در انتهای جمله قرار می‌گیرد.",
    ),
    (
        "Herzlichen Glückwunsch zum Geburtstag!",
        "جملهٔ زیر را مرتب کنید: (تولدت مبارک!)",
        "عبارت تبریک رسمی و معمول آلمانی برای تولد همراه با حرف اضافهٔ داتیو «zum» (کوتاه‌شدهٔ zu dem).",
    ),
    (
        "Ich bringe einen Kuchen zur Feier mit.",
        "جملهٔ زیر را مرتب کنید: (من برای جشن یک کیک با خودم می‌آورم.)",
        "فعل جداشدنی «mitbringen» است؛ «bringe» در جایگاه دوم و پیشوند «mit» در پایان جمله می‌آید.",
    ),
    (
        "Kommst du am Samstag zu mir?",
        "جملهٔ زیر را مرتب کنید: (شنبه پیش من می‌آیی؟)",
        "سؤال بله/خیر است؛ فعل «Kommst» در جایگاه اول و عبارت جهت/داتیو «zu mir» در جمله می‌آید.",
    ),
    (
        "Wir möchten zusammen feiern.",
        "جملهٔ زیر را مرتب کنید: (ما می‌خواهیم با هم جشن بگیریم.)",
        "با فعل وجهی «möchten» در جایگاه دوم، فعل اصلی «feiern» به صورت مصدر در انتهای جمله قرار می‌گیرد.",
    ),
    (
        "Vielen Dank für das schöne Geschenk!",
        "جملهٔ زیر را مرتب کنید: (خیلی ممنون بابت هدیهٔ زیبا!)",
        "حرف اضافهٔ «für» همیشه مفعول آکوزاتیو می‌گیرد: «das schöne Geschenk».",
    ),
]


class Command(BaseCommand):
    help = "Seed active production drills (SCRAMBLE and typed FILL_BLANK) across L02-L23."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate execution without modifying the database.",
        )

    def _convert_cloze_distractors(self, dry_run):
        """Action 1: Drop distractor rows for authored cloze exercises in 13 lessons."""
        distractors = Answer.objects.filter(
            question__exercise__is_published=True,
            question__exercise__type=Exercise.ExerciseType.FILL_BLANK,
            question__exercise__lesson__order__in=CLOZE_LESSONS,
            question__exercise__order=3,
            is_correct=False,
        )
        count = distractors.count()
        if not dry_run and count > 0:
            distractors.delete()
        return count

    def _create_exercise_with_questions(self, lesson, title, instruction, etype, items, is_scramble, dry_run):
        """Helper to create or get an exercise and add its questions idempotently."""
        ex = Exercise.objects.filter(lesson=lesson, title=title).first()
        created = False
        if ex is None:
            max_order = Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"] or 0
            if dry_run:
                ex = Exercise(
                    lesson=lesson,
                    title=title,
                    instruction=instruction,
                    type=etype,
                    difficulty=Exercise.Difficulty.MEDIUM,
                    order=max_order + 1,
                    is_published=True,
                )
            else:
                ex = Exercise.objects.create(
                    lesson=lesson,
                    title=title,
                    instruction=instruction,
                    type=etype,
                    difficulty=Exercise.Difficulty.MEDIUM,
                    order=max_order + 1,
                    is_published=True,
                )
            created = True

        questions_created = 0
        if not dry_run:
            for idx, item in enumerate(items, start=1):
                if is_scramble:
                    sentence, prompt, explanation = item
                    q, q_created = Question.objects.get_or_create(
                        exercise=ex,
                        order=idx,
                        defaults={
                            "prompt": prompt,
                            "explanation": explanation,
                        },
                    )
                    if q_created:
                        Answer.objects.create(
                            question=q,
                            text=sentence,
                            is_correct=True,
                            order=1,
                        )
                        questions_created += 1
                else:
                    prompt, correct_text, explanation = item
                    q, q_created = Question.objects.get_or_create(
                        exercise=ex,
                        order=idx,
                        defaults={
                            "prompt": prompt,
                            "explanation": explanation,
                        },
                    )
                    if q_created:
                        Answer.objects.create(
                            question=q,
                            text=correct_text,
                            is_correct=True,
                            order=1,
                        )
                        questions_created += 1
        else:
            questions_created = len(items)

        return ex, created, questions_created

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        prefix = "[DRY-RUN] " if dry_run else ""

        with transaction.atomic():
            # Action 1: Cloze distractor removal
            removed_distractors = self._convert_cloze_distractors(dry_run)
            self.stdout.write(
                f"{prefix}Action 1: Removed {removed_distractors} distractor rows from 13 lessons "
                f"(36 questions promoted to typed cloze)."
            )

            # Action 2: Lesson 12 Rebalancing
            l12 = Lesson.objects.filter(order=12).first()
            if l12:
                ex_l12_scramble, created_s, q_s = self._create_exercise_with_questions(
                    lesson=l12,
                    title="تمرین جمله — مرتب کردن (۲)",
                    instruction="واژه‌های درهم را به ترتیب درست بچین و جمله را بنویس.",
                    etype=Exercise.ExerciseType.SCRAMBLE,
                    items=L12_SCRAMBLE_ITEMS,
                    is_scramble=True,
                    dry_run=dry_run,
                )
                ex_l12_cloze, created_c, q_c = self._create_exercise_with_questions(
                    lesson=l12,
                    title="تمرین تکمیل جمله — مرور قواعد A1.1",
                    instruction="جای خالی را با واژهٔ مناسب پر کنید.",
                    etype=Exercise.ExerciseType.FILL_BLANK,
                    items=L12_CLOZE_ITEMS,
                    is_scramble=False,
                    dry_run=dry_run,
                )
                self.stdout.write(
                    f"{prefix}Action 2 (L12): Added Scramble ({q_s} Qs) and Typed Cloze ({q_c} Qs)."
                )

            # Action 3: Targeted Scrambles for L04, L19, L20
            l04 = Lesson.objects.filter(order=4).first()
            if l04:
                _, _, q_l04 = self._create_exercise_with_questions(
                    lesson=l04,
                    title="تمرین ساخت جمله — خانواده و ضمیر ملکی",
                    instruction="واژه‌های درهم را به ترتیب درست بچین و جمله را بنویس.",
                    etype=Exercise.ExerciseType.SCRAMBLE,
                    items=L04_SCRAMBLE_ITEMS,
                    is_scramble=True,
                    dry_run=dry_run,
                )
                self.stdout.write(f"{prefix}Action 3 (L04): Added Scramble ({q_l04} Qs).")

            l19 = Lesson.objects.filter(order=19).first()
            if l19:
                _, _, q_l19 = self._create_exercise_with_questions(
                    lesson=l19,
                    title="تمرین ساخت جمله — زمان گذشته (Perfekt)",
                    instruction="واژه‌های درهم را به ترتیب درست بچین و جمله را بنویس.",
                    etype=Exercise.ExerciseType.SCRAMBLE,
                    items=L19_SCRAMBLE_ITEMS,
                    is_scramble=True,
                    dry_run=dry_run,
                )
                self.stdout.write(f"{prefix}Action 3 (L19): Added Scramble ({q_l19} Qs).")

            l20 = Lesson.objects.filter(order=20).first()
            if l20:
                _, _, q_l20 = self._create_exercise_with_questions(
                    lesson=l20,
                    title="تمرین ساخت جمله — دعوت و تبریک",
                    instruction="واژه‌های درهم را به ترتیب درست بچین و جمله را بنویس.",
                    etype=Exercise.ExerciseType.SCRAMBLE,
                    items=L20_SCRAMBLE_ITEMS,
                    is_scramble=True,
                    dry_run=dry_run,
                )
                self.stdout.write(f"{prefix}Action 3 (L20): Added Scramble ({q_l20} Qs).")

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(f"{prefix}Stage 2.1 execution completed successfully.")
