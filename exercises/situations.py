"""Situational roleplay scenarios for German everyday and Ausbildung life.

These scenarios enrich standard dialogue practice into branch-aware interactive roleplays
(Situationsdialoge) across 5 core real-world domains:
  1. L05: Arbeitsplatz & Betriebskantine (Siemens-Ausbildung, Mahlzeit-Kultur, Siezen)
  2. L09: Bäckerei & Frischemarkt (Brötchen kaufen, Höflichkeitsformeln, Bar/Kartenzahlung)
  3. L15: Arztpraxis & Terminvereinbarung (Akute Schmerzen, Versichertenkarte, Wartezimmer)
  4. L18: Apotheke & Beratung (Hustensaft, pflanzliche Mittel, Dosierung, Gute Besserung)
  5. L23: Bürgeramt & Meldebehörde (Wohnsitzanmeldung, Wohnungsgeberbestätigung)

Pure Python, additive, zero database schema changes.
"""

SITUATIONAL_SCENARIOS = {
    5: {
        "scenario_id": "arbeitsplatz_kantine",
        "title": "اولین روز کارآموزی و ناهار در غذاخوری شرکت (Arbeitsplatz & Kantine)",
        "setting": "Betriebskantine der Firma, Stuttgart",
        "role_you": "Neuer Azubi (کارآموز جدید)",
        "role_partner": "Herr Krause (Ausbilder / سرپرست کارآموزی)",
        "partner_avatar": "K",
        "objective": "پیوستن به میز ناهار همکاران، احوالپرسی محترمانه در محیط کار، و رعایت قواعد Siezen در محیط Ausbildung.",
        "etiquette_tip": "🇩🇪 فرهنگ کارآموزی (Ausbildung): در محیط کار آلمانی، حتماً با مدیران و همکاران بزرگ‌تر از ضمیر رسمی «Sie» استفاده کنید مگر اینکه صریحاً به شما «Du» پیشنهاد دهند. هنگام ورود به غذاخوری در وقت ناهار، گفتن «Mahlzeit!» یا «Guten Appetit!» یک رسم اداری پسندیده است.",
        "turns": [
            {
                "speaker": "Herr Krause",
                "mine": False,
                "text": "Hallo! Willkommen im Team. Wie gefällt Ihnen der erste Tag?",
                "translation": "سلام! به تیم خوش آمدید. روز اول چطور می‌گذرد؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "تشکر محترمانه و ابراز رضایت از کارآموزی:",
                "text": "Vielen Dank, Herr Krause! Es ist sehr interessant und alle sind sehr nett.",
                "translation": "خیلی ممنون، آقای کراوزه! بسیار جالب است و همه خیلی مهربانند.",
                "audio": "",
                "branches": [
                    {
                        "text": "Vielen Dank, Herr Krause! Es ist sehr interessant und alle sind sehr nett.",
                        "is_recommended": True,
                        "etiquette_note": "بسیار محترمانه: صدا زدن سرپرست با نام خانوادگی (Herr Krause) و لحن مثبت، تأثیر اولیهٔ حرفه‌ای می‌گذارد.",
                    },
                    {
                        "text": "Danke dir! Die Arbeit ist gut.",
                        "is_recommended": False,
                        "etiquette_note": "خطای اتیکت کاری: استفاده از ضمیر غیررسمی «dir» برای سرپرست اشتباه است؛ در آلمان تا زمان پیشنهاد سرپرست حتماً «Sie / Ihnen» بگویید.",
                    },
                ],
            },
            {
                "speaker": "Herr Krause",
                "mine": False,
                "text": "Setzen Sie sich gern zu uns. Guten Appetit!",
                "translation": "بفرمایید پیش ما بنشینید. نوش جان!",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "پاسخ به تعارف نشستن و گفتن نوش جان کاری:",
                "text": "Danke schön, Mahlzeit! Ist dieser Platz noch frei?",
                "translation": "خیلی ممنون، نوش جان! این صندلی هنوز خالی است؟",
                "audio": "",
                "branches": [
                    {
                        "text": "Danke schön, Mahlzeit! Ist dieser Platz noch frei?",
                        "is_recommended": True,
                        "etiquette_note": "اصطلاح طلایی: کلمهٔ «Mahlzeit!» کلید اداری ورود به وقت ناهار در شرکت‌های آلمانی است.",
                    },
                    {
                        "text": "Ja, ich habe großen Hunger.",
                        "is_recommended": False,
                        "etiquette_note": "خیلی عامیانه است. قبل از نشستن در جمع اداری حتماً بپرسید: «Ist hier noch frei?» و «Guten Appetit» بگویید.",
                    },
                ],
            },
            {
                "speaker": "Herr Krause",
                "mine": False,
                "text": "Ja, natürlich. Was haben Sie vor der Ausbildung gemacht?",
                "translation": "بله حتماً. قبل از کارآموزی چه کار می‌کردید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "توضیح کوتاه درباره یادگیری آلمانی و آمدن به کارآموزی:",
                "text": "Ich habe intensiv Deutsch gelernt und mich auf die Ausbildung vorbereitet.",
                "translation": "من فشرده آلمانی خواندم و خودم را برای کارآموزی آماده کردم.",
                "audio": "",
                "branches": [
                    {
                        "text": "Ich habe intensiv Deutsch gelernt und mich auf die Ausbildung vorbereitet.",
                        "is_recommended": True,
                        "etiquette_note": "پاسخی سنجیده و متعهدانه که انگیزه و پشتکار شما را در کار نشان می‌دهد.",
                    },
                    {
                        "text": "Ich war zu Hause und habe nichts gemacht.",
                        "is_recommended": False,
                        "etiquette_note": "این لحن بی‌پروایانه انگیزهٔ کاری را زیر سؤال می‌برد؛ همیشه بر یادگیری زبان و آمادگی تمرکز کنید.",
                    },
                ],
            },
        ],
    },
    9: {
        "scenario_id": "supermarkt_baeckerei",
        "title": "خرید در نانوایی و بازار میوه (Bäckerei & Markt)",
        "setting": "Bäckerei & Frischemarkt, Berlin",
        "role_you": "Kunde (مشتری)",
        "role_partner": "Frau Müller (فروشنده)",
        "partner_avatar": "M",
        "objective": "خرید سیب‌زمینی، گوجه و نان، سفارش میوه با لحن محترمانه، و پرداخت حساب.",
        "etiquette_tip": "🇩🇪 آداب خرید در آلمان: برای سفارش، عبارت «Ich möchte bitte...» یا «Ich hätte gern...» مودبانه و طبیعی است؛ از کاربرد مستقیم «Ich will» پرهیز کنید. در پایان پرداخت نقدی، گفتن «Stimmt so» یعنی بقیه پول انعام شماست.",
        "turns": [
            {
                "speaker": "Frau Müller",
                "mine": False,
                "text": "Guten Tag! Was darf es denn sein?",
                "translation": "روز بخیر! چه میل دارید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "سفارش ۱ کیلو سیب‌زمینی و ۱ کیلو گوجه‌فرنگی با لحن مودبانه:",
                "text": "Ich möchte bitte ein Kilo Kartoffeln und ein Kilo Tomaten.",
                "translation": "یک کیلو سیب‌زمینی و یک کیلو گوجه‌فرنگی می‌خواهم لطفاً.",
                "audio": "",
                "branches": [
                    {
                        "text": "Ich möchte bitte ein Kilo Kartoffeln und ein Kilo Tomaten.",
                        "is_recommended": True,
                        "etiquette_note": "بسیار مودبانه و استاندارد: کاربرد «Ich möchte bitte» لحنی محترمانه و دقیق می‌سازد.",
                    },
                    {
                        "text": "Ich will Kartoffeln und Tomaten.",
                        "is_recommended": False,
                        "etiquette_note": "تلهٔ زبانی: فعل «Ich will» در آلمانی آمرانه به نظر می‌رسد؛ در خرید روزمره حتماً «Ich möchte» بگویید.",
                    },
                ],
            },
            {
                "speaker": "Frau Müller",
                "mine": False,
                "text": "Möchten Sie auch Obst?",
                "translation": "میوه هم میل دارید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "پاسخ مثبت: درخواست ۳ عدد موز و ۱ پرتقال با لطفاً (bitte):",
                "text": "Ja, gerne. Drei Bananen und eine Orange, bitte.",
                "translation": "بله، با کمال میل. سه عدد موز و یک پرتقال لطفاً.",
                "audio": "",
                "branches": [
                    {
                        "text": "Ja, gerne. Drei Bananen und eine Orange, bitte.",
                        "is_recommended": True,
                        "etiquette_note": "استفاده از «gerne» و «bitte» مکالمه را بسیار طبیعی و دوستانه جلوه می‌دهد.",
                    },
                    {
                        "text": "Nein, ich brauche kein Obst.",
                        "is_recommended": False,
                        "etiquette_note": "پاسخ منفی گرامری است اما در مکالمه خرید، پاسخ کوتاه با «bitte» پسندیده‌تر است.",
                    },
                ],
            },
            {
                "speaker": "Frau Müller",
                "mine": False,
                "text": "Das macht zusammen neun Euro zwanzig.",
                "translation": "جمعاً می‌شود نه یورو و بیست سنت.",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "پرداخت پول: تحویل ۱۰ یورو و گفتن بفرمایید:",
                "text": "Hier bitte, zehn Euro. Stimmt so!",
                "translation": "بفرمایید، ده یورو. بقیه‌اش برای خودتان (انعام)!",
                "audio": "",
                "branches": [
                    {
                        "text": "Hier bitte, zehn Euro. Stimmt so!",
                        "is_recommended": True,
                        "etiquette_note": "اصطلاح طلایی: «Stimmt so» روش رایج اعلام بخشیدن پول خرد (انعام) در خریدهای آلمان است.",
                    },
                    {
                        "text": "Hier ist das Geld.",
                        "is_recommended": False,
                        "etiquette_note": "از نظر گرامری درست اما خشک است؛ آلمانی‌زبان‌ها معمولاً فقط می‌گویند «Hier bitte».",
                    },
                ],
            },
        ],
    },
    15: {
        "scenario_id": "arzttermin_praxis",
        "title": "پذیرش مطب پزشکی: گرفتن نوبت اورژانسی (Arztpraxis & Termin)",
        "setting": "Hausarztpraxis Dr. Schneider, Frankfurt",
        "role_you": "Patient (بیمار)",
        "role_partner": "Frau Becker (منشی پذیرش مطب)",
        "partner_avatar": "B",
        "objective": "درخواست نوبت ویزیت فوری به دلیل سردرد شدید و تب، ارائه کارت بیمه درمانی و رفتن به اتاق انتظار.",
        "etiquette_tip": "🇩🇪 سیستم درمانی آلمان: در آلمان نمی‌توان بدون هماهنگی یا نوبت وارد مطب شد مگر در موارد اورژانسی. هنگام مراجعه، فوراً بگویید «Ich habe akute Schmerzen» تا در صورت امکان بین مراجعان به شما نوبت دهند. همراه داشتن کارت بیمه سلامت در هر بار مراجعه الزامی است.",
        "turns": [
            {
                "speaker": "Frau Becker",
                "mine": False,
                "text": "Praxis Dr. Schneider, guten Tag. Wie kann ich Ihnen helfen?",
                "translation": "مطب دکتر اشنایدر، روز بخیر. چطور می‌توانم کمکتان کنم؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "شرح مشکل و درخواست نوبت ویزیت برای امروز:",
                "text": "Guten Tag, mein Name ist Sina. Ich habe akute Schmerzen und brauche heute einen Termin.",
                "translation": "روز بخیر، نام من سینا است. درد شدید دارم و امروز به نوبت ویزیت نیاز دارم.",
                "audio": "",
                "branches": [
                    {
                        "text": "Guten Tag, mein Name ist Sina. Ich habe akute Schmerzen und brauche heute einen Termin.",
                        "is_recommended": True,
                        "etiquette_note": "عالی: معرفی نام و استفاده از اصطلاح «akute Schmerzen» کلید دریافت ویزیت بدون نوبت قبلی است.",
                    },
                    {
                        "text": "Ich will jetzt den Arzt sehen.",
                        "is_recommended": False,
                        "etiquette_note": "لحن آمرانه: در آلمان منشی‌ها نوبت‌ها را مدیریت می‌کنند و لحن دستوری شانس پذیرش را کم می‌کند.",
                    },
                ],
            },
            {
                "speaker": "Frau Becker",
                "mine": False,
                "text": "Sind Sie schon Patient bei uns und haben Sie Ihre Versichertenkarte dabei?",
                "translation": "قبلاً بیمار ما بوده‌اید و کارت بیمه همراهتان هست؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "پاسخ مثبت و ارائه کارت بیمه سلامت:",
                "text": "Ja, ich bin schon hier registriert. Hier ist meine elektronische Gesundheitskarte.",
                "translation": "بله، قبلاً اینجا پرونده دارم. این هم کارت الکترونیک بیمه سلامت من.",
                "audio": "",
                "branches": [
                    {
                        "text": "Ja, ich bin schon hier registriert. Hier ist meine elektronische Gesundheitskarte.",
                        "is_recommended": True,
                        "etiquette_note": "ارائهٔ سریع و محترمانهٔ کارت بیمه فرآیند پذیرش را بسیار آسان می‌کند.",
                    },
                    {
                        "text": "Ich weiß nicht, wo meine Karte ist.",
                        "is_recommended": False,
                        "etiquette_note": "بدون کارت بیمه پذیرش با تاخیر یا الزام به پرداخت ودیعه همراه خواهد بود.",
                    },
                ],
            },
            {
                "speaker": "Frau Becker",
                "mine": False,
                "text": "Sehr gut. Nehmen Sie bitte im Wartezimmer Platz, der Arzt ruft Sie gleich auf.",
                "translation": "بسیار خوب. لطفاً در اتاق انتظار بنشینید، دکتر به زودی صدایتان می‌کند.",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "تشکر محترمانه و رفتن به اتاق انتظار:",
                "text": "Vielen Dank für Ihre Hilfe. Einen Moment noch: Darf ich ein Glas Wasser haben?",
                "translation": "خیلی ممنون از کمکتان. ببخشید، ممکن است یک لیوان آب داشته باشم؟",
                "audio": "",
                "branches": [
                    {
                        "text": "Vielen Dank für Ihre Hilfe. Einen Moment noch: Darf ich ein Glas Wasser haben?",
                        "is_recommended": True,
                        "etiquette_note": "مودبانه و صمیمانه؛ پرسیدن برای آب با «Darf ich...» کمال ادب را نشان می‌دهد.",
                    },
                    {
                        "text": "Okay, danke.",
                        "is_recommended": False,
                        "etiquette_note": "کوتاه است اما عبارت «Vielen Dank für Ihre Hilfe» بازخورد بهتری در محیط درمانی دارد.",
                    },
                ],
            },
        ],
    },
    18: {
        "scenario_id": "apotheke_beratung",
        "title": "در داروخانه: خرید داروی سرماخوردگی و دستور مصرف (In der Apotheke)",
        "setting": "Adler-Apotheke, Köln",
        "role_you": "Kunde / Patient (مشتری)",
        "role_partner": "Herr Frank (داروساز)",
        "partner_avatar": "F",
        "objective": "شرح علائم سرفه و گلو‌درد، تهیه داروی بدون نسخه، و سوال درباره نحوه و زمان مصرف دارو.",
        "etiquette_tip": "🇩🇪 قوانین دارو در آلمان: داروها به دو دسته بدون نسخه («rezeptfrei») و با نسخه («rezeptpflichtig») تقسیم می‌شوند. داروخانه‌ها موظف به مشاوره هستند. همیشه طریقهٔ مصرف را دقیق بپرسید («Wie oft soll ich das einnehmen?») و در انتها آرزوی سلامتی («Gute Besserung!») را با تشکر پاسخ دهید.",
        "turns": [
            {
                "speaker": "Herr Frank",
                "mine": False,
                "text": "Guten Tag! Was kann ich für Sie tun?",
                "translation": "روز بخیر! چه کمکی از دست من برایتان برمی‌آید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "شرح علائم سرماخوردگی (سرفه و گلو‌درد از دو روز پیش):",
                "text": "Guten Tag! Ich habe seit zwei Tagen starken Husten und Halsschmerzen.",
                "translation": "روز بخیر! دو روز است سرفهٔ شدید و گلو‌درد دارم.",
                "audio": "",
                "branches": [
                    {
                        "text": "Guten Tag! Ich habe seit zwei Tagen starken Husten und Halsschmerzen.",
                        "is_recommended": True,
                        "etiquette_note": "ساختار «seit zwei Tagen» به همراه Präsens برای بیان بیماری ادامه‌دار شیوهٔ استاندارد آلمانی است.",
                    },
                    {
                        "text": "Geben Sie mir starke Medikamente.",
                        "is_recommended": False,
                        "etiquette_note": "درخواست داروی قوی بدون شرح علائم پذیرفته نمی‌شود؛ داروساز باید علت را بداند.",
                    },
                ],
            },
            {
                "speaker": "Herr Frank",
                "mine": False,
                "text": "Haben Sie ein Rezept vom Arzt oder möchten Sie etwas Rezeptfreies?",
                "translation": "از پزشک نسخه دارید یا داروی بدون نسخه می‌خواهید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "پاسخ: نسخه ندارم و داروی گیاهی بدون نسخه می‌خواهم:",
                "text": "Ich habe kein Rezept. Haben Sie einen pflanzlichen Hustensaft?",
                "translation": "نسخه ندارم. شربت سینهٔ گیاهی دارید؟",
                "audio": "",
                "branches": [
                    {
                        "text": "Ich habe kein Rezept. Haben Sie einen pflanzlichen Hustensaft?",
                        "is_recommended": True,
                        "etiquette_note": "درخواست داروی «pflanzlich» (گیاهی) در داروخانه‌های آلمان بسیار محبوب و مرسوم است.",
                    },
                    {
                        "text": "Ich war nicht beim Arzt, geben Sie mir einfach etwas.",
                        "is_recommended": False,
                        "etiquette_note": "خیلی مبهم و شتاب‌زده است؛ بیان نوع داروی مدنظر به داروساز کمک می‌کند.",
                    },
                ],
            },
            {
                "speaker": "Herr Frank",
                "mine": False,
                "text": "Hier ist ein Efeu-Hustensaft. Nehmen Sie dreimal täglich fünf Milliliter nach dem Essen.",
                "translation": "بفرمایید، این شربت عصاره پیچک است. سه بار در روز پنج میلی‌لیتر بعد از غذا مصرف کنید.",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "تایید دستور مصرف، تشکر و آرزوی روز خوب:",
                "text": "Verstanden, dreimal täglich nach dem Essen. Vielen Dank und einen schönen Tag noch!",
                "translation": "متوجه شدم، سه بار در روز بعد از غذا. خیلی ممنون و روزتان خوش!",
                "audio": "",
                "branches": [
                    {
                        "text": "Verstanden, dreimal täglich nach dem Essen. Vielen Dank und einen schönen Tag noch!",
                        "is_recommended": True,
                        "etiquette_note": "تکرار دستور مصرف نشان‌دهنده دقت شماست و داروساز را مطمئن می‌کند.",
                    },
                    {
                        "text": "Danke, Tschüss.",
                        "is_recommended": False,
                        "etiquette_note": "گفتن «Tschüss» در داروخانه غیررسمی است؛ «Auf Wiedersehen» یا «Schönen Tag noch» پسندیده‌تر است.",
                    },
                ],
            },
        ],
    },
    23: {
        "scenario_id": "buergeramt_anmeldung",
        "title": "اداره امور شهروندان: ثبت رسمی نشانی محل سکونت (Bürgeramt: Anmeldung)",
        "setting": "Bürgeramt Innenstadt, Hamburg",
        "role_you": "Neubürger / Azubi (مهاجر/کارآموز)",
        "role_partner": "Herr Richter (کارشناس باجه شهرداری)",
        "partner_avatar": "R",
        "objective": "ارائه شماره نوبت، تحویل مدارک ثبت آدرس (پاسپورت و تاییدیه موجر)، امضای برگه و دریافت تاییدیه.",
        "etiquette_tip": "🇩🇪 قانون ثبت آدرس (Meldepflicht): هر فردی که وارد آلمان می‌شود موظف است ظرف ۲ هفته آدرس خود را در شهرداری ثبت کند. مدارک الزامی: پاسپورت و برگهٔ تاییدیه صاحبخانه («Wohnungsgeberbestätigung»). در ادارات رسمی آلمان حتماً سر وقت حاضر شوید.",
        "turns": [
            {
                "speaker": "Herr Richter",
                "mine": False,
                "text": "Nummer B42, bitte an Schalter 3! Guten Tag, Sie möchten Ihre Wohnung anmelden?",
                "translation": "شماره B42، لطفاً باجه ۳! روز بخیر، مایلید آدرس سکونتتان را ثبت کنید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "سلام رسمی و تایید نوبت ثبت نشانی:",
                "text": "Guten Tag! Ja genau, ich habe einen Termin zur Wohnsitzanmeldung.",
                "translation": "روز بخیر! بله دقیقاً، من یک نوبت برای ثبت محل سکونت دارم.",
                "audio": "",
                "branches": [
                    {
                        "text": "Guten Tag! Ja genau, ich habe einen Termin zur Wohnsitzanmeldung.",
                        "is_recommended": True,
                        "etiquette_note": "روشن و اداری: اصطلاح «Wohnsitzanmeldung» دقیقاً عنوان رسمی این فرایند قانونی است.",
                    },
                    {
                        "text": "Hallo, ich wohne jetzt in Hamburg.",
                        "is_recommended": False,
                        "etiquette_note": "خیلی غیررسمی برای باجهٔ شهرداری؛ در ادارات دولتی همیشه با اصطلاحات اداری صحبت کنید.",
                    },
                ],
            },
            {
                "speaker": "Herr Richter",
                "mine": False,
                "text": "Haben Sie Ihren Reisepass und die Wohnungsgeberbestätigung vom Vermieter dabei?",
                "translation": "پاسپورت و تاییدیه موجر (صاحبخانه) را همراه دارید؟",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "ارائه مدارک کامل به کارشناس باجه:",
                "text": "Ja, hier sind mein Reisepass und das ausgefüllte Formular vom Vermieter.",
                "translation": "بله، بفرمایید، این پاسپورت من و فرم تکمیل‌شده توسط صاحبخانه است.",
                "audio": "",
                "branches": [
                    {
                        "text": "Ja, hier sind mein Reisepass und das ausgefüllte Formular vom Vermieter.",
                        "is_recommended": True,
                        "etiquette_note": "ارائهٔ منظم مدارک اداری در آلمان بهترین راه برای تسریع کار و برخورد مثبت کارمند است.",
                    },
                    {
                        "text": "Ich habe nur den Mietvertrag dabei.",
                        "is_recommended": False,
                        "etiquette_note": "نکته مهم: طبق قانون آلمان، قرارداد اجاره کافی نیست و حتماً برگهٔ Wohnungsgeberbestätigung لازم است.",
                    },
                ],
            },
            {
                "speaker": "Herr Richter",
                "mine": False,
                "text": "Alles vollständig. Bitte prüfen Sie die Angaben und unterschreiben Sie hier unten.",
                "translation": "همه مدارک کامل است. لطفاً مشخصات را بررسی کنید و این پایین را امضا فرمایید.",
                "audio": "",
            },
            {
                "speaker": "Du",
                "mine": True,
                "prompt_label": "بررسی، امضا، تشکر و درخواست برگهٔ تاییدیه نهایی:",
                "text": "Die Daten stimmen. Ich habe unterschrieben. Erhalte ich die Meldebestätigung gleich?",
                "translation": "مشخصات درست است. امضا کردم. آیا برگهٔ تاییدیه ثبت آدرس را همین الان دریافت می‌کنم؟",
                "audio": "",
                "branches": [
                    {
                        "text": "Die Daten stimmen. Ich habe unterschrieben. Erhalte ich die Meldebestätigung gleich?",
                        "is_recommended": True,
                        "etiquette_note": "بسیار مهم: «Meldebestätigung» مدرک اصلی برای افتتاح حساب بانکی و بیمه در آلمان است.",
                    },
                    {
                        "text": "Fertig. Kann ich jetzt gehen?",
                        "is_recommended": False,
                        "etiquette_note": "بدون تحویل گرفتن برگهٔ Meldebestätigung خارج نشوید! حتماً این سند را از کارشناس تحویل بگیرید.",
                    },
                ],
            },
        ],
    },
}


def get_situational_scenario(lesson):
    """Return the situational scenario dict for this lesson, or None if it has none."""
    if not lesson or not getattr(lesson, "order", None):
        return None
    lesson_order = lesson.order
    if lesson_order in SITUATIONAL_SCENARIOS:
        return SITUATIONAL_SCENARIOS[lesson_order]
    return None
