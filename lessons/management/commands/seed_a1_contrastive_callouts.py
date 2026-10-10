"""Seed contrastive pedagogy callouts and real-world German / Ausbildung tips.

Phase 10 of the pedagogical roadmap:
Introduces 10 curated contrastive callout blocks across foundational A1 lessons:
- Lesson 01: Begrüßung & Vorstellung (Falle: Willkommen vs Bitte / Ausbildung: du vs Sie & Blickkontakt)
- Lesson 02: Länder, Sprachen & Herkunft (Falle: der Iran & die Schweiz / Ausbildung: Staatsangehörigkeit vs Wohnort)
- Lesson 03: Zahlen, Alphabet & Alter (Falle: haben vs sein bei Alter / Ausbildung: Buchstabieralphabet am Telefon)
- Lesson 04: Familie & Personen (Falle: mein vs meine & Geschwister / Ausbildung: Notfallkontakt & Familienstand)
- Lesson 05: Beruf & Arbeit (Falle: Nullartikel bei Berufen / Ausbildung: Azubi vs Fachkraft im Tarifvertrag)

Additive, idempotent, and supports --dry-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from lessons.models import Lesson, LessonContent


CALLOUT_DATA = {
    1: [
        {
            "title": "⚠️ تلهٔ فارسی‌زبانان: پاسخ به تشکر (Willkommen یا Bitte؟)",
            "body": (
                "❌ اشتباه رایج فارسی‌زبانان:\n"
                "در فارسی وقتی کسی تشکر می‌کند، گاهی می‌گوییم «خواهش می‌کنم / خوش آمدید». زبان‌آموزان به اشتباه در پاسخ به Danke می‌گویند: «Willkommen!»\n"
                "در آلمانی عبارت Willkommen فقط برای خوش‌آمدگویی فیزیکی به یک مکان (Welcome) به کار می‌رود!\n\n"
                "✅ ساختار اصیل آلمانی:\n"
                "در پاسخ به تشکر (Danke / Vielen Dank)، منحصراً از یکی از این عبارت‌ها استفاده کنید:\n"
                "• Bitte! (خواهش می‌کنم - عمومی و پرکاربرد)\n"
                "• Bitte schön! / Bitte sehr! (بفرمایید / خواهش می‌کنم)\n"
                "• Gern geschehen! (با کمال میل - بسیار محترمانه و رایج)\n"
                "• Kein Problem! (مسئله‌ای نیست - دوستانه)\n\n"
                "💡 نکتهٔ ذهن آلمانی:\n"
                "کلمهٔ Willkommen به تنهایی پاسخِ تشکر نیست. اگر می‌خواهید بگویید «قدمت روی چشم»، همان «Gern geschehen!» دقیق‌ترین معادل احساسی است."
            ),
        },
        {
            "title": "🇩🇪 نکتهٔ کارآموزی و زندگی: مرز حساس du و Sie در محیط کار",
            "body": (
                "🏢 در محیط کار، شرکت و دورهٔ آوسبیلدونگ:\n"
                "در آلمان تفکیک بین ضمیر خودمانی (du) و رسمی (Sie) یک مرز حرفه‌ای بسیار جدی است، نه فقط یک تفاوت گرامری ساده.\n"
                "در روز اول کارآموزی یا کار جدید:\n"
                "• با مدیران، مربیان کارآموزی (Ausbilder) و تمام همکاران فقط و فقط از «Sie» استفاده کنید.\n"
                "• هرگز شما پیش‌قدم نشوید برای گفتن «du»!\n"
                "• این قاعده یک‌طرفه است: پیشنهاد تغییر به «du» همیشه از طرف فرد باسابقه، مسن‌تر یا دارای رتبه بالاتر داده می‌شود («Wir können uns duzen»).\n\n"
                "📌 ترفند موفقیت در آلمان:\n"
                "هنگام احوال‌پرسی و دست دادن در آلمان، ارتباط چشمی مستقیم (Blickkontakt) بسیار حیاتی است. نگاه نکردن به چشم طرف مقابل در فرهنگ کاری آلمان حمل بر عدم صداقت یا ضعف اعتمادبه‌نفس می‌شود."
            ),
        },
    ],
    2: [
        {
            "title": "⚠️ تلهٔ فارسی‌زبانان: کشورهای دارای حرف تعریف (der Iran، die Schweiz)",
            "body": (
                "❌ اشتباه رایج فارسی‌زبانان:\n"
                "در فارسی اسم تمام کشورها یکسان به کار می‌رود: «من اهل ایرانم»، «من اهل آلمانم».\n"
                "به همین دلیل زبان‌آموزان به اشتباه می‌گویند:\n"
                "«❌ Ich komme aus Iran.» یا «❌ Ich wohne in Schweiz.»\n\n"
                "✅ ساختار اصیل آلمانی:\n"
                "اکثر کشورها در آلمانی بدون آرتیکل هستند (aus Deutschland, in Spanien). اما چند کشور مهم حتماً آرتیکل دارند و بعد از حروف اضافهٔ aus و in به حالت داتیو (Dativ) می‌روند:\n"
                "• der Iran ➔ Ich komme aus dem Iran. / Ich lebe im Iran.\n"
                "• die Schweiz ➔ Ich komme aus der Schweiz. / Ich lebe in der Schweiz.\n"
                "• die Türkei ➔ Ich komme aus der Türkei. / Ich lebe in der Türkei.\n"
                "• die USA (جمع) ➔ Ich komme aus den USA. / Ich lebe in den USA.\n\n"
                "💡 قاعدهٔ طلایی:\n"
                "هر زمان نام کشورتان (ایران) را به زبان می‌آورید، ترکیب ثابت «aus dem Iran» را مثل یک کلمهٔ یکپارچه در ذهن بسپارید."
            ),
        },
        {
            "title": "🇩🇪 نکتهٔ کارآموزی و زندگی: تفاوت تابعیت و محل سکونت در فرم‌ها",
            "body": (
                "🏢 در ادارات دولتی (Bürgeramt) و مصاحبه‌های استخدامی:\n"
                "در آلمان میان سه مفهوم تفاوت حقوقی و ثبت رسمی دقیقی وجود دارد:\n"
                "۱. Geburtsort: محل تولد (مثلاً Teheran)\n"
                "۲. Staatsangehörigkeit: تابعیت / ملیت (مثلاً iranisch)\n"
                "۳. Wohnort: شهر محل سکونت فعلی شما در آلمان (مثلاً Berlin / Frankfurt)\n\n"
                "📌 نکتهٔ مصاحبه و کارآموزی:\n"
                "اگر در گفت‌وگو یا مصاحبه از شما پرسیدند «Woher kommen Sie؟»، بهترین و حرفه‌ای‌ترین پاسخ دو بخشی است:\n"
                "«Ich komme aus dem Iran, aber ich wohne jetzt in Frankfurt.»\n"
                "این پاسخ نشان می‌دهد که شما در آلمان مستقر و متمرکز بر زندگی و کار جدید خود هستید."
            ),
        },
    ],
    3: [
        {
            "title": "⚠️ تلهٔ فارسی‌زبانان: بیان سن با haben یا sein؟",
            "body": (
                "❌ اشتباه رایج فارسی‌زبانان:\n"
                "در فارسی سن را «داشتن» می‌دانیم: «من ۲۴ سال سن دارم».\n"
                "به همین دلیل ترجمهٔ مستقیم ذهنی منجر به این اشتباه بزرگ می‌شود:\n"
                "«❌ Ich habe 24 Jahre alt.»\n\n"
                "✅ ساختار اصیل آلمانی:\n"
                "سن در تفکر زبان آلمانی یک «کیفیت وجودی» و حالت است، نه یک دارایی فیزیکی! بنابراین منحصراً با فعل sein بیان می‌شود:\n"
                "• Ich bin 24 Jahre alt.\n"
                "• یا به صورت خودمانی‌تر و روزمره: Ich bin 24.\n"
                "• سؤال: Wie alt bist du? / Wie alt sind Sie? (چقدر پیر/سالمند هستید؟)\n\n"
                "💡 خطای تلفظی اعداد دورقمی:\n"
                "در آلمانی ترتیب خواندن اعداد برعکس فارسی است: ابتدا یکان و سپس دهگان!\n"
                "۲۱ = einundzwanzig (یک و بیست)\n"
                "۳۵ = fünfunddreißig (پنج و سی)"
            ),
        },
        {
            "title": "🇩🇪 نکتهٔ کارآموزی و زندگی: الفبای هجی تلفنی (Buchstabieralphabet)",
            "body": (
                "🏢 در مکالمات تلفنی با ادارات، بانک‌ها و کارفرمایان:\n"
                "وقتی نام، نام خانوادگی، یا ایمیل غیرآلمانی خود را پشت تلفن می‌گویید، طرف مقابل بلافاصله می‌گوید: «Können Sie das bitte buchstabieren؟»\n"
                "در آلمان برای جلوگیری از اشتباه حروف شبیه هم (مانند B و P، یا D و T)، از الفبای استاندارد نام‌ها استفاده می‌شود:\n"
                "• A wie Anton\n"
                "• B wie Berta\n"
                "• D wie Dora\n"
                "• M wie Martha\n"
                "• S wie Samuel\n\n"
                "📌 خواندن شماره حساب و تلفن:\n"
                "شماره‌های اداری، شماره تلفن و شماره‌های بانکی (IBAN) در آلمان معمولاً رقم به رقم یا دو رقم به دو رقم خوانده می‌شوند، نه به شکل اعداد بزرگ چند صدتایی!"
            ),
        },
    ],
    4: [
        {
            "title": "⚠️ تلهٔ فارسی‌زبانان: جنسیت صفت ملکی (mein یا meine؟)",
            "body": (
                "❌ اشتباه رایج فارسی‌زبانان:\n"
                "در فارسی ضمیر ملکی «ـَم» برای مذکر و مؤنث کاملاً یکسان است: «پدرم»، «مادرم»، «کتابم».\n"
                "زبان‌آموزان اغلب فکر می‌کنند جنسیت ضمیر باید با جنسیت خودِ گوینده هماهنگ باشد!\n\n"
                "✅ ساختار اصیل آلمانی:\n"
                "جنسیت صفت ملکی در آلمانی منحصراً تابع «اسمی که بعد از آن می‌آید» است، نه جنسیت فرد گوینده:\n"
                "• اسم مذکر یا خنثی: mein Vater (پدرم) / mein Kind (فرزندم)\n"
                "• اسم مؤنث یا جمع: meine Mutter (مادرم) / meine Eltern (والدینم)\n"
                "بنابراین یک آقا هم می‌گوید «meine Schwester» و یک خانم هم می‌گوید «mein Bruder».\n\n"
                "💡 اصطلاح جمع Geschwister:\n"
                "در آلمانی برای گفتن «خواهر و برادر»، ترکیب Brüder und Schwestern به کار نمی‌رود، بلکه از واژهٔ جمع یکپارچه استفاده می‌شود:\n"
                "Ich habe zwei Geschwister. (من دو تا خواهر/برادر دارم.)"
            ),
        },
        {
            "title": "🇩🇪 نکتهٔ کارآموزی و زندگی: مشخصات خانوادگی و تماس اضطراری در قراردادها",
            "body": (
                "🏢 در فرم‌های استخدام، آوسبیلدونگ و ثبت‌نام مهدکودک/مدرسه:\n"
                "در آلمان گزینه‌های وضعیت تأهل (Familienstand) تنوع دقیق حقوقی دارند:\n"
                "• ledig (مجرد)\n"
                "• verheiratet (متأهل)\n"
                "• geschieden (مطلقه)\n"
                "• verwitwet (همسر فوت‌شده)\n\n"
                "📌 ثبت Notfallkontakt (تماس اضطراری):\n"
                "در تمامی محیط‌های کاری آلمان موظفید یک شماره تماس اضطراری از یکی از نزدیکان معرفی کنید.\n"
                "اما نکتهٔ فرهنگی مهم: در فرهنگ محیط کار آلمان، ورود به حریم خصوصی دیگران (پرسیدن از جزئیات ازدواج، حقوق همسر، یا مسائل خانوادگی) یک خط قرمز اخلاقی است. درباره زندگی شخصی فقط زمانی صحبت می‌شود که خود فرد تمایل نشان دهد."
            ),
        },
    ],
    5: [
        {
            "title": "⚠️ تلهٔ فارسی‌زبانان: حذف آرتیکل نکره هنگام بیان شغل",
            "body": (
                "❌ اشتباه رایج فارسی‌زبانان:\n"
                "در فارسی می‌گوییم: «من یک مهندس هستم» یا «او یک پزشک است».\n"
                "به همین دلیل ذهن فارسی‌زبان تمایل دارد کلمهٔ «یک» (ein / eine) را ترجمه کند:\n"
                "«❌ Ich bin ein Ingenieur.»\n\n"
                "✅ ساختار اصیل آلمانی:\n"
                "در زبان آلمانی هنگام بیان شغل با فعل‌های sein و werden، آرتیکل نکره حتماً حذف می‌شود:\n"
                "• Ich bin Ingenieur. (من مهندسم - مذکر)\n"
                "• Ich bin Lehrerin. (من معلمم - مؤنث)\n"
                "• Er arbeitet als Arzt. (او به عنوان پزشک کار می‌کند.)\n\n"
                "💡 استثنای وجود صفت:\n"
                "آرتیکل فقط و فقط زمانی بازمی‌گردد که قبل از نام شغل یک صفت توصیفی بیاید:\n"
                "«Er ist ein guter Arzt.» (او یک پزشک خوب است.)"
            ),
        },
        {
            "title": "🇩🇪 نکتهٔ کارآموزی و زندگی: واژه‌شناسی رسمی کارآموزی (Azubi در برابر Fachkraft)",
            "body": (
                "🏢 اصطلاحات رسمی بازار کار و دورهٔ آوسبیلدونگ در آلمان:\n"
                "در آلمان عنوان شغلی بار حقوقی و قانونی مستقیم دارد و در قرارداد کاری ثبت می‌شود:\n"
                "• Auszubildende / Auszubildender (مخفف: Azubi): عنوان رسمی کارآموز. شما در محیط کار کارگر ساده نیستید، بلکه کارآموز قانونی هستید.\n"
                "• Fachkraft: نیروی کار متخصص که دورهٔ ۳ ساله آوسبیلدونگ را با موفقیت تمام کرده و مدرک رسمی اتاق بازرگانی (IHK یا HWK) دارد.\n"
                "• Hilfskraft: نیروی کمکی یا کارگر بدون مدرک رسمی.\n\n"
                "📌 اهمیت قرارداد صنفی (Tarifvertrag):\n"
                "در آلمان تفاوت بین Azubi و Fachkraft حداقل حقوق مصوب شما را در جدول‌های قرارداد جمعی صنفی تعیین می‌کند. به عنوان یک Azubi، کارفرما موظف است زمان مشخصی را صرف آموزش تئوری و عملی شما کند نه اینکه فقط کارهای متفرقه به شما بسپارد!"
            ),
        },
    ],
}


class Command(BaseCommand):
    help = "Seed contrastive pedagogy callouts and real-world German / Ausbildung tips into L01–L05"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate injection without writing changes to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        created_count = 0
        updated_count = 0
        reused_count = 0

        with transaction.atomic():
            for lesson_order, blocks in sorted(CALLOUT_DATA.items()):
                lesson = Lesson.objects.filter(order=lesson_order).first()
                if not lesson:
                    self.stdout.write(self.style.WARNING(f"Lesson {lesson_order} not found, skipping."))
                    continue

                max_order = (
                    LessonContent.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"] or 0
                )

                for block_data in blocks:
                    title = block_data["title"]
                    body = block_data["body"]

                    existing = LessonContent.objects.filter(lesson=lesson, title=title).first()

                    if existing:
                        if existing.body != body or existing.type != LessonContent.ContentType.NOTE:
                            if not dry_run:
                                existing.body = body
                                existing.type = LessonContent.ContentType.NOTE
                                existing.save(update_fields=["body", "type"])
                            updated_count += 1
                            self.stdout.write(f"Updated callout: L{lesson_order:02d} - {title[:40]}...")
                        else:
                            reused_count += 1
                    else:
                        max_order += 1
                        next_order = max_order

                        if not dry_run:
                            LessonContent.objects.create(
                                lesson=lesson,
                                order=next_order,
                                type=LessonContent.ContentType.NOTE,
                                title=title,
                                body=body,
                            )
                        created_count += 1
                        self.stdout.write(f"Created callout: L{lesson_order:02d} [#{next_order}] - {title[:40]}...")

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY RUN] Would create {created_count}, update {updated_count}, reuse {reused_count} blocks."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully seeded contrastive callouts: {created_count} created, {updated_count} updated, {reused_count} reused."
                    )
                )
