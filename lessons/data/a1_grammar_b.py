"""Grammar topics for A1.2 (lessons 13-24).

``A1_2`` is filled in batches with ``A1_2.update({...})`` so the file stays easy to
extend. Titles are the stable key that ``lessons/data/a1_lessons_b.py`` references.
"""

A1_2: dict[str, str] = {}

# ------------------------------------------------------------- lessons 13-16
A1_2.update(
    {
        "Modalverben: können, wollen, möchten": """فعل‌های کمکی وجهی (Modalverben) با یک فعل اصلی می‌آیند و آن را صرف نمی‌کنند: فعل اصلی به شکل مصدر در آخر جمله می‌ماند.

können (توانستن): ich kann · du kannst · er kann · wir können · ihr könnt · sie können
wollen (خواستن): ich will · du willst · er will · wir wollen · ihr wollt · sie wollen
möchten (خواستن مؤدبانه): ich möchte · du möchtest · er möchte · wir möchten · ihr möchtet · sie möchten

مثال:
Ich kann gut schwimmen. (خوب می‌توانم شنا کنم.)
Wir wollen ins Kino gehen. (می‌خواهیم به سینما برویم.)
Ich möchte einen Kaffee trinken. (می‌خواهم یک قهوه بنوشم.)

نکته: در اول‌شخص و سوم‌شخص مفرد هیچ پایانه‌ای نمی‌آید: ich kann (نه: ich kanne).

English: Modal verbs können, wollen and möchten. They take the second position and send the main verb to the end in the infinitive.""",

        "Satzklammer mit Modalverben": """وقتی جمله یک فعل کمکی وجهی دارد، جمله یک «قوس» می‌سازد: فعل کمکی در جایگاه دوم و مصدر در آخر جمله.

Ich (۱) kann (۲) heute nicht kommen.
ساختار: فاعل + فعل کمکی + بقیه جمله + مصدر

مثال:
Er muss um sieben Uhr aufstehen. (او باید ساعت هفت بلند شود.)
Wir wollen am Samstag einkaufen. (می‌خواهیم شنبه خرید کنیم.)
Kannst du mir helfen? (می‌توانی کمکم کنی؟)

نکته: فعل جداشدنی در آخر جمله با پیشوندش می‌آید: Ich muss früh aufstehen. (نه: auf zu stehen)

English: The sentence bracket: modal verb in position 2, infinitive at the very end.""",

        "Verabredungen: Lust haben, Zeit haben": """برای قرار گذاشتن این ساختارها را به کار ببرید:

Hast du Zeit? (وقت داری؟)
Hast du Lust? (حوصله/میل داری؟)
Ich habe keine Zeit. (وقت ندارم.)
Ich habe Lust. (میل دارم.)

پیشنهاد دادن:
Wollen wir ins Kino gehen? (برویم سینما؟)
Hast du am Samstag Zeit? (شنبه وقت داری؟)
Ja, gern! (بله، با کمال میل!)
Es tut mir leid, ich habe keine Zeit. (متأسفم، وقت ندارم.)

قبول کردن: Ja, gern. / Das ist eine gute Idee. (فکر خوبی است.)
رد کردن مؤدبانه: Leider nicht. / Es tut mir leid, ich kann nicht.

English: Making and answering invitations with Zeit haben, Lust haben and „Wollen wir …?“""",

        "Wetter und unpersönliches es": """در آلمانی درباره هوا با ضمیر «es» حرف می‌زنیم؛ es فاعل صوری است و معنی «آن» نمی‌دهد:

Wie ist das Wetter? (هوا چطور است؟)
Es ist kalt. (هوا سرد است.)
Es ist warm. (هوا گرم است.)
Es regnet. (باران می‌بارد.)
Es schneit. (برف می‌بارد.)
Die Sonne scheint. (خورشید می‌تابد.)

واژه‌های هوا: das Wetter · der Regen · der Schnee · die Sonne · der Wind · kalt · warm · heiß · kühl · der Grad (درجه)
Heute sind es 20 Grad. (امروز ۲۰ درجه است.)

English: Weather with the impersonal „es“: Es ist kalt. Es regnet. Es schneit. Die Sonne scheint.""",

        "Jahreszeiten und Monate": """فصل‌ها:
der Frühling (بهار) · der Sommer (تابستان) · der Herbst (پاییز) · der Winter (زمستان)
die Jahreszeit (فصل سال)

ماه‌ها:
der Januar · der Februar · der März · der April · der Mai · der Juni
der Juli · der August · der September · der Oktober · der November · der Dezember

حرف اضافه: im + ماه و فصل
Im Winter ist es kalt. (در زمستان هوا سرد است.)
Im Juli fahre ich in den Urlaub. (تیر/جولای به تعطیلات می‌روم.)

English: Seasons and months, with the preposition „im“: im Winter, im Juli.""",

        "Komparativ (Grundlagen): kalt – kälter": """برای مقایسه، صفت پایانه «-er» می‌گیرد و بعد از آن «als» می‌آید:

kalt → kälter (سردتر) · warm → wärmer · groß → größer · klein → kleiner · alt → älter · jung → jünger
بی‌قاعده: gut → besser · viel → mehr · gern → lieber

مثال:
Im Winter ist es kälter als im Sommer. (زمستان از تابستان سردتر است.)
Berlin ist größer als Bonn. (برلین از بُن بزرگ‌تر است.)
Mein Bruder ist älter als ich. (برادرم از من بزرگ‌تر است.)

English: The comparative with -er + „als“: kälter als, größer als, älter als. Irregular: gut – besser, viel – mehr.""",

        "Modalverben: müssen, dürfen, sollen": """müssen (مجبور بودن): ich muss · du musst · er muss · wir müssen · ihr müsst · sie müssen
dürfen (اجازه داشتن): ich darf · du darfst · er darf · wir dürfen · ihr dürft · sie dürfen
sollen (باید/توصیه): ich soll · du sollst · er soll · wir sollen · ihr sollt · sie sollen

مثال:
Ich muss heute arbeiten. (امروز باید کار کنم.)
Hier darf man nicht rauchen. (اینجا سیگار کشیدن ممنوع است.)
Du sollst mehr schlafen. (بهتر است بیشتر بخوابی.)

نکته: در جمله منفی «nicht müssen» یعنی «لازم نیست» و «nicht dürfen» یعنی «اجازه نداشتن/ممنوع است»:
Du musst nicht kommen. (لازم نیست بیایی.)
Du darfst nicht rauchen. (اجازه نداری سیگار بکشی.)

English: müssen (must), dürfen (may) and sollen (should). Note that „nicht müssen“ means need not and „nicht dürfen“ means must not.""",

        "Zeitpräpositionen: am, um, im, vor, nach": """am + روز و بخش روز: am Montag · am Wochenende · am Morgen · am Abend
um + ساعت: um acht Uhr
im + ماه و فصل: im Januar · im Sommer
von … bis: von neun bis fünf Uhr
vor + dativ: vor dem Unterricht (قبل از کلاس)
nach + dativ: nach der Arbeit (بعد از کار)

مثال:
Am Freitag habe ich einen Termin. (جمعه یک قرار دارم.)
Der Kurs beginnt um neun Uhr. (کلاس ساعت نه شروع می‌شود.)
Nach der Arbeit gehe ich einkaufen. (بعد از کار خرید می‌کنم.)

English: Time prepositions am (days), um (clock), im (months/seasons), von … bis, vor and nach + dative.""",

        "Termine machen und verschieben": """قرار گذاشتن:

Haben Sie am Dienstag Zeit? (سه‌شنبه وقت دارید؟) — فارسی‌زبانان معمولاً اشتباه می‌کنند و می‌گویند «am Dienstag haben Sie Zeit؟» که برای سؤال درست نیست؛ در سؤال فعل اول می‌آید.
Ich möchte einen Termin machen. (می‌خواهم وقت بگیرم.)
Passt es Ihnen am Dienstag um zehn Uhr? (سه‌شنبه ساعت ده مناسب شماست؟)
Das passt mir gut. (مناسب من است.)
Leider kann ich nicht. Können wir den Termin verschieben? (متأسفانه نمی‌توانم. می‌توانیم قرار را جابه‌جا کنیم؟)
Der Termin ist am Dienstag, den dritten Mai. (قرار سه‌شنبه، سوم ماه مه است.)

English: Making, accepting and changing appointments: einen Termin machen, Passt es Ihnen …?, den Termin verschieben.""",

        "Wechselpräpositionen mit Dativ und Akkusativ": """حروف اضافه‌ای مانند in، an، auf، unter، über، neben، zwischen، vor، hinter دو حالت دارند:

• جای ثابت (wo?) → dativ: dem / der / dem / den
Das Bild hängt an der Wand. (تابلو روی دیوار است.)

• حرکت به سمتی (wohin?) → akkusativ: den / die / das / die
Ich hänge das Bild an die Wand. (تابلو را روی دیوار می‌آویزم.)

جفت‌فعل‌های مهم:
stehen / stellen · liegen / legen · sitzen / sich setzen
Ich stelle die Lampe neben das Sofa. (چراغ را کنار کاناپه می‌گذارم.)
Die Lampe steht neben dem Sofa. (چراغ کنار کاناپه است.)

English: Two-way prepositions: dative for position (wo?), accusative for direction (wohin?), with the pairs stehen/stellen, liegen/legen, sitzen/setzen.""",

        "Wegbeschreibung: Imperativ mit Sie und du": """برای راهنمایی کردن از imperative استفاده می‌کنیم:

با Sie: Gehen Sie geradeaus. · Biegen Sie links ab. · Nehmen Sie die U-Bahn.
با du: Geh geradeaus. · Bieg links ab. · Nimm die U-Bahn.

جمله‌های کاربردی:
Entschuldigung, wo ist der Bahnhof? (ببخشید، ایستگاه قطار کجاست؟)
Wie komme ich zum Bahnhof? (چطور به ایستگاه بروم؟)
Gehen Sie hier geradeaus, dann links. (اینجا را مستقیم بروید، بعد به چپ.)
Es ist nicht weit. (دور نیست.)

نکته: «ab|biegen» جداشدنی است: Biegen Sie links ab!

English: Giving directions with the imperative: Gehen Sie geradeaus, Biegen Sie links ab. Question: Wie komme ich zum …?""",

        "Präpositionen mit Dativ: mit, nach, zu, bei, aus": """این حروف اضافه همیشه با dativ می‌آیند:

mit (با): mit dem Bus · mit der Bahn · mit meinem Bruder
nach (به؛ برای شهر و کشور): nach Berlin · nach Deutschland
zu (به؛ برای اشخاص و جاها): zum Bahnhof · zur Arbeit · zu meinem Freund
bei (نزدِ): bei der Arbeit · bei meiner Familie
aus (از): aus dem Iran · aus der Schweiz

نکته: zum = zu + dem و zur = zu + der
Ich fahre mit dem Bus zur Arbeit. (با اتوبوس به سر کار می‌روم.)
Er kommt aus der Türkei. (او اهل ترکیه است.)

English: Dative prepositions mit, nach, zu, bei, aus. Contractions: zum = zu + dem, zur = zu + der.""",

        "Orientierung: links, rechts, geradeaus": """واژه‌های جهت:
links (چپ) · rechts (راست) · geradeaus (مستقیم) · hier (اینجا) · dort (آنجا)
die Ecke (گوشه) · die Kreuzung (چهارراه) · die Ampel (چراغ راهنما) · die Straße (خیابان) · der Weg (راه) · der Platz (میدان)
gegenüber (روبه‌روی) · neben (کنار) · zwischen (بین) · vor (جلوی) · hinter (پشت)

مثال:
Gehen Sie bis zur Kreuzung. (تا چهارراه بروید.)
Die Apotheke ist gleich um die Ecke. (داروخانه همان سر کوچه است.)
Der Bahnhof ist gegenüber von der Post. (ایستگاه روبه‌روی پست است.)

English: Orientation vocabulary: links, rechts, geradeaus and the words for corner, crossroads, traffic light, street and square.""",
    }
)

# ------------------------------------------------------------- lessons 17-20
A1_2.update(
    {
        "Perfekt mit „sein“: Reisen in der Vergangenheit": """برای حرف زدن درباره گذشته از زمان «Perfekt» استفاده می‌کنیم. این زمان دو بخش دارد: فعل کمکی + Partizip II.

شماری از فعل‌ها فعل کمکی «sein» می‌گیرند؛ بیشترشان فعل‌های حرکت و جابه‌جایی هستند:
gehen → ist gegangen (رفته است)
kommen → ist gekommen · fahren → ist gefahren · fliegen → ist geflogen · reisen → ist gereist · ankommen → ist angekommen

ساختار جمله:
Ich bin nach Berlin gefahren. (به برلین رفته‌ام.)
Wir sind im Sommer nach Österreich gereist. (تابستان به اتریش سفر کردیم.)
Er ist um acht Uhr angekommen. (او ساعت هشت رسید.)
Wann bist du gefahren? (چه وقت رفتی؟)

نکته: فعل کمکی در جایگاه دوم است و Partizip II در آخر جمله.

English: The perfect tense with „sein“ for verbs of movement: Ich bin gefahren, Wir sind gereist, Er ist angekommen.""",

        "Reisen: mit dem Zug, mit dem Bus": """واژه‌های سفر:
die Reise (سفر) · der Urlaub (تعطیلات) · das Hotel · das Einzelzimmer · das Doppelzimmer · die Rezeption
der Koffer · das Gepäck · der Rucksack · das Ticket · die Fahrkarte · der Flughafen · der Abflug · die Abfahrt · die Ankunft

با وسیله نقلیه: mit dem Zug · mit dem Bus · mit dem Auto · mit dem Flugzeug · mit dem Fahrrad
به یک شهر/کشور: nach Berlin · nach Deutschland
به یک جا/شخص: zum Bahnhof · zum Flughafen · zur Rezeption

مثال:
Wir fahren mit dem Zug nach München. (با قطار به مونیخ می‌رویم.)
Ich fliege mit dem Flugzeug nach Deutschland. (با هواپیما به آلمان پرواز می‌کنم.)
Mein Koffer ist am Flughafen. (چمدانم در فرودگاه است.)

English: Travel vocabulary and the patterns mit dem Zug / nach Berlin / zum Bahnhof.""",

        "Hotel: Höflichkeitsfragen und Bitten": """در هتل با «Sie» و جمله‌های مؤدبانه حرف می‌زنیم:

Ich habe eine Reservierung. (رزرو دارم.)
Ich möchte ein Einzelzimmer. (یک اتاق یک‌نفره می‌خواهم.)
Haben Sie noch ein Zimmer frei? (اتاق خالی دارید؟)
Was kostet das Zimmer pro Nacht? (اتاق شبی چقدر است?)
Frühstück ist inklusive. (صبحانه هم شامل است.)
Können Sie mir helfen? (می‌توانید کمکم کنید؟)
Wo ist der Aufzug? (آسانسور کجاست؟)

فرم‌های مؤدبانه درخواست:
Könnten Sie … ? (می‌توانید …؟) — در سطح A1 همین «Können Sie … ?» هم مؤدبانه است.
Bitte, würden Sie … ? — برای سطح بالاتر.

English: Polite requests at a hotel with „Sie“: eine Reservierung haben, ein Zimmer frei haben, Können Sie … ?""",

        "Der Körper und Schmerzen: weh tun": """اعضای بدن:
der Kopf · das Auge · das Ohr · die Nase · der Mund · der Zahn · der Hals · das Haar
der Arm · die Hand · der Finger · das Bein · der Fuß · der Bauch · der Rücken · das Herz

برای درد از «weh tun» استفاده می‌کنیم؛ شخص در حالت dativ و عضو بدن فاعل است:
Mein Kopf tut weh. (سرم درد می‌کند.)
Meine Beine tun weh. (پاهایم درد می‌کنند.)
Der Zahn tut mir weh. (دندانم درد می‌کند.)

پرسیدن حال کسی:
Was ist los? (چه شده؟) · Was fehlt Ihnen? (چه ناراحتی دارید؟)
Ich habe Kopfschmerzen. — در سطح A1 می‌توانید بگویید: Mein Kopf tut weh.

English: Body parts and pain with „weh tun“: Mein Kopf tut weh. Der Zahn tut mir weh.""",

        "Modalverben beim Arzt: sollen, müssen, dürfen": """در مطب دکتر این فعل‌های وجهی زیاد به کار می‌روند:

sollen = توصیه پزشک: Sie sollen mehr schlafen. (باید بیشتر بخوابید.)
nehmen = مصرف کردن: Nehmen Sie die Tabletten dreimal am Tag. (قرص‌ها را روزی سه بار بخورید.)
müssen = اجبار: Sie müssen zu Hause bleiben. (باید در خانه بمانید.)
dürfen = اجازه (در منفی: ممنوع): Sie dürfen keinen Sport machen. (اجازه ندارید ورزش کنید.)

مثال گفتگو:
Was fehlt Ihnen? – Ich habe Fieber und mein Hals tut weh.
Sie müssen viel trinken und Sie dürfen nicht rauchen.

English: Modal verbs at the doctor's: sollen (advice), müssen (must), dürfen (may / must not).""",

        "Ratschläge geben: Imperativ und sollen": """برای توصیه دو راه داریم:

• Imperativ (با du یا Sie):
Schlaf mehr! (بیشتر بخواب!) · Trinken Sie viel Wasser!
Geh zum Arzt! · Bleib im Bett!

• sollen:
Du sollst mehr schlafen. (بهتر است بیشتر بخوابی.)
Sie sollen viel trinken. (باید زیاد آب بنوشید.)

مؤدبانه‌تر:
Ich glaube, du solltest zum Arzt gehen. — «solltest» شکل Konjunktiv II است و برای A1 لازم نیست؛ شما با «Du sollst zum Arzt gehen» منظور را می‌رسانید.
An deiner Stelle würde ich … — برای سطوح بالاتر.

English: Giving advice with the imperative (Schlaf mehr! Trinken Sie viel!) or with sollen (Du sollst mehr schlafen).""",

        "Perfekt mit „haben“": """بیشتر فعل‌ها در Perfekt فعل کمکی «haben» می‌گیرند. ساختار: haben (جایگاه دوم) + Partizip II (آخر جمله).

ich habe · du hast · er hat · wir haben · ihr habt · sie/Sie haben

مثال:
Ich habe gestern gearbeitet. (دیروز کار کردم.)
Was hast du am Wochenende gemacht? (آخر هفته چه کار کردی؟)
Wir haben einen Film gesehen. (یک فیلم دیدیم.)
Sie hat nichts gesagt. (او چیزی نگفت.)

نکته: فعل‌هایی که مفعول مستقیم دارند، همیشه با «haben» می‌آیند.

English: The perfect tense with „haben“: haben in position 2, participle at the end. Most verbs take haben.""",

        "Partizip II: regelmäßige Verben": """فعل‌های باقاعده Partizip II را این‌طور می‌سازند:
ge- + ریشه + -t
machen → gemacht · lernen → gelernt · kaufen → gekauft · spielen → gespielt
arbeiten → gearbeitet · kochen → gekocht · wohnen → gewohnt · hören → gehört · suchen → gesucht

دو استثنا مهم:
• فعل‌های مختوم به -ieren بدون ge-: telefonieren → telefoniert · studieren → studiert · reagieren → reagiert
• فعل‌های با پیشوند بی‌تکیه (be-, ver-, er-، ge-): besuchen → besucht · verstehen → verstanden · erzählen → erzählt

فعل‌های جداشدنی: ge- بین پیشوند و ریشه می‌آید:
aufstehen → aufgestanden · einkaufen → eingekauft · anrufen → angerufen · mitnehmen → mitgenommen

English: Regular participles are ge- + stem + t (gemacht, gearbeitet). No ge- with -ieren or unstressed prefixes; separable verbs put ge- in the middle.""",

        "Perfekt: Satzklammer": """در جمله Perfekt دو بخش فعل جمله را «قوس» می‌دهند:
فعل کمکی (haben/sein) در جایگاه دوم + Partizip II در آخر جمله.

Ich habe gestern einen Film gesehen.
Er ist nach Berlin gefahren.
Ich bin um sechs Uhr aufgestanden.
Hast du schon gegessen?

نکته: در سؤال‌های بله/خیر فعل کمکی اول جمله می‌آید: Hast du … ?
در سؤال W: Was hast du … ?

جمله‌های زمانی گذشته:
gestern (دیروز) · vorgestern (پریروز) · letzte Woche (هفته گذشته) · letzten Monat · letztes Jahr · im Sommer (تابستان گذشته)
Ich habe letzte Woche viel gearbeitet. (هفته گذشته زیاد کار کردم.)

English: The perfect tense bracket (auxiliary in position 2, participle last) and past time expressions: gestern, letzte Woche, im Sommer.""",

        "Vergangenes: gestern, letzte Woche, im Sommer": """برای حرف زدن درباره گذشته این قیدهای زمان را به کار ببرید:
gestern (دیروز) · vorgestern (پریروز) · letzte Woche (هفته گذشته) · letzten Monat (ماه گذشته) · letztes Jahr (سال گذشته) · im Sommer (تابستان؛ در بافت گذشته)

مثال:
Gestern habe ich gearbeitet. (دیروز کار کردم.)
Letzte Woche waren wir im Kino. (هفته گذشته سینما بودیم.)
Im Sommer sind wir nach Deutschland geflogen. (تابستان به آلمان پرواز کردیم.)

نکته: قید زمان می‌تواند اول جمله بیاید؛ آن‌گاه فعل کمکی پس از آن و فاعل پس از فعل می‌آید:
Letzte Woche habe ich viel gearbeitet.

English: Time expressions for the past (gestern, letzte Woche, letzten Monat, letztes Jahr), plus the inversion they trigger.""",

        "Partizip II: unregelmäßige Verben": """بسیاری از فعل‌های پرکاربرد بی‌قاعده‌اند و باید Partizip II آن‌ها را حفظ کرد:

essen → gegessen · trinken → getrunken · sehen → gesehen · lesen → gelesen
schreiben → geschrieben · sprechen → gesprochen · nehmen → genommen
finden → gefunden · treffen → getroffen · schlafen → geschlafen
gehen → gegangen · kommen → gekommen · fahren → gefahren · fliegen → geflogen
bleiben → geblieben · heißen → geheißen · wissen → gewusst

با haben: Ich habe einen Apfel gegessen. (یک سیب خوردم.)
با sein: Ich bin nach Hause gegangen. (به خانه رفتم.)

English: Irregular participles (gegessen, getrunken, gesehen, genommen, gefahren, gegangen …) – learn them by heart.""",

        "Datum und Ordinalzahlen": """اعداد ترتیبی:
der erste · der zweite · der dritte · der vierte · der fünfte · der sechste · der siebte · der achte · der neunte · der zehnte
der elfte · der zwölfte · der zwanzigste · der einundzwanzigste · der dreißigste · der einunddreißigste

نکته: از ۲۰ به بعد «-ste» می‌گیرند و تا ۱۹ «-te».

گفتن تاریخ:
Der Wievielte ist heute? – Heute ist der dritte Mai. (امروز سوم ماه مه است.)
Mein Geburtstag ist am vierten Juli. (روز تولد من چهارم جولای است.)

نکته: در جمله با «am» عدد ترتیبی پایان «-en» می‌گیرد: am dritten Mai.

English: Ordinal numbers and dates: Heute ist der dritte Mai. Am dritten Mai habe ich einen Termin.""",

        "Einladungen: Feste und Glückwünsche": """واژه‌های جشن:
das Fest · die Feier · die Party · die Einladung · das Geschenk · der Gast · die Hochzeit · der Geburtstag · herzlichen Glückwunsch

دعوت و تبریک:
Ich habe eine Einladung. (یک دعوت‌نامه دارم.)
Ich möchte dich einladen. (می‌خواهم تو را دعوت کنم.)
Herzlichen Glückwunsch zum Geburtstag! (تولدت مبارک!)
Alles Gute! (بهترین آرزوها!) · Viel Glück! (موفق باشی!) · Viel Spaß! (خوش بگذره!)

پاسخ مؤدبانه:
Vielen Dank! Ich komme gern. (خیلی ممنون! با کمال میل می‌آیم.)
Leider kann ich nicht kommen. (متأسفانه نمی‌توانم بیایم.)

English: Parties, invitations and congratulations: Herzlichen Glückwunsch!, Alles Gute!, Viel Glück! and polite replies.""",
    }
)

# ------------------------------------------------------------- lessons 21-24
A1_2.update(
    {
        "Telefonieren: Höflichkeitsformen": """در تماس تلفنی آلمانی این جمله‌ها را به کار ببرید:

Guten Tag, hier ist … (روز بخیر، … صحبت می‌کند.)
Kann ich bitte mit Herrn Klein sprechen? (می‌توانم با آقای کلاین صحبت کنم؟)
Einen Moment, bitte. (یک لحظه لطفاً.)
Können Sie das bitte wiederholen? (می‌توانید لطفاً تکرار کنید؟)
Ich verstehe nicht. Können Sie langsamer sprechen? (نمی‌فهمم. می‌توانید آهسته‌تر صحبت کنید؟)
Ich rufe später wieder an. (بعداً دوباره زنگ می‌زم.)
Auf Wiederhören! (خداحافظ – مخصوص تلفن)

نکته: در تلفن «Auf Wiederhören» می‌گوییم، نه «Auf Wiedersehen».

English: Telephone phrases: Hier ist …, Kann ich mit … sprechen?, Auf Wiederhören! Note the telephone goodbye.""",

        "Indirekte Fragen mit ob und W-Wort": """اگر سؤالی را داخل جمله بیاوریم، فعل به آخر می‌رود:

سؤال مستقیم: Wo ist der Bahnhof?
سؤال غیرمستقیم: Wissen Sie, wo der Bahnhof ist?

سؤال بله/خیر با «ob»:
Kommen Sie morgen? → Wissen Sie, ob Sie morgen kommen?
Ich weiß nicht, ob er Zeit hat. (نمی‌دانم آیا وقت دارد.)

سؤال W با کلمه پرسشی:
Ich weiß nicht, wann der Zug fährt. (نمی‌دانم قطار چه وقت حرکت می‌کند.)
Kannst du mir sagen, wo die Post ist? (می‌توانی بگویی پست کجاست؟)

نکته: بعد از کاما فعل به آخر جمله می‌رود — این مهم‌ترین نکته این ساختار است.

English: Indirect questions with „ob“ (yes/no) or a W-word; the verb moves to the end of the clause.""",

        "E-Mail und Brief: Anrede und Gruß": """ساختار یک ایمیل/نامه کوتاه در سطح A1:

تحیت (Anrede):
Liebe Anna, / Lieber Ben, (دوستانه)
Sehr geehrte Frau Klein, / Sehr geehrter Herr Klein, (رسمی، در نامه)
Hallo Herr Klein, (رایج در ایمیل)

متن: درخواست خود را کوتاه بنویسید
Ich schreibe Ihnen, weil ich eine Frage habe. (به شما می‌نویسم چون یک سؤال دارم.)
Ich möchte einen Termin machen.

پایان (Gruß):
Viele Grüße / Freundliche Grüße (دوستانه)
Mit freundlichen Grüßen (رسمی)

نام: در ایمیل دوستانه فقط نام کوچک، در نامه رسمی نام و نام خانوادگی.

English: How to open and close a German e-mail or letter: Liebe/Lieber …, Sehr geehrte …, Viele Grüße, Mit freundlichen Grüßen.""",

        "seit + Dativ": """«seit» یعنی «از زمانِ … تا حالا» و همیشه با dativ می‌آید:
seit einem Jahr · seit zwei Monaten · seit 2020

مثال:
Ich lerne seit einem Jahr Deutsch. (یک سال است آلمانی یاد می‌گیرم.)
Sie wohnt seit September in Berlin. (از سپتامبر در برلین زندگی می‌کند.)
Ich arbeite seit drei Jahren hier. (سه سال است اینجا کار می‌کنم.)

نکته مهم برای فارسی‌زبانان: در فارسی می‌گوییم «یک سال است که…» و در آلمانی هم زمان حال به کار می‌رود، نه گذشته:
✅ Ich lerne seit einem Jahr Deutsch. — ❌ Ich habe seit einem Jahr Deutsch gelernt.

English: seit + dative for „since/for“ (Ich lerne seit einem Jahr Deutsch) – the tense stays present.""",

        "Präpositionen mit Dativ: mit, nach, bei, seit, von, zu, aus": """فهرست کامل حروف اضافه‌ای که همیشه dativ می‌گیرند:
aus · bei · mit · nach · seit · von · zu · gegenüber

der Mann → mit dem Mann · die Frau → mit der Frau · das Kind → mit dem Kind · die Eltern → mit den Eltern

مثال:
Er fährt mit dem Fahrrad. (با دوچرخه می‌رود.)
Sie kommt gerade von der Arbeit. (همین حالا از سر کار می‌آید.)
Wir wohnen bei unseren Eltern. (نزد پدر و مادرم زندگی می‌کنیم.)
Ich gehe zu meiner Freundin. (پیش دوستم می‌روم.)
Das ist ein Geschenk von meinem Bruder. (این هدیه‌ای از برادرم است.)

English: The dative prepositions aus, bei, mit, nach, seit, von, zu, gegenüber with dem/der/dem/den.""",

        "Lernen und Prüfungen: Wortschatz und Strukturen": """واژه‌های درس و امتحان:
die Schule · der Schüler · der Kurs · der Unterricht · die Klasse · die Aufgabe · die Übung · die Hausaufgabe
die Prüfung · der Test · die Note · die Frage · die Antwort · die Lösung · der Fehler · das Beispiel · das Thema · der Text · der Satz
das Heft · das Wörterbuch · die Bibliothek · die Universität · das Studium

جمله‌های کاربردی:
Ich habe eine Frage. (یک سؤال دارم.)
Können Sie das bitte erklären? (می‌توانید لطفاً توضیح دهید؟)
Ich habe die Hausaufgaben gemacht. (تکلیف‌ها را انجام دادم.)
Ich mache einen Deutschkurs. (دوره آلمانی می‌گذرانم.)
Ich habe die Prüfung bestanden. — «bestehen» در سطح A1 فقط به‌عنوان عبارت: Ich habe die Prüfung geschafft. (امتحان را قبول شدم.)
Wie schreibt man das? (این را چطور می‌نویسند؟)

English: School and exam vocabulary with the sentences you need in a language course.""",

        "Formulare verstehen: Höflichkeitsformen und Imperativ": """در فرم‌ها و اداره‌ها این جمله‌ها را می‌خوانید و می‌شنوید:

Füllen Sie das Formular aus. (فرم را پر کنید.)
Schreiben Sie bitte deutlich. (لطفاً واضح بنویسید.)
Unterschreiben Sie hier. (اینجا امضا کنید.)
Bitte legen Sie Ihren Ausweis vor. (لطفاً کارت شناسایی‌تان را ارائه دهید.)
Ihre Daten, bitte. (اطلاعات شما لطفاً.)

واژه‌های فرم:
der Familienname · der Vorname · das Geburtsdatum · der Geburtsort · die Adresse · die Postleitzahl · die Unterschrift · der Ausweis · die Anmeldung

نکته: روی فرم‌های آلمانی معمولاً اول Familienname (نام خانوادگی) می‌آید و بعد Vorname.

English: Reading and filling in German forms: Füllen Sie … aus, Unterschreiben Sie hier, plus the field names.""",

        "Ordinalzahlen in Formularen und Dokumenten": """در فرم‌ها و مکاتبه‌های اداری تاریخ را با عدد ترتیبی می‌نویسند:

تهران، ۳ مه ۲۰۲۵ → Berlin, der 3. Mai 2025 / Berlin, 03.05.2025

در متن:
am dritten Mai → am 3. Mai
Mein Geburtsdatum ist der vierte Juli 1995. (تاریخ تولد من چهارم جولای ۱۹۹۵ است.)

عددهای ترتیبی پرکاربرد در فرم:
der erste · der zweite · der dritte · der vierte · der fünfte · der zehnte · der zwölfte · der zwanzigste · der einunddreißigste

English: Ordinal numbers in forms and official letters, and the two common date formats (der 3. Mai / 03.05.2025).""",

        "Bank und Amt: Fragen stellen": """جمله‌های کاربردی در بانک و اداره:

Ich möchte ein Konto eröffnen. (می‌خواهم حساب باز کنم.)
Ich möchte Geld überweisen. (می‌خواهم پول انتقال دهم.)
Wo ist der Schalter? (باجه کجاست؟)
Wo bekomme ich Informationen? (از کجا اطلاعات می‌گیرم؟)
Haben Sie einen Termin für mich? (برای من وقت دارید؟)
Ich brauche eine Bestätigung. (یک تأییدیه لازم دارم.)
Können Sie mir bitte helfen? (می‌توانید لطفاً کمکم کنید؟)

واژه‌ها: das Konto · der Schalter · die Auskunft · die Unterschrift · die Anmeldung · der Kunde · die Zahl · das Formular · die Bestätigung

English: Useful questions at the bank and at official offices, plus the key vocabulary.""",

        "Wiederholung: Verbformen im Überblick": """مرور همه شکل‌های فعل که در A1 یاد گرفتید:

۱) حال ساده (Präsens):
ich wohne · du wohnst · er wohnt · wir wohnen

۲) فعل‌های بی‌قاعده با تغییر مصوت:
du fährst · er schläft · du isst · er nimmt · du sprichst

۳) فعل‌های جداشدنی:
Ich stehe um sechs Uhr auf. · Der Kurs fängt um neun an.

۴) فعل‌های وجهی:
ich kann · ich muss · ich darf · ich soll · ich will · ich möchte
Ich muss heute arbeiten.

۵) گذشته (Präteritum) از sein و haben:
ich war · ich hatte

۶) گذشته (Perfekt):
ich habe gearbeitet · ich bin gefahren · ich habe aufgeräumt

English: All the verb forms of A1: present, stem-changing verbs, separable verbs, modals, war/hatte and the perfect tense.""",

        "Wiederholung: Satzbau im Überblick": """قواعد جایگاه کلمه در A1:

۱) جمله خبری — فعل در جایگاه دوم:
Ich trinke morgen Kaffee.
Morgen trinke ich Kaffee. (اگر چیز دیگری اول بیاید، فاعل بعد از فعل می‌آید.)

۲) سؤال بله/خیر — فعل اول:
Trinkst du Kaffee?

۳) سؤال W — کلمه پرسشی اول، فعل دوم:
Was trinkst du?

۴) قوس فعل با فعل وجهی:
Ich muss heute länger arbeiten.

۵) قوس فعل در Perfekt:
Ich habe gestern gearbeitet.

۶) جمله‌های فرعی با weil / dass / ob / wenn — فعل به آخر می‌رود:
Ich komme nicht, weil ich keine Zeit habe.

English: Word order in statements, questions, the verb bracket with modals and the perfect, and subordinate clauses with weil/dass/ob/wenn.""",

        "Wiederholung: Fälle im Überblick: Nominativ, Akkusativ, Dativ": """در A1 سه حالت مهم داریم:

۱) Nominativ (فاعل):
der Tisch ist neu. · die Lampe ist neu. · das Buch ist neu. · die Schuhe sind neu.

۲) Akkusativ (مفعول مستقیم):
der → den · ein → einen (بقیه تغییر نمی‌کنند)
Ich kaufe einen Tisch. · Ich nehme die Lampe. · Ich lese das Buch.

۳) Dativ (مفعول غیرمستقیم و بعد از حروف اضافه خاص):
der → dem · die → der · das → dem · die (جمع) → den (+ -n)
Ich helfe dem Mann. · Das gefällt der Frau. · Ich fahre mit dem Bus.

جدول کوتاه:
        مذکر    مؤنث    خنثی    جمع
Nom.    der     die     das     die
Akk.    den     die     das     die
Dat.    dem     der     dem     den

English: The three A1 cases at a glance: nominative, accusative and dative, with the article table.""",
    }
)

# === APPEND HERE ===
