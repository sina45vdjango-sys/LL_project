"""Seed authentic Goethe A1 Schreiben Lab exercises (Forms and Guided Email Composition).

Phase 8 of the pedagogical roadmap:
Introduces 7 curated Schreiben Lab exercises (+31 questions) across:
- Lesson 23: Amt, Bank und Formulare (3 bureaucratic form-filling exercises, 15 questions)
  1. Anmeldung bei der Meldebehörde (Bürgeramt)
  2. Eröffnung eines Girokontos (Bank)
  3. Hotel-Meldeschein (Hotel / Gästekarte)
- Lesson 21: Telefonieren, E-Mail und Post (4 stepped email composer exercises, 16 questions)
  1. E-Mail: Anmeldung zum Deutschkurs (Formal)
  2. E-Mail: Krankmeldung an den Arbeitgeber (Formal / Ausbildung)
  3. E-Mail: Terminvereinbarung beim Arzt / Amt (Formal)
  4. E-Mail: Einladung zur Geburtstagsfeier (Informell an Freunde)

All exercises use Exercise.ExerciseType.WRITING with typed TEXT answers,
multiple accepted case/whitespace-forgiving variants, and structured Persian explanations.

Idempotent and supports --dry-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, Question
from lessons.models import Lesson


FORM_LAB_L23 = [
    {
        "title": "کارگاه فرم: ثبت‌نام سکونت (Anmeldung)",
        "instruction": "متن زیر را با دقت بخوان و ۵ اطلاعات خواسته‌شده را از متن استخراج کرده و در فرم اداری وارد کن.",
        "passage": (
            "Ihre Freundin Maryam Hosseini zieht nach Frankfurt. Sie ist am 12.08.1996 in "
            "Teheran geboren und hat die iranische Staatsangehörigkeit. Ihre neue Wohnung liegt in "
            "der Schillerstraße 24, 60313 Frankfurt am Main. Sie arbeitet als Ingenieurin. "
            "Helfen Sie Frau Hosseini und tragen Sie die 5 fehlenden Angaben in das Anmeldeformular ein."
        ),
        "questions": [
            {
                "prompt": "فیلد ۱ — Familienname (نام خانوادگی متقاضی):",
                "answers": ["Hosseini"],
                "explanation": "نام خانوادگی در متن «Maryam Hosseini» ذکر شده است؛ بنابراین فیلد Familienname برابر «Hosseini» است.",
            },
            {
                "prompt": "فیلد ۲ — Vorname (نام کوچک متقاضی):",
                "answers": ["Maryam", "Mariam"],
                "explanation": "نام کوچک متقاضی در متن «Maryam» است.",
            },
            {
                "prompt": "فیلد ۳ — Geburtsdatum (تاریخ تولد به فرمت روز.ماه.سال):",
                "answers": ["12.08.1996", "12. 08. 1996", "12.8.1996"],
                "explanation": "در متن آمده است: «am 12.08.1996 in Teheran geboren». فرمت استاندارد تاریخ در آلمان 12.08.1996 است.",
            },
            {
                "prompt": "فیلد ۴ — Postleitzahl und Wohnort (کد پستی و شهر محل سکونت):",
                "answers": ["60313 Frankfurt", "60313 Frankfurt am Main", "Frankfurt", "60313"],
                "explanation": "نشانی جدید در متن: «Schillerstraße 24, 60313 Frankfurt am Main» است. کد پستی و شهر «60313 Frankfurt» است.",
            },
            {
                "prompt": "فیلد ۵ — Staatsangehörigkeit (تابعیت / ملیت به آلمانی):",
                "answers": ["iranisch", "Iran"],
                "explanation": "در متن قید شده: «hat die iranische Staatsangehörigkeit». در فرم‌های آلمانی ملیت به صورت «iranisch» درج می‌شود.",
            },
        ],
    },
    {
        "title": "کارگاه فرم: افتتاح حساب بانکی (Girokonto)",
        "instruction": "اطلاعات متقاضی را در متن زیر بخوان و فیلدهای لازم برای افتتاح حساب جاری (Girokonto) در بانک را تکمیل کن.",
        "passage": (
            "Herr David Klein möchte bei der Bank ein Girokonto eröffnen. Er ist am 03.11.1992 in "
            "Hamburg geboren und arbeitet als Arzt im Klinikum. Er wohnt in Berlin, Postleitzahl 10115, "
            "Invalidenstraße 18. Er ist ledig. Tragen Sie die 5 Angaben in das Bankformular ein."
        ),
        "questions": [
            {
                "prompt": "فیلد ۱ — Geburtsort (محل تولد):",
                "answers": ["Hamburg"],
                "explanation": "در متن آمده: «in Hamburg geboren»؛ بنابراین محل تولد (Geburtsort) شهر «Hamburg» است.",
            },
            {
                "prompt": "فیلد ۲ — Beruf (شغل متقاضی):",
                "answers": ["Arzt"],
                "explanation": "در متن ذکر شده: «arbeitet als Arzt» (به عنوان پزشک کار می‌کند). فیلد Beruf برابر «Arzt» است.",
            },
            {
                "prompt": "فیلد ۳ — Straße und Hausnummer (خیابان و پلاک محل سکونت):",
                "answers": ["Invalidenstraße 18", "Invalidenstr. 18"],
                "explanation": "نشانی محل سکونت در متن: «Invalidenstraße 18» است.",
            },
            {
                "prompt": "فیلد ۴ — Postleitzahl (کد پستی ۵ رقمی):",
                "answers": ["10115"],
                "explanation": "کد پستی ۵ رقمی ذکر شده در متن: «10115» است.",
            },
            {
                "prompt": "فیلد ۵ — Familienstand (وضعیت تأهل — مجرد به آلمانی):",
                "answers": ["ledig"],
                "explanation": "در متن آمده است: «Er ist ledig» (او مجرد است). در فرم‌های اداری برای مجرد «ledig» نوشته می‌شود.",
            },
        ],
    },
    {
        "title": "کارگاه فرم: برگهٔ پذیرش هتل (Hotel-Meldeschein)",
        "instruction": "متن رزرو زیر را بخوان و برگهٔ پذیرش و اقامت در هتل (Meldeschein) را تکمیل کن.",
        "passage": (
            "Frau Sarah Weber reist mit ihrem Ehemann nach Köln. Sie haben im Hotel Central reserviert. "
            "Anreise ist am 14.05. und Abreise am 17.05. Sie buchen ein Doppelzimmer für 2 Personen mit "
            "Frühstück. Frau Weber bezahlt mit Kreditkarte. Tragen Sie die 5 Angaben in den Meldeschein ein."
        ),
        "questions": [
            {
                "prompt": "فیلد ۱ — Anreisedatum (تاریخ ورود به هتل):",
                "answers": ["14.05.", "14.05", "14. Mai"],
                "explanation": "در متن صریحاً آمده: «Anreise ist am 14.05.».",
            },
            {
                "prompt": "فیلد ۲ — Abreisedatum (تاریخ خروج از هتل):",
                "answers": ["17.05.", "17.05", "17. Mai"],
                "explanation": "در متن آمده: «Abreise am 17.05.».",
            },
            {
                "prompt": "فیلد ۳ — Anzahl der Personen (تعداد نفرات اقامت‌کننده):",
                "answers": ["2", "2 Personen", "zwei"],
                "explanation": "متن می‌گوید: «für 2 Personen» (برای ۲ نفر؛ خانم وبر و همسرش).",
            },
            {
                "prompt": "فیلد ۴ — Zimmerart (نوع اتاق رزرو شده):",
                "answers": ["Doppelzimmer"],
                "explanation": "در متن آمده: «buchen ein Doppelzimmer» (اتاق دونفره).",
            },
            {
                "prompt": "فیلد ۵ — Zahlungsart (روش پرداخت هزینهٔ هتل):",
                "answers": ["Kreditkarte", "mit Kreditkarte"],
                "explanation": "روش پرداخت در متن: «bezahlt mit Kreditkarte» (با کارت اعتباری) است.",
            },
        ],
    },
]

EMAIL_LAB_L21 = [
    {
        "title": "کارگاه نگارش: ایمیل رسمی به آموزشگاه زبان",
        "instruction": "می‌خواهی در یک دورهٔ زبان آلمانی ثبت‌نام کنی. این ایمیل رسمی ۴ مرحله‌ای را به خانم میلر (Frau Müller) بنویس.",
        "questions": [
            {
                "prompt": "گام ۱ — Anrede: به خانم میلر (Frau Müller) یک عنوان احترام‌آمیز رسمی بنویس:",
                "answers": [
                    "Sehr geehrte Frau Müller,",
                    "Sehr geehrte Frau Müller",
                    "Guten Tag Frau Müller,",
                    "Guten Tag Frau Müller",
                ],
                "explanation": "در مکاتبات رسمی آلمانی برای خانم‌ها از عبارت احترام‌آمیز «Sehr geehrte Frau ...» همراه با کاما استفاده می‌شود.",
            },
            {
                "prompt": "گام ۲ — Grund: بنویس که می‌خواهی در دورهٔ زبان آلمانی ثبت‌نام کنی (Ich möchte mich für den Deutschkurs anmelden):",
                "answers": [
                    "Ich möchte mich für den Deutschkurs anmelden.",
                    "Ich möchte mich für den Deutschkurs A1 anmelden.",
                    "Ich möchte einen Deutschkurs besuchen.",
                ],
                "explanation": "برای اعلام قصد ثبت‌نام رسمی: «Ich möchte mich für den Deutschkurs anmelden.» ساختار استاندارد و روان است.",
            },
            {
                "prompt": "گام ۳ — Frage: بپرس این دوره چه زمانی شروع می‌شود؟ (Wann beginnt der Kurs?):",
                "answers": [
                    "Wann beginnt der Kurs?",
                    "Wann fängt der Kurs an?",
                ],
                "explanation": "برای پرسیدن تاریخ شروع: «Wann beginnt der Kurs?» یا با فعل جداشدنی «Wann fängt der Kurs an?» به کار می‌رود.",
            },
            {
                "prompt": "گام ۴ — Grußformel: پایان‌بندی و امضای رسمی بنویس (با احترام):",
                "answers": [
                    "Mit freundlichen Grüßen",
                    "Mit freundlichen Grüßen,",
                ],
                "explanation": "در آلمان پایان‌بندی رسمی استاندارد بدون رقیب «Mit freundlichen Grüßen» است (در آلمانی بعد از این عبارت کاما گذاشته نمی‌شود).",
            },
        ],
    },
    {
        "title": "کارگاه نگارش: اعلام بیماری به محل کار / کارفرما",
        "instruction": "بیمار شده‌ای و نمی‌توانی سر کار یا Ausbildung بروی. به سرپرست خود، آقای اشمیت (Herr Schmidt)، ایمیل بزن.",
        "questions": [
            {
                "prompt": "گام ۱ — Anrede: عنوان رسمی اداری به آقای اشمیت (Herr Schmidt) بنویس:",
                "answers": [
                    "Sehr geehrter Herr Schmidt,",
                    "Sehr geehrter Herr Schmidt",
                    "Guten Tag Herr Schmidt,",
                    "Guten Tag Herr Schmidt",
                ],
                "explanation": "برای آقایان در فرم رسمی از «Sehr geehrter Herr ...» (با پسوند -er) استفاده می‌شود.",
            },
            {
                "prompt": "گام ۲ — Grund: بنویس من امروز بیمار هستم و نمی‌توانم بیایم:",
                "answers": [
                    "Ich bin heute krank und kann nicht kommen.",
                    "Ich bin krank und kann heute nicht kommen.",
                    "Ich bin heute krank.",
                    "Ich bin krank.",
                ],
                "explanation": "جملهٔ شفاف و صریح اداری: «Ich bin heute krank und kann nicht kommen.»",
            },
            {
                "prompt": "گام ۳ — Information: بنویس امروز پیش پزشک می‌روم (gehen zum Arzt):",
                "answers": [
                    "Ich gehe heute zum Arzt.",
                    "Ich gehe zum Arzt.",
                ],
                "explanation": "برای اعلام ویزیت پزشک: «Ich gehe heute zum Arzt.» در آلمان برای غیبت اداری دریافت گواهی پزشک الزامی است.",
            },
            {
                "prompt": "گام ۴ — Grußformel: پایان‌بندی رسمی اداری بنویس:",
                "answers": [
                    "Mit freundlichen Grüßen",
                    "Mit freundlichen Grüßen,",
                ],
                "explanation": "پایان‌بندی رسمی اداری: «Mit freundlichen Grüßen».",
            },
        ],
    },
    {
        "title": "کارگاه نگارش: هماهنگی وقت ملاقات اداری / مطب",
        "instruction": "می‌خواهی برای هفته آینده یک وقت ملاقات (Termin) رزرو کنی. مراحل نگارش ایمیل را تکمیل کن.",
        "questions": [
            {
                "prompt": "گام ۱ — Anrede: وقتی نام مخاطب را در اداره یا کلینیک نمی‌دانی، عنوان رسمی چیست؟ (خانم‌ها و آقایان گرامی):",
                "answers": [
                    "Sehr geehrte Damen und Herren,",
                    "Sehr geehrte Damen und Herren",
                ],
                "explanation": "عنوان رسمی استاندارد در آلمان هنگامی که نام دقیق مخاطب مشخص نیست: «Sehr geehrte Damen und Herren,».",
            },
            {
                "prompt": "گام ۲ — Bitte: بنویس من نیاز به یک وقت ملاقات دارم (Ich brauche einen Termin):",
                "answers": [
                    "Ich brauche einen Termin.",
                    "Ich brauche bitte einen Termin.",
                    "Ich möchte einen Termin vereinbaren.",
                ],
                "explanation": "درخواست صریح و واضح در سطح A1: «Ich brauche einen Termin.» یا «Ich möchte einen Termin vereinbaren.»",
            },
            {
                "prompt": "گام ۳ — Zeit: بپرس آیا روز سه‌شنبه وقت دارید؟ (Haben Sie am Dienstag Zeit?):",
                "answers": [
                    "Haben Sie am Dienstag Zeit?",
                    "Haben Sie am Dienstag einen Termin?",
                ],
                "explanation": "برای پیشنهاد روز مشخص در آلمانی: «Haben Sie am Dienstag Zeit?».",
            },
            {
                "prompt": "گام ۴ — Gruß: تشکر کن و پایان‌بندی رسمی بنویس:",
                "answers": [
                    "Vielen Dank und mit freundlichen Grüßen",
                    "Mit freundlichen Grüßen",
                    "Vielen Dank. Mit freundlichen Grüßen",
                ],
                "explanation": "پایان‌بندی همراه با سپاسگزاری: «Vielen Dank und mit freundlichen Grüßen» یا «Mit freundlichen Grüßen».",
            },
        ],
    },
    {
        "title": "کارگاه نگارش: پیام و ایمیل دوستانه به یک دوست",
        "instruction": "دوستت لوکاس (Lukas) را به جشن تولدت در روز جمعه دعوت می‌کنی. این پیام دوستانه را بنویس.",
        "questions": [
            {
                "prompt": "گام ۱ — Anrede: عنوان غیررسمی و صمیمانه به لوکاس بنویس (Lieber ...):",
                "answers": [
                    "Lieber Lukas,",
                    "Lieber Lukas",
                    "Hallo Lukas,",
                    "Hallo Lukas",
                ],
                "explanation": "در نامه‌ها و پیام‌های غیررسمی برای آقایان از «Lieber [نام],» و برای خانم‌ها از «Liebe [نام],» استفاده می‌شود.",
            },
            {
                "prompt": "گام ۲ — Einladung: بنویس روز جمعه یک جشن دارم (Ich mache am Freitag eine Party):",
                "answers": [
                    "Ich mache am Freitag eine Party.",
                    "Ich habe am Freitag eine Party.",
                    "Ich habe am Freitag Geburtstag.",
                ],
                "explanation": "بیان طبیعی و صمیمانه: «Ich mache am Freitag eine Party.» یا «Ich habe am Freitag Geburtstag.».",
            },
            {
                "prompt": "گام ۳ — Frage: بپرس آیا می‌توانی بیایی؟ (Kannst du kommen?):",
                "answers": [
                    "Kannst du kommen?",
                    "Kommst du?",
                ],
                "explanation": "پرسش دوستانه با صیغه du: «Kannst du kommen?».",
            },
            {
                "prompt": "گام ۴ — Grußformel: پایان‌بندی دوستانه و صمیمانه بنویس (Viele Grüße):",
                "answers": [
                    "Viele Grüße",
                    "Viele Grüße,",
                    "Herzliche Grüße",
                    "Liebe Grüße",
                ],
                "explanation": "در پایان پیام‌های دوستانه از «Viele Grüße» یا «Liebe Grüße» استفاده می‌شود (هرگز عبارت رسمی Mit freundlichen Grüßen به کار نمی‌رود).",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed authentic Goethe A1 Schreiben Lab exercises (Forms and Guided Email Composition)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be seeded without modifying the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        prefix = "[DRY-RUN] " if dry_run else ""

        lesson21 = Lesson.objects.filter(order=21).first()
        lesson23 = Lesson.objects.filter(order=23).first()

        if not lesson21 or not lesson23:
            self.stdout.write(
                self.style.WARNING(
                    f"{prefix}Lessons 21 and/or 23 not found. Skipping seeding."
                )
            )
            return

        total_exercises = 0
        total_questions = 0

        with transaction.atomic():
            # 1. Seed L23 Bureaucratic Form-Filling Exercises
            for ex_data in FORM_LAB_L23:
                ex = Exercise.objects.filter(lesson=lesson23, title=ex_data["title"]).first()
                if not ex:
                    next_order = (
                        Exercise.objects.filter(lesson=lesson23).aggregate(Max("order"))["order__max"]
                        or 0
                    ) + 1
                    passage = ex_data.get("passage", "")
                    combined_instruction = ex_data["instruction"]
                    if passage:
                        combined_instruction = f"{ex_data['instruction']}\n\n«{passage}»"

                    if not dry_run:
                        ex = Exercise.objects.create(
                            lesson=lesson23,
                            title=ex_data["title"],
                            instruction=combined_instruction,
                            type=Exercise.ExerciseType.WRITING,
                            difficulty=Exercise.Difficulty.MEDIUM,
                            order=next_order,
                            is_published=True,
                        )
                else:
                    passage = ex_data.get("passage", "")
                    combined_instruction = ex_data["instruction"]
                    if passage:
                        combined_instruction = f"{ex_data['instruction']}\n\n«{passage}»"

                    if not dry_run:
                        ex.instruction = combined_instruction
                        ex.type = Exercise.ExerciseType.WRITING
                        ex.is_published = True
                        ex.save()

                total_exercises += 1

                for idx, q_data in enumerate(ex_data["questions"], start=1):
                    full_prompt = q_data["prompt"]

                    if not dry_run:
                        q, _ = Question.objects.get_or_create(
                            exercise=ex,
                            order=idx,
                            defaults={
                                "prompt": full_prompt,
                                "explanation": q_data["explanation"],
                            },
                        )
                        q.prompt = full_prompt
                        q.explanation = q_data["explanation"]
                        q.save()

                        # Clear and seed accepted answers
                        q.answers.all().delete()
                        for a_idx, ans_text in enumerate(q_data["answers"], start=1):
                            Answer.objects.create(
                                question=q,
                                text=ans_text,
                                is_correct=True,
                                order=a_idx,
                            )

                    total_questions += 1

            # 2. Seed L21 Stepped Email Composition Exercises
            for ex_data in EMAIL_LAB_L21:
                ex = Exercise.objects.filter(lesson=lesson21, title=ex_data["title"]).first()
                if not ex:
                    next_order = (
                        Exercise.objects.filter(lesson=lesson21).aggregate(Max("order"))["order__max"]
                        or 0
                    ) + 1
                    if not dry_run:
                        ex = Exercise.objects.create(
                            lesson=lesson21,
                            title=ex_data["title"],
                            instruction=ex_data["instruction"],
                            type=Exercise.ExerciseType.WRITING,
                            difficulty=Exercise.Difficulty.MEDIUM,
                            order=next_order,
                            is_published=True,
                        )
                else:
                    if not dry_run:
                        ex.instruction = ex_data["instruction"]
                        ex.type = Exercise.ExerciseType.WRITING
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

                        # Clear and seed accepted answers
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
                f"{prefix}Successfully processed {total_exercises} Schreiben Lab exercises "
                f"with {total_questions} questions across Lessons 21 and 23."
            )
        )
