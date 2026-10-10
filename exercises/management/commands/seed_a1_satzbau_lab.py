"""Seed authentic German syntax & sentence-building lab exercises (Satzbau Playground).

Phase 11 of the pedagogical roadmap:
Introduces 5 curated Satzbau exercises (+25 questions) across core syntax milestones:
- Lesson 04: Verb in Position 2 & Inversion (Temporaladverb in Position 1)
- Lesson 06: Separable Verbs Satzklammer (Verb in Pos 2, Präfix at Sentence End)
- Lesson 13: Modal Verbs Satzklammer (Modalverb in Pos 2, Infinitiv at Sentence End)
- Lesson 16: Adverb Order & Local Direction (Temporal vor Lokal)
- Lesson 19: Perfekt Satzklammer with haben (haben in Pos 2, Partizip II at Sentence End)

All exercises use Exercise.ExerciseType.SCRAMBLE with multiple valid German orderings,
clear Persian pedagogical hints, and full grammar explanations.

Additive, idempotent, and supports --dry-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, Question
from lessons.models import Lesson


SATZBAU_LAB_DATA = {
    4: {
        "title": "کارگاه چیدمان جمله: جایگاه فعل و وارونگی فاعل و قید (Satzbau: Verb auf Position 2)",
        "instruction": "در جملات خبری آلمانی، فعل صرف‌شده همیشه در جایگاه ۲ قرار دارد. اگر جمله را با قید زمان یا مکان شروع کنی، فاعل به جایگاه ۳ می‌رود. کلمات را با کلیک مرتب کن.",
        "questions": [
            {
                "prompt": "«امروز من با خواهرم آلمانی می‌خوانم» (قید زمان Heute در جایگاه ۱):",
                "answers": [
                    "Heute lerne ich mit meiner Schwester Deutsch.",
                    "Ich lerne heute mit meiner Schwester Deutsch.",
                ],
                "explanation": "قاعدهٔ وارونگی: وقتی جمله با قید زمان (Heute) شروع می‌شود، فعل (lerne) در جایگاه ۲ می‌ماند و فاعل (ich) بلافاصله بعد از فعل در جایگاه ۳ می‌آید.",
            },
            {
                "prompt": "«برادرم در برلین زندگی می‌کند» (فاعل در جایگاه ۱):",
                "answers": [
                    "Mein Bruder wohnt jetzt in Berlin.",
                    "Jetzt wohnt mein Bruder in Berlin.",
                ],
                "explanation": "در جملهٔ ساده خبری: فاعل (Mein Bruder) در جایگاه ۱ و فعل (wohnt) در جایگاه ۲ قرار می‌گیرد.",
            },
            {
                "prompt": "«فردا ما با هم پدر و مادرم را می‌بینیم» (قید زمان Morgen در جایگاه ۱):",
                "answers": [
                    "Morgen besuchen wir zusammen meine Eltern.",
                    "Wir besuchen morgen zusammen meine Eltern.",
                ],
                "explanation": "فعل besuchen در جایگاه ۲، فاعل wir در جایگاه ۳ و مفعول meine Eltern در ادامه می‌آید.",
            },
            {
                "prompt": "«من یک برادر و دو خواهر دارم» (فاعل در جایگاه ۱):",
                "answers": [
                    "Ich habe einen Bruder und zwei Schwestern.",
                ],
                "explanation": "فعل habe در جایگاه ۲ قرار می‌گیرد و مفعول‌های مستقیم (einen Bruder und zwei Schwestern) بعد از آن می‌آیند.",
            },
            {
                "prompt": "«گاهی اوقات من به خانواده‌ام زنگ می‌زنم» (قید Manchmal در جایگاه ۱):",
                "answers": [
                    "Manchmal rufe ich meine Familie an.",
                    "Ich rufe manchmal meine Familie an.",
                ],
                "explanation": "فعل جداشدنی anrufen: بخش صرف‌شده (rufe) در جایگاه ۲ و پیشوند (an) به عنوان آخرین کلمهٔ جمله قاب را می‌بندد.",
            },
        ],
    },
    6: {
        "title": "کارگاه چیدمان جمله: افعال جداشدنی و ساختار قاب (Satzbau: Trennbare Verben)",
        "instruction": "در افعال جداشدنی، بخش اصلی فعل در جایگاه ۲ صرف می‌شود و پیشوند جداشدنی (Präfix) دقیقاً به آخرین کلمهٔ جمله پرتاب می‌شود (قانون قاب جمله).",
        "questions": [
            {
                "prompt": "«من هر روز صبح ساعت ۷ بیدار می‌شوم» (فعل: aufstehen):",
                "answers": [
                    "Ich stehe jeden Morgen um sieben Uhr auf.",
                    "Jeden Morgen stehe ich um sieben Uhr auf.",
                ],
                "explanation": "فعل aufstehen: stehe در جایگاه ۲ و پیشوند auf در انتهای جمله قرار می‌گیرد.",
            },
            {
                "prompt": "«او بعدازظهر در سوپرمارکت خرید می‌کند» (فعل: einkaufen):",
                "answers": [
                    "Er kauft am Nachmittag im Supermarkt ein.",
                    "Am Nachmittag kauft er im Supermarkt ein.",
                ],
                "explanation": "فعل einkaufen: kauft در جایگاه ۲ و پیشوند ein در پایان جمله قاب را می‌بندد.",
            },
            {
                "prompt": "«قطار ساعت ۱۵ به ایستگاه می‌رسد» (فعل: ankommen):",
                "answers": [
                    "Der Zug kommt um 15 Uhr am Bahnhof an.",
                    "Um 15 Uhr kommt der Zug am Bahnhof an.",
                ],
                "explanation": "فعل ankommen: kommt در جایگاه ۲ و پیشوند an در انتهای جمله.",
            },
            {
                "prompt": "«سارا امروز عصر دوستانش را دعوت می‌کند» (فعل: einladen):",
                "answers": [
                    "Sara lädt heute Abend ihre Freunde ein.",
                    "Heute Abend lädt Sara ihre Freunde ein.",
                ],
                "explanation": "فعل einladen: lädt در جایگاه ۲ و پیشوند ein در پایان جمله قاب را می‌بندد.",
            },
            {
                "prompt": "«ما امروز عصر با هم تلویزیون تماشا می‌کنیم» (فعل: fernsehen):",
                "answers": [
                    "Wir sehen heute Abend zusammen fern.",
                    "Heute Abend sehen wir zusammen fern.",
                ],
                "explanation": "فعل fernsehen: sehen در جایگاه ۲ و پیشوند fern در آخرین کلمهٔ جمله.",
            },
        ],
    },
    13: {
        "title": "کارگاه چیدمان جمله: افعال مدال و مصدر در پایان جمله (Satzbau: Modalverben)",
        "instruction": "در جملات دارای فعل مدال (können, wollen, müssen...)، فعل مدال در جایگاه ۲ صرف می‌شود و فعل اصلی به صورت مصدر دست‌نخورده به آخرین کلمهٔ جمله می‌رود.",
        "questions": [
            {
                "prompt": "«من می‌توانم خیلی خوب گیتار بنوازم» (فعل مدال: können):",
                "answers": [
                    "Ich kann sehr gut Gitarre spielen.",
                    "Sehr gut kann ich Gitarre spielen.",
                ],
                "explanation": "فعل مدال kann در جایگاه ۲ و مصدر spielen در پایان جمله قرار می‌گیرد.",
            },
            {
                "prompt": "«ما می‌خواهیم امشب با هم پیتزا بپزیم» (فعل مدال: wollen):",
                "answers": [
                    "Wir wollen heute Abend zusammen Pizza kochen.",
                    "Heute Abend wollen wir zusammen Pizza kochen.",
                ],
                "explanation": "فعل مدال wollen در جایگاه ۲ و مصدر kochen در انتهای جمله.",
            },
            {
                "prompt": "«علی باید امروز برای امتحان درس بخواند» (فعل مدال: müssen):",
                "answers": [
                    "Ali muss heute für die Prüfung lernen.",
                    "Heute muss Ali für die Prüfung lernen.",
                ],
                "explanation": "فعل مدال muss در جایگاه ۲ و مصدر lernen در پایان جمله.",
            },
            {
                "prompt": "«آیا شما می‌توانید فردا به من کمک کنید؟» (سؤال بله/خیر با مدال):",
                "answers": [
                    "Können Sie mir morgen bitte helfen?",
                ],
                "explanation": "در سؤال بله/خیر، فعل مدال (Können) در جایگاه ۱ می‌آید و مصدر (helfen) در انتهای جمله قاب را می‌بندد.",
            },
            {
                "prompt": "«او می‌خواهد در تابستان به آلمان سفر کند» (فعل مدال: möchten):",
                "answers": [
                    "Er möchte im Sommer nach Deutschland reisen.",
                    "Im Sommer möchte er nach Deutschland reisen.",
                ],
                "explanation": "فعل möchte در جایگاه ۲ و مصدر reisen در انتهای جمله.",
            },
        ],
    },
    16: {
        "title": "کارگاه چیدمان جمله: قیدهای زمان و مکان (Satzbau: Temporal vor Lokal)",
        "instruction": "در آلمانی ترتیب قیدها قانون TeKaMoLo را دنبال می‌کند: قید زمان (Wann?) همیشه قبل از قید مکان (Wo / Wohin?) می‌آید.",
        "questions": [
            {
                "prompt": "«اتوبوس سر وقت به ایستگاه مرکزی حرکت می‌کند» (زمان قبل از مکان):",
                "answers": [
                    "Der Bus fährt pünktlich zum Hauptbahnhof.",
                    "Pünktlich fährt der Bus zum Hauptbahnhof.",
                ],
                "explanation": "ترتیب استاندارد آلمانی: قید زمان/حالت (pünktlich) قبل از قید مکان/مقصد (zum Hauptbahnhof).",
            },
            {
                "prompt": "«من امروز بعدازظهر به کتابخانه می‌روم» (زمان قبل از مکان):",
                "answers": [
                    "Ich gehe heute Nachmittag in die Bibliothek.",
                    "Heute Nachmittag gehe ich in die Bibliothek.",
                ],
                "explanation": "قید زمان (heute Nachmittag) قبل از قید مکان (in die Bibliothek) قرار می‌گیرد.",
            },
            {
                "prompt": "«ما روزهای شنبه در پارک ورزش می‌کنیم» (زمان قبل از مکان):",
                "answers": [
                    "Wir machen am Samstag Sport im Park.",
                    "Am Samstag machen wir Sport im Park.",
                ],
                "explanation": "قید زمان (am Samstag) قبل از قید مکان (im Park).",
            },
            {
                "prompt": "«مرد غریبه مستقیم به سمت میدان می‌رود» (فعل در جایگاه ۲):",
                "answers": [
                    "Der Mann geht geradeaus zum Marktplatz.",
                    "Geradeaus geht der Mann zum Marktplatz.",
                ],
                "explanation": "فعل geht در جایگاه ۲ و جهت حرکت در ادامه جمله قرار می‌گیرد.",
            },
            {
                "prompt": "«دفتر کار بعد از چهارراه سمت چپ قرار دارد» (توصیف آدرس):",
                "answers": [
                    "Das Büro liegt nach der Kreuzung links.",
                    "Nach der Kreuzung liegt das Büro links.",
                ],
                "explanation": "فعل liegt در جایگاه ۲ و جهت‌های آدرس‌دهی در ادامه جمله.",
            },
        ],
    },
    19: {
        "title": "کارگاه چیدمان جمله: زمان گذشتهٔ کامل و Partizip II (Satzbau: Perfekt-Klammer)",
        "instruction": "در زمان گذشته کامل با haben، فعل haben در جایگاه ۲ صرف می‌شود و اسم مفعول (Partizip II) به عنوان آخرین کلمهٔ جمله قاب را می‌بندد.",
        "questions": [
            {
                "prompt": "«من دیروز یک لپ‌تاپ نو خریدم» (فعل: haben + gekauft):",
                "answers": [
                    "Ich habe gestern einen neuen Laptop gekauft.",
                    "Gestern habe ich einen neuen Laptop gekauft.",
                ],
                "explanation": "فعل کمکی habe در جایگاه ۲ و اسم مفعول gekauft در انتهای جمله قاب گذشته را می‌بندد.",
            },
            {
                "prompt": "«ما دیروز مدت زیادی با مدیر صحبت کردیم» (فعل: haben + gesprochen):",
                "answers": [
                    "Wir haben gestern lange mit dem Chef gesprochen.",
                    "Gestern haben wir lange mit dem Chef gesprochen.",
                ],
                "explanation": "فعل haben در جایگاه ۲ و اسم مفعول gesprochen در انتهای جمله.",
            },
            {
                "prompt": "«او دیشب ایمیل مهم را ارسال کرد» (فعل: haben + geschickt):",
                "answers": [
                    "Er hat gestern Abend die wichtige E-Mail geschickt.",
                    "Gestern Abend hat er die wichtige E-Mail geschickt.",
                ],
                "explanation": "فعل hat در جایگاه ۲ و اسم مفعول geschickt در انتهای جمله.",
            },
            {
                "prompt": "«آیا تو تکالیف را به طور کامل انجام دادی؟» (سؤال گذشته بله/خیر):",
                "answers": [
                    "Hast du die Hausaufgaben komplett gemacht?",
                ],
                "explanation": "در سؤال بله/خیر، فعل کمکی Hast در آغاز و Partizip II (gemacht) در انتهای جمله.",
            },
            {
                "prompt": "«آن‌ها دیروز اتاق کار را مرتب تمیز کردند» (فعل: haben + aufgeräumt):",
                "answers": [
                    "Sie haben gestern das Büro ordentlich aufgeräumt.",
                    "Gestern haben sie das Büro ordentlich aufgeräumt.",
                ],
                "explanation": "فعل haben در جایگاه ۲ و اسم مفعول فعل جداشدنی aufgeräumt (با ge در میانه) در پایان جمله.",
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Seed authentic German syntax & sentence-building lab exercises (Satzbau Playground)"

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
            for lesson_order, ex_data in SATZBAU_LAB_DATA.items():
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
                            type=Exercise.ExerciseType.SCRAMBLE,
                            difficulty=Exercise.Difficulty.MEDIUM,
                            order=next_order,
                            is_published=True,
                        )
                else:
                    if not dry_run:
                        ex.instruction = ex_data["instruction"]
                        ex.type = Exercise.ExerciseType.SCRAMBLE
                        ex.is_published = True
                        ex.save(update_fields=["instruction", "type", "is_published"])

                total_exercises += 1
                self.stdout.write(f"{prefix}Exercise: L{lesson_order:02d} - {ex_data['title']}")

                for q_order, q_data in enumerate(ex_data["questions"], start=1):
                    q = None
                    if ex and not dry_run:
                        q, _ = Question.objects.update_or_create(
                            exercise=ex,
                            order=q_order,
                            defaults={
                                "prompt": q_data["prompt"],
                                "explanation": q_data["explanation"],
                            },
                        )

                        for a_order, ans_text in enumerate(q_data["answers"], start=1):
                            Answer.objects.update_or_create(
                                question=q,
                                text=ans_text,
                                defaults={
                                    "is_correct": True,
                                    "order": a_order,
                                },
                            )
                    total_questions += 1

            if dry_run:
                transaction.set_rollback(True)

        status_msg = (
            f"{prefix}Finished Satzbau Lab seeding: {total_exercises} exercises, "
            f"{total_questions} questions."
        )
        self.stdout.write(self.style.SUCCESS(status_msg))
