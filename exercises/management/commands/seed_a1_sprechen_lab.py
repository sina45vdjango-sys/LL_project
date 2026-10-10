"""Seed authentic Goethe A1 Sprechen Lab exercises (Oral Exam Teile 1, 2, and 3).

Phase 9 of the pedagogical roadmap:
Introduces 3 curated Goethe Sprechen Lab exercises (+15 questions) across:
- Lesson 01: Begrüßung & Kennenlernen (Teil 1: Sich vorstellen & Spontane Fragen) - 5 questions
- Lesson 08: Essen, Trinken & Einkaufen (Teil 2: Thema-Karten — Fragen & Reaktionen) - 5 questions
- Lesson 14: Alltag & Höfliche Bitten (Teil 3: Bitte-Karten — Bitten & Reagieren) - 5 questions

All exercises use Exercise.ExerciseType.SPEAKING with typed/choice verbal responses,
multiple accepted case/whitespace-forgiving variants, pronunciation notes,
and structured Persian etiquette and grammatical feedback.

Idempotent and supports --dry-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, Question
from lessons.models import Lesson


SPRECHEN_LAB_DATA = {
    1: {
        "title": "کارگاه گفتن: معرفی خود و پاسخ به پرسش‌های ممتحن (Sprechen Teil 1)",
        "instruction": "در بخش اول آزمون گفتاری گوته، باید خود را بر اساس کلیدواژه‌ها معرفی کنی و به دو سؤال شفاهی ممتحن (هجی کردن نام و بیان شماره) پاسخ دهی.",
        "questions": [
            {
                "prompt": "کارت معرفی — Name & Herkunft: جمله‌ای برای معرفی نام و کشورت (ایران) بنویس:",
                "answers": [
                    "Ich heiße Maryam und komme aus dem Iran.",
                    "Ich heiße Ali und komme aus dem Iran.",
                    "Mein Name ist Sara und ich komme aus dem Iran.",
                    "Ich bin Reza und komme aus dem Iran.",
                ],
                "explanation": "در بخش معرفی شفاهی A1 ساختار استاندارد: «Ich heiße ... und komme aus dem Iran.» است. به یاد داشته باشید که کشور ایران با حرف تعریف می‌آید: «aus dem Iran».",
            },
            {
                "prompt": "کارت معرفی — Alter & Wohnort: جمله‌ای برای بیان سن (مثلاً ۲۴ سال) و شهر سکونت (مثلاً تهران) بگو:",
                "answers": [
                    "Ich bin 24 Jahre alt und wohne in Teheran.",
                    "Ich bin 25 Jahre alt und wohne in Teheran.",
                    "Ich wohne in Teheran und bin 24 Jahre alt.",
                    "Ich bin 20 Jahre alt und wohne in Isfahan.",
                ],
                "explanation": "ساختار بیان سن و سکونت: «Ich bin [عدد] Jahre alt und wohne in [شهر].» فعل همیشه در جایگاه دوم جمله قرار دارد.",
            },
            {
                "prompt": "کارت معرفی — Beruf & Sprachen: جمله‌ای دربارهٔ شغل (مثلاً مهندس یا دانشجو) و زبان‌هایی که صحبت می‌کنی بگو:",
                "answers": [
                    "Ich arbeite als Ingenieur und spreche Persisch und Deutsch.",
                    "Ich bin Student und spreche Persisch, Englisch und Deutsch.",
                    "Ich arbeite als Ingenieurin und spreche Deutsch.",
                    "Ich bin Studentin und spreche Persisch und Deutsch.",
                ],
                "explanation": "برای شغل از حرف اضافهٔ als استفاده می‌شود: «Ich arbeite als ...» و برای زبان‌ها: «Ich spreche Persisch, Englisch und ein bisschen Deutsch.».",
            },
            {
                "prompt": "سؤال ناگهانی ممتحن — Buchstabieren: ممتحن می‌گوید: «Buchstabieren Sie bitte Ihren Namen!» نام خود (مثلاً S-A-R-A یا M-A-R-Y-A-M) را هجی کن:",
                "answers": [
                    "S-A-R-A",
                    "M-A-R-Y-A-M",
                    "A-L-I",
                    "Sara",
                    "Maryam",
                    "Ali",
                    "S A R A",
                    "M A R Y A M",
                ],
                "explanation": "در این بخش تلفظ دقیق حروف الفبای آلمانی سنجیده می‌شود. مثلاً S (اِس)، A (آ)، R (اِر)، A (آ).",
            },
            {
                "prompt": "سؤال ناگهانی ممتحن — Telefonnummer: ممتحن می‌گوید: «Wie ist Ihre Telefonnummer?» شماره تلفن فرضی (مثلاً 0176 12345678) را بگو:",
                "answers": [
                    "0176 12345678",
                    "0176 12 34 56 78",
                    "017612345678",
                    "0176 45 67 89",
                ],
                "explanation": "شماره تلفن‌ها معمولاً دو رقم دو رقم خوانده می‌شوند: null-eins-sieben-sechs ... ارقام دورقمی از راست به چپ خوانده می‌شوند.",
            },
        ],
    },
    8: {
        "title": "کارگاه گفتن: کارت‌های موضوعی و تبادل اطلاعات (Sprechen Teil 2)",
        "instruction": "در بخش دوم آزمون گوته، به نوبت یک کارت موضوعی (Thema) می‌کشی، از طرف مقابل سؤال می‌پرسی و به سؤال او پاسخ می‌دهی.",
        "questions": [
            {
                "prompt": "کارت ۱ — [Thema: Essen und Trinken | Wort: Frühstück] با این کارت سؤالی دربارهٔ صبحانه بساز (مثلاً صبحانه چه می‌خوری؟):",
                "answers": [
                    "Was isst du zum Frühstück?",
                    "Was frühstückst du?",
                    "Was essen Sie zum Frühstück?",
                ],
                "explanation": "در W-Frage واژهٔ پرسشی اول و فعل صرف‌شده در جایگاه دوم می‌آید: «Was isst du zum Frühstück?» (برای صبحانه چه می‌خوری؟). پاسخ الگو: «Ich esse Brot mit Käse.»",
            },
            {
                "prompt": "کارت ۲ — [Thema: Einkaufen | Wort: Supermarkt] با این کارت سؤالی دربارهٔ رفتن به سوپرمارکت بساز (کی به سوپرمارکت می‌روی؟):",
                "answers": [
                    "Wann gehst du in den Supermarkt?",
                    "Gehst du in den Supermarkt?",
                    "Wann gehen Sie in den Supermarkt?",
                ],
                "explanation": "استفاده از Wann (چه زمانی): «Wann gehst du in den Supermarkt?» یا سؤال بله/خیر: «Gehst du heute in den Supermarkt?». پاسخ الگو: «Ich gehe am Nachmittag in den Supermarkt.»",
            },
            {
                "prompt": "کارت ۳ — [Thema: Freizeit | Wort: Sport] با این کارت سؤالی دربارهٔ ورزش بساز (آیا ورزش می‌کنی؟ / چه ورزشی؟):",
                "answers": [
                    "Treibst du gern Sport?",
                    "Machst du Sport?",
                    "Welchen Sport machst du?",
                    "Treiben Sie Sport?",
                ],
                "explanation": "اصطلاح رایج در آلمانی: «Sport treiben» یا «Sport machen». سؤال بله/خیر با فعل در اول: «Treibst du gern Sport?» (آیا اهل ورزش هستی؟). پاسخ الگو: «Ja, ich spiele gern Fußball.»",
            },
            {
                "prompt": "کارت ۴ — [Thema: Wohnen | Wort: Zimmer] با این کارت سؤالی دربارهٔ تعداد اتاق‌های خانه بساز:",
                "answers": [
                    "Wie viele Zimmer hat deine Wohnung?",
                    "Wie viele Zimmer hat Ihre Wohnung?",
                    "Hat deine Wohnung einen Balkon?",
                ],
                "explanation": "پرسش با Wie viele (چه تعداد): «Wie viele Zimmer hat deine Wohnung?». پاسخ الگو: «Meine Wohnung hat drei Zimmer.»",
            },
            {
                "prompt": "کارت ۵ — [Thema: Beruf & Arbeit | Wort: Arbeitszeit] با این کارت سؤالی دربارهٔ ساعت کاری بساز (ساعت چند کار می‌کنی؟):",
                "answers": [
                    "Wann arbeitest du?",
                    "Wie sind deine Arbeitszeiten?",
                    "Wann arbeiten Sie?",
                    "Wie lange arbeitest du?",
                ],
                "explanation": "پرسش دربارهٔ زمان کار: «Wann arbeitest du?» یا «Wie lange arbeitest du?». پاسخ الگو: «Ich arbeite von 8 bis 17 Uhr.»",
            },
        ],
    },
    14: {
        "title": "کارگاه گفتن: کارت‌های درخواست و واکنش در موقعیت‌های روزمره (Sprechen Teil 3)",
        "instruction": "در بخش سوم آزمون گوته، یک کارت تصویری/موقعیتی می‌کشی و از طرف مقابل یک درخواست مؤدبانه (Bitte) مطرح می‌کنی.",
        "questions": [
            {
                "prompt": "کارت ۱ — [موقعیت: یک لیوان آب (Ein Glas Wasser)] یک درخواست مؤدبانه برای گرفتن آب مطرح کن (می‌شود لطفاً یک لیوان آب به من بدهید؟):",
                "answers": [
                    "Können Sie mir bitte ein Glas Wasser geben?",
                    "Gib mir bitte ein Glas Wasser.",
                    "Kann ich bitte ein Glas Wasser haben?",
                    "Geben Sie mir bitte ein Glas Wasser.",
                ],
                "explanation": "مؤدبانه‌ترین فرمول درخواست در A1 استفاده از «Können Sie mir bitte ... geben?» است. فرم امری مؤدبانه: «Geben Sie mir bitte ein Glas Wasser.». واکنش الگو: «Ja, natürlich. Hier, bitte!»",
            },
            {
                "prompt": "کارت ۲ — [موقعیت: در باز است (Die Tür)] درخواست کن در را ببندند (لطفاً در را ببندید):",
                "answers": [
                    "Machen Sie bitte die Tür zu.",
                    "Können Sie bitte die Tür zumachen?",
                    "Schließen Sie bitte die Tür.",
                ],
                "explanation": "فعل جداشدنی zumachen (بستن): در امری پیشوند zu به انتهای جمله می‌رود: «Machen Sie bitte die Tür zu.». واکنش الگو: «Ja, gern!» یا «Mache ich sofort.»",
            },
            {
                "prompt": "کارت ۳ — [موقعیت: خودکار / مداد (Der Stift)] درخواست کن خودکار طرف مقابل را قرض بگیری:",
                "answers": [
                    "Kann ich bitte deinen Stift haben?",
                    "Gib mir bitte deinen Stift.",
                    "Geben Sie mir bitte einen Stift.",
                    "Kann ich Ihren Stift haben?",
                ],
                "explanation": "فرمول درخواست دوستانه: «Kann ich bitte deinen Stift haben?» یا امری: «Gib mir bitte den Stift.». واکنش الگو: «Ja, nimm ihn dir!» (بله، بردار).",
            },
            {
                "prompt": "کارت ۴ — [موقعیت: متوجه نشدی / تکرار (Wiederholen)] از ممتحن یا طرف مقابل بخواه حرفش را تکرار کند:",
                "answers": [
                    "Können Sie das bitte wiederholen?",
                    "Wiederholen Sie das bitte.",
                    "Kannst du das bitte wiederholen?",
                ],
                "explanation": "عبارت کلیدی و حیاتی در آزمون و مکالمه: «Können Sie das bitte wiederholen?» (می‌شود لطفاً این را تکرار کنید؟). واکنش الگو: «Ja, natürlich.»",
            },
            {
                "prompt": "کارت ۵ — [موقعیت: تلفن همراه روشن است (Handy ausmachen)] درخواست کن تلفن همراه را خاموش کنند:",
                "answers": [
                    "Machen Sie bitte das Handy aus.",
                    "Können Sie bitte das Handy ausmachen?",
                    "Schalten Sie bitte das Handy aus.",
                ],
                "explanation": "فعل جداشدنی ausmachen (خاموش کردن دستگاه): «Machen Sie bitte das Handy aus.». واکنش الگو: «Entschuldigung, mache ich sofort!» (ببخشید، الان خاموش می‌کنم).",
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Seed authentic Goethe A1 Sprechen Lab exercises (Oral Exam Teile 1, 2, and 3)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be seeded without modifying the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        prefix = "[DRY-RUN] " if dry_run else ""

        total_exercises = 0
        total_questions = 0

        with transaction.atomic():
            for lesson_order, ex_data in SPRECHEN_LAB_DATA.items():
                lesson = Lesson.objects.filter(order=lesson_order).first()
                if not lesson:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{prefix}Lesson {lesson_order} not found. Skipping."
                        )
                    )
                    continue

                ex = Exercise.objects.filter(lesson=lesson, title=ex_data["title"]).first()
                if not ex:
                    next_order = (
                        Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"]
                        or 0
                    ) + 1
                    if not dry_run:
                        ex = Exercise.objects.create(
                            lesson=lesson,
                            title=ex_data["title"],
                            instruction=ex_data["instruction"],
                            type=Exercise.ExerciseType.SPEAKING,
                            difficulty=Exercise.Difficulty.MEDIUM,
                            order=next_order,
                            is_published=True,
                        )
                else:
                    if not dry_run:
                        ex.instruction = ex_data["instruction"]
                        ex.type = Exercise.ExerciseType.SPEAKING
                        ex.is_published = True
                        ex.save()

                total_exercises += 1

                for idx, q_data in enumerate(ex_data["questions"], start=1):
                    if not dry_run:
                        q, _ = Question.objects.get_or_create(
                            exercise=ex,
                            order=idx,
                            defaults={
                                "prompt": q_data["prompt"],
                                "explanation": q_data["explanation"],
                            },
                        )
                        q.prompt = q_data["prompt"]
                        q.explanation = q_data["explanation"]
                        q.save()

                        # Seed accepted oral production answers
                        q.answers.all().delete()
                        for a_idx, ans_text in enumerate(q_data["answers"], start=1):
                            Answer.objects.create(
                                question=q,
                                text=ans_text,
                                is_correct=True,
                                order=a_idx,
                            )

                    total_questions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Successfully processed {total_exercises} Sprechen Lab exercises "
                f"with {total_questions} questions across Lessons 1, 8, and 14."
            )
        )
