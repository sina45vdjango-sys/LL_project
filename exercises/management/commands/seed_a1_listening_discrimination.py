"""Seed targeted A1 listening discrimination exercises in key everyday lessons.

Stage 2.2 of the pedagogical roadmap:
Introduces 5 curated listening discrimination exercises (+26 questions) across:
- Lesson 03: Numbers, Spelling & Phone Numbers (6 questions)
- Lesson 06: Clock Times & Daily Routine (5 questions)
- Lesson 09: Shopping & Prices (5 questions)
- Lesson 15: Appointments & Calendar (5 questions)
- Lesson 17: Travel, Transport & Hotel (5 questions)

Each question tests authentic Goethe-Zertifikat A1 Hören discrimination (extracting
the exact number, spelling, time, price, day, or location from the audio clip)
with realistic distractors and structured Persian explanations.

Idempotent and supports --dry-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, Question
from lessons.models import Lesson
from vocabulary.models import Sentence


DRILL_DATA = {
    3: {
        "title": "شنیدن و تشخیص اطلاعات: اعداد، شماره‌ها و هجی کردن",
        "instruction": "به فایل صوتی گوش کن و بر اساس اطلاعاتی که می‌شنوی، پاسخ درست را انتخاب کن.",
        "questions": [
            {
                "sentence_id": 34,
                "prompt": "به شماره تلفن گوش کن. کدام شماره در فایل خوانده شد؟",
                "options": [
                    ("0176 45 67 89", True),
                    ("0176 54 67 89", False),
                    ("0176 45 76 89", False),
                    ("0176 45 67 98", False),
                ],
                "explanation": "در آلمانی ارقام دورقمی از راست خوانده می‌شوند: «fünfundvierzig» (۴۵)، «siebenundsechzig» (۶۷)، «neunundachtzig» (۸۹). بنابراین شمارهٔ صحیح 0176 45 67 89 است.",
            },
            {
                "sentence_id": 38,
                "prompt": "به تلفظ حروف (هجی کردن نام) گوش کن. کدام نام هجی شد؟",
                "options": [
                    ("Ahmadi", True),
                    ("Amadi", False),
                    ("Ahmedi", False),
                    ("Ehmadi", False),
                ],
                "explanation": "حروف به این ترتیب هجی شدند: A (آ)، H (ها)، M (اِم)، A (آ)، D (دِ)، I (ای) که تشکیل نام «Ahmadi» را می‌دهند.",
            },
            {
                "sentence_id": 36,
                "prompt": "سن گوینده چقدر است؟",
                "options": [
                    ("۳۰ سال", True),
                    ("۱۳ سال", False),
                    ("۲۰ سال", False),
                    ("۲۳ سال", False),
                ],
                "explanation": "گوینده می‌گوید «dreißig Jahre alt» یعنی ۳۰ سال. توجه کنید پسوند «-zig» نشانهٔ ده‌هاست (dreißig = ۳۰)، در حالی که پسوند «-zehn» نشانهٔ ۱۰ تا ۱۹ است (dreizehn = ۱۳).",
            },
            {
                "sentence_id": 44,
                "prompt": "کدام شماره موبایل در فایل صوتی اعلام شد؟",
                "options": [
                    ("0176 12345678", True),
                    ("0176 12345687", False),
                    ("0176 21345678", False),
                    ("0176 12435678", False),
                ],
                "explanation": "شمارهٔ اعلام‌شده با دقت به ارقام یک تا هشت: 0176 12345678 است.",
            },
            {
                "sentence_id": 41,
                "prompt": "قیمت اعلام‌شده چقدر است؟",
                "options": [
                    ("۱۲ یورو", True),
                    ("۲ یورو", False),
                    ("۲۰ یورو", False),
                    ("۱۰ یورو", False),
                ],
                "explanation": "عدد گفته‌شده «zwölf» یعنی ۱۲ (دقت کنید با zwei = ۲ یا zwanzig = ۲۰ اشتباه نشود).",
            },
            {
                "sentence_id": 353,
                "prompt": "شخص چند ساله است؟",
                "options": [
                    ("۲۴ سال", True),
                    ("۴۲ سال", False),
                    ("۱۴ سال", False),
                    ("۳۴ سال", False),
                ],
                "explanation": "در فایل گفته می‌شود «vierundzwanzig» یعنی چهار و بیست (۲۴ سال). در زبان آلمانی ابتدا یکان و سپس دهگان تلفظ می‌شود.",
            },
        ],
    },
    6: {
        "title": "شنیدن و تشخیص اطلاعات: ساعت و زمان",
        "instruction": "به فایل صوتی گوش کن و بر اساس اطلاعاتی که می‌شنوی، پاسخ درست را انتخاب کن.",
        "questions": [
            {
                "sentence_id": 76,
                "prompt": "ساعت چند است؟",
                "options": [
                    ("۷:۳۰", True),
                    ("۸:۳۰", False),
                    ("۷:۱۵", False),
                    ("۸:۱۵", False),
                ],
                "explanation": "در آلمانی «halb acht» یعنی نیم ساعت مانده به هشت، یعنی ساعت ۷:۳۰ (یکی از دام‌های رایج در آزمون گوته A1 که نباید با ۸:۳۰ اشتباه شود).",
            },
            {
                "sentence_id": 78,
                "prompt": "گوینده چه ساعتی از خواب بیدار می‌شود؟",
                "options": [
                    ("۶:۰۰", True),
                    ("۷:۰۰", False),
                    ("۶:۳۰", False),
                    ("۵:۰۰", False),
                ],
                "explanation": "عبارت «um sechs Uhr» صراحتاً ساعت ۶:۰۰ صبح را بیان می‌کند («aufstehen» = بیدار شدن).",
            },
            {
                "sentence_id": 80,
                "prompt": "ساعات کاری گوینده کدام است؟",
                "options": [
                    ("از ۸:۰۰ تا ۱۶:۰۰ (۴ بعدازظهر)", True),
                    ("از ۸:۰۰ تا ۱۴:۰۰ (۲ بعدازظهر)", False),
                    ("از ۹:۰۰ تا ۱۷:۰۰ (۵ بعدازظهر)", False),
                    ("از ۷:۰۰ تا ۱۵:۰۰ (۳ بعدازظهر)", False),
                ],
                "explanation": "عبارت «von acht bis vier» یعنی از ساعت ۸ تا ۴ (که در سیستم ۲۴ ساعته برابر ۱۶:۰۰ است).",
            },
            {
                "sentence_id": 81,
                "prompt": "زمان صرف صبحانه چه ساعتی است؟",
                "options": [
                    ("۶:۳۰", True),
                    ("۷:۳۰", False),
                    ("۶:۱۵", False),
                    ("۷:۰۰", False),
                ],
                "explanation": "«halb sieben» یعنی نیم ساعت قبل از هفت، یعنی ساعت ۶:۳۰.",
            },
            {
                "sentence_id": 84,
                "prompt": "در روزهای آخر هفته تا چه ساعتی می‌خوابد؟",
                "options": [
                    ("۱۰:۰۰", True),
                    ("۹:۰۰", False),
                    ("۸:۰۰", False),
                    ("۱۱:۰۰", False),
                ],
                "explanation": "عبارت «bis zehn Uhr» یعنی تا ساعت ۱۰:۰۰.",
            },
        ],
    },
    9: {
        "title": "شنیدن و تشخیص اطلاعات: قیمت‌ها و مقادیر خرید",
        "instruction": "به فایل صوتی گوش کن و بر اساس اطلاعاتی که می‌شنوی، پاسخ درست را انتخاب کن.",
        "questions": [
            {
                "sentence_id": 122,
                "prompt": "کل مبلغ خرید چقدر است؟",
                "options": [
                    ("۹٫۲۰ یورو", True),
                    ("۹٫۰۲ یورو", False),
                    ("۲٫۹۰ یورو", False),
                    ("۱۹٫۲۰ یورو", False),
                ],
                "explanation": "عبارت «neun Euro zwanzig» یعنی ۹ یورو و ۲۰ سنت (9,20 €).",
            },
            {
                "sentence_id": 125,
                "prompt": "قیمت این کالا چقدر است؟",
                "options": [
                    ("۳٫۹۰ یورو", True),
                    ("۳٫۱۹ یورو", False),
                    ("۹٫۳۰ یورو", False),
                    ("۲٫۹۰ یورو", False),
                ],
                "explanation": "عبارت «drei Euro neunzig» یعنی ۳ یورو و ۹۰ سنت (3,90 €).",
            },
            {
                "sentence_id": 119,
                "prompt": "مشتری چه مقداری از این دو قلم کالا می‌خواهد؟",
                "options": [
                    ("۱ کیلو سیب‌زمینی و ۱ کیلو گوجه", True),
                    ("۲ کیلو سیب‌زمینی و ۱ کیلو گوجه", False),
                    ("۱ کیلو سیب‌زمینی و ۲ کیلو گوجه", False),
                    ("نیم کیلو سیب‌زمینی و ۱ کیلو گوجه", False),
                ],
                "explanation": "عبارت «ein Kilo Kartoffeln und ein Kilo Tomaten» دقیقاً بیانگر یک کیلو از هر کدام است.",
            },
            {
                "sentence_id": 121,
                "prompt": "تعداد میوه‌های درخواستی چقدر است؟",
                "options": [
                    ("۳ موز و ۱ پرتقال", True),
                    ("۱ موز و ۳ پرتقال", False),
                    ("۲ موز و ۱ پرتقال", False),
                    ("۳ موز و ۲ پرتقال", False),
                ],
                "explanation": "«drei Bananen» یعنی ۳ عدد موز و «eine Orange» یعنی ۱ عدد پرتقال.",
            },
            {
                "sentence_id": 127,
                "prompt": "خریدار چه نان‌هایی می‌خرد؟",
                "options": [
                    ("۱ نان بزرگ و ۲ نان کوچک (Brötchen)", True),
                    ("۲ نان بزرگ و ۱ نان کوچک", False),
                    ("۱ نان بزرگ و ۱ نان کوچک", False),
                    ("۲ نان بزرگ و ۲ نان کوچک", False),
                ],
                "explanation": "در زبان آلمانی «Brot» یعنی نان کامل و «Brötchen» نان کوچک ساندویچی است؛ «ein Brot und zwei Brötchen» یعنی ۱ نان و ۲ نان کوچک.",
            },
        ],
    },
    15: {
        "title": "شنیدن و تشخیص اطلاعات: روزها و ساعت قرارها",
        "instruction": "به فایل صوتی گوش کن و بر اساس اطلاعاتی که می‌شنوی، پاسخ درست را انتخاب کن.",
        "questions": [
            {
                "sentence_id": 197,
                "prompt": "قرار ملاقات در چه روزی از هفته است؟",
                "options": [
                    ("پنجشنبه", True),
                    ("سه‌شنبه", False),
                    ("چهارشنبه", False),
                    ("جمعه", False),
                ],
                "explanation": "واژهٔ «Donnerstag» یعنی پنجشنبه. با «Dienstag» (سه‌شنبه) اشتباه نشود.",
            },
            {
                "sentence_id": 199,
                "prompt": "قرار دکتر در چه ساعتی است؟",
                "options": [
                    ("۱۰:۰۰", True),
                    ("۹:۰۰", False),
                    ("۱۱:۰۰", False),
                    ("۸:۰۰", False),
                ],
                "explanation": "عبارت «Um zehn Uhr» یعنی ساعت ۱۰:۰۰.",
            },
            {
                "sentence_id": 204,
                "prompt": "برنامه در چه روزی و چه ساعتی است و زمان قرار ملاقات کی است؟",
                "options": [
                    ("برنامه جمعه ساعت ۸:۰۰، ملاقات ساعت ۷:۰۰ جلوی تئاتر", True),
                    ("برنامه جمعه ساعت ۷:۰۰، ملاقات ساعت ۸:۰۰ جلوی تئاتر", False),
                    ("برنامه پنجشنبه ساعت ۸:۰۰، ملاقات ساعت ۷:۰۰ جلوی تئاتر", False),
                    ("برنامه جمعه ساعت ۸:۰۰، ملاقات ساعت ۶:۰۰ جلوی سینما", False),
                ],
                "explanation": "در فایل گفته می‌شود برنامه جمعه ساعت ۸ است («Am Freitag um acht») اما ساعت ۷ برای دیدن هم قرار می‌گذارند («um sieben vor dem Theater»).",
            },
            {
                "sentence_id": 209,
                "prompt": "فیلم چه ساعتی شروع می‌شود؟",
                "options": [
                    ("۸:۰۰", True),
                    ("۷:۰۰", False),
                    ("۹:۰۰", False),
                    ("۸:۳۰", False),
                ],
                "explanation": "عبارت «um acht Uhr» یعنی ساعت ۸:۰۰.",
            },
            {
                "sentence_id": 210,
                "prompt": "طول مدت کلاس یا دوره چقدر است؟",
                "options": [
                    ("۲ ساعت", True),
                    ("۱ ساعت", False),
                    ("۳ ساعت", False),
                    ("۴ ساعت", False),
                ],
                "explanation": "«zwei Stunden» یعنی ۲ ساعت (Stunde = ساعت به‌عنوان واحد شمارش طول زمان).",
            },
        ],
    },
    17: {
        "title": "شنیدن و تشخیص اطلاعات: سفر، هتل و اعلام‌ها",
        "instruction": "به فایل صوتی گوش کن و بر اساس اطلاعاتی که می‌شنوی، پاسخ درست را انتخاب کن.",
        "questions": [
            {
                "sentence_id": 230,
                "prompt": "نوع اتاق و مدت اقامت چقدر است؟",
                "options": [
                    ("اتاق یک‌نفره برای ۳ شب", True),
                    ("اتاق دونفره برای ۳ شب", False),
                    ("اتاق یک‌نفره برای ۲ شب", False),
                    ("اتاق دونفره برای ۱ شب", False),
                ],
                "explanation": "واژهٔ «Einzelzimmer» یعنی اتاق یک‌نفره (نه Doppelzimmer = دونفره) و «drei Nächte» یعنی ۳ شب.",
            },
            {
                "sentence_id": 232,
                "prompt": "هزینه اقامت هر شب چقدر است و وضعیت صبحانه چیست؟",
                "options": [
                    ("۶۰ یورو شبی — صبحانه رایگان/شامل است", True),
                    ("۱۶ یورو شبی — صبحانه رایگان/شامل است", False),
                    ("۶۰ یورو شبی — صبحانه جداگانه حساب می‌شود", False),
                    ("۷۰ یورو شبی — صبحانه شامل است", False),
                ],
                "explanation": "عدد «60» در آلمانی «sechzig» است (با sechzehn = ۱۶ اشتباه نشود) و «Frühstück ist inklusive» یعنی صبحانه روی قیمت اتاق است.",
            },
            {
                "sentence_id": 234,
                "prompt": "مسافر بلیت قطار به کدام مقصد را می‌خواهد؟",
                "options": [
                    ("برلین (Berlin)", True),
                    ("بن (Bonn)", False),
                    ("برمن (Bremen)", False),
                    ("مونیخ (München)", False),
                ],
                "explanation": "در جمله صراحتاً گفته می‌شود «nach Berlin» یعنی به مقصد برلین.",
            },
            {
                "sentence_id": 237,
                "prompt": "مسافر چند چمدان همراه دارد؟",
                "options": [
                    ("۲ چمدان", True),
                    ("۱ چمدان", False),
                    ("۳ چمدان", False),
                    ("۴ چمدان", False),
                ],
                "explanation": "«zwei Koffer» یعنی ۲ عدد چمدان.",
            },
            {
                "sentence_id": 231,
                "prompt": "مسافر در فایل صوتی چه سؤالی درباره اتاق می‌پرسد؟",
                "options": [
                    ("قیمت اتاق برای هر شب چقدر است؟", True),
                    ("آیا اتاق اینترنت و وای‌فای دارد؟", False),
                    ("ساعت تحویل اتاق چه موقع است؟", False),
                    ("اتاق در کدام طبقه قرار دارد؟", False),
                ],
                "explanation": "مسافر می‌پرسد: «Was kostet das Zimmer pro Nacht?» که یعنی هزینهٔ اتاق برای هر شب چقدر است.",
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Seed targeted A1 listening discrimination exercises in L03, L06, L09, L15, L17."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without saving to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        prefix = "[DRY-RUN] " if dry_run else ""

        total_exercises = 0
        total_questions = 0

        with transaction.atomic():
            for lesson_order, data in DRILL_DATA.items():
                lesson = Lesson.objects.filter(order=lesson_order).first()
                if not lesson:
                    self.stdout.write(self.style.WARNING(f"Lesson {lesson_order} not found, skipping."))
                    continue

                ex = Exercise.objects.filter(lesson=lesson, title=data["title"]).first()
                if not ex:
                    if dry_run:
                        ex = Exercise(
                            lesson=lesson,
                            title=data["title"],
                            instruction=data["instruction"],
                            type=Exercise.ExerciseType.LISTENING,
                            difficulty=Exercise.Difficulty.EASY,
                            order=0,
                            is_published=True,
                        )
                    else:
                        max_order = (
                            Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"] or 0
                        )
                        ex = Exercise.objects.create(
                            lesson=lesson,
                            title=data["title"],
                            instruction=data["instruction"],
                            type=Exercise.ExerciseType.LISTENING,
                            difficulty=Exercise.Difficulty.EASY,
                            order=max_order + 1,
                            is_published=True,
                        )
                    total_exercises += 1
                else:
                    if not dry_run:
                        ex.instruction = data["instruction"]
                        ex.type = Exercise.ExerciseType.LISTENING
                        ex.is_published = True
                        ex.save()

                for idx, q_data in enumerate(data["questions"], start=1):
                    sentence_id = q_data["sentence_id"]
                    sentence = Sentence.objects.filter(pk=sentence_id).first()
                    audio_name = sentence.audio.name if sentence and sentence.audio else ""

                    if not dry_run:
                        q, q_created = Question.objects.get_or_create(
                            exercise=ex,
                            order=idx,
                            defaults={
                                "prompt": q_data["prompt"],
                                "audio": audio_name,
                                "explanation": q_data["explanation"],
                            },
                        )
                        if not q_created:
                            q.prompt = q_data["prompt"]
                            q.audio = audio_name
                            q.explanation = q_data["explanation"]
                            q.save()

                        # Ensure answers match exactly
                        existing_answers = list(q.answers.order_by("order"))
                        if not existing_answers:
                            for a_idx, (a_text, a_correct) in enumerate(q_data["options"], start=1):
                                Answer.objects.create(
                                    question=q,
                                    text=a_text,
                                    is_correct=a_correct,
                                    order=a_idx,
                                )
                        else:
                            for a_idx, (a_text, a_correct) in enumerate(q_data["options"], start=1):
                                if a_idx <= len(existing_answers):
                                    ans = existing_answers[a_idx - 1]
                                    ans.text = a_text
                                    ans.is_correct = a_correct
                                    ans.save()
                                else:
                                    Answer.objects.create(
                                        question=q,
                                        text=a_text,
                                        is_correct=a_correct,
                                        order=a_idx,
                                    )

                        total_questions += 1
                    else:
                        total_questions += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix}Successfully processed {len(DRILL_DATA)} listening discrimination exercises "
                    f"with {total_questions} questions across Lessons 3, 6, 9, 15, 17."
                )
            )
