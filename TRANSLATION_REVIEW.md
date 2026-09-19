# A1 Persian translations — review pass

**Scope:** all 987 A1 vocabulary rows in the `vocabulary_word` table (German → Persian glosses).
**Data of record:** `vocabulary/data/*.json` — the database is regenerated from these files with
`python manage.py import_a1_words`, so every fix below lives in the JSON, not only in Postgres.

## Important limitation — please read

This pass was carried out by the assistant, **not by a native Persian speaker**. It is a
methodical review (every gloss read against its German headword, plus automated consistency
checks), but it is not a substitute for a native speaker's judgement on idiom and register.

Two things are machine-verified and can be trusted:

- **Structure** — article ↔ gender agreement, noun capitalisation, required fields, duplicates: 0 issues.
- **Collisions** — no two different German words are left sharing an identical Persian gloss
  unless they are true synonyms (see the bottom of this document).

Everything in *"Needs a native call"* below is a judgement call I could not settle with confidence.

## Method

1. Dumped all 987 rows and read every Persian gloss against its German headword.
2. Automated check: article ↔ gender agreement, noun capitalisation, non-nouns carrying a stray
   article/gender, empty Persian/English/IPA fields.
3. Automated check: grouped rows by identical Persian gloss to surface two German words that a
   learner could not tell apart (e.g. `nein` vs `neun`).
4. Applied corrections to the JSON data files and re-imported.

## Corrections applied

### Wrong or misleading glosses

| German | Was | Now | Why |
|---|---|---|---|
| `die Wurst` | سوسیژ | **سوسیس** | Typo — the old string was not a word. |
| `alles Gute` | همه چیز خوب | **بهترین آرزوها** | Literal translation. It is a farewell wish, not a statement about things. |
| `gern` | با میل، دوستانه | **با کمال میل، با رغبت** | "دوستانه" means *friendly*, not *gladly*. |
| `selbstständig` | خودکفا، آزاد | **خودکفا، مستقل** | "آزاد" means *free*, which is not the sense (self-employed / independent). |
| `weh tun` | درد دادن | **درد کردن** | Persian says the pain "does" (`درد کردن`), not "gives". |
| `schmecken` | مزه دادن | **مزه داشتن، خوشمزه بودن** | Same construction issue. |
| `regnen` | باران آمدن | **باران باریدن** | Persian rain "falls" (`باریدن`), it does not "come". |
| `schneien` | برف آمدن | **برف باریدن** | Same. |

### Ambiguities — two words a learner could not tell apart

| German | Was | Now | Why |
|---|---|---|---|
| `nein` / `neun` | **both** `نه` | `نه (پاسخ منفی)` / `نه (عدد ۹)` | Both genuinely translate as `نه`: *no* and *nine*. Was a real trap. |
| `Kugelschreiber` / `automatisch` | **both** `خودکار` | `خودکار (قلم)` / `اتوماتیک، خودبهخود` | `خودکار` means both *ballpoint pen* and *automatic*. |
| `Bein` / `Fuß` | **both** `پا` | `پا (ساق)` / `پا (کف پا)` | *leg* vs *foot* — same Persian word. |
| `sitzen` / `sich setzen` | **both** `نشستن` | `نشستن (حالت)` / `نشستن (عمل نشستن)` | *to be sitting* vs *to sit down*. |
| `Apartment` / `Wohnung` | **both** `آپارتمان` | `آپارتمان مبله` / `آپارتمان` | `Apartment` in the Goethe list is the furnished/short-let kind. |
| `Uhr` / `Stunde` | **both** `ساعت` | `ساعت (وسیله)` / `ساعت (مدت)` | clock vs hour. |

### Clarifications (gloss widened or disambiguated)

| German | Was | Now |
|---|---|---|
| `der Spaß` | سرگرمی | **لذت، خوشی** (collided with `das Hobby` = سرگرمی) |
| `die Zitrone` | لیمو | **لیموترش** (unmarked `لیمو` usually means the sweet lime) |
| `der Termin` | قرار | **قرار ملاقات** |
| `der Beruf` | حرفه | **شغل، حرفه** |
| `das Wetter` | هوا | **آبوهوا** (unmarked `هوا` also means *air*) |
| `die Jacke` | کاپشن | **ژاکت** (`کاپشن` is colloquial) |
| `die Torte` | کیک تزئینی | **تورت (کیک خامهای)** |
| `das Gepäck` | چمدان و بار | **بار و اسباب سفر** |
| `das Lokal` | کافه‌رستوران محلی | **کافه یا رستوران محلی** |
| `die Geschwister` | خواهر و برادر | **خواهر و برادرها** (it is plural) |
| `der Anrufbeantworter` | منشی تلفنی | **پاسخگوی خودکار** |
| `der Unterricht` | درس | **کلاس درس** |
| `die Sehenswürdigkeit` | جاذبه دیدنی | **جاذبه گردشگری** |
| `der Geburtstag` | تولد | **روز تولد** |
| `die Medizin` | دارو، پزشکی | *(plural removed — `die Medizinen` is not used)* |

## Needs a native call

These are not errors I can settle. Flagging them for a Persian speaker to confirm:

1. **Register consistency — the biggest open question.** Some phrases are colloquial
   (`چطوری؟`, `اسمت چیه؟`, `خوش بگذره`, `حواست باشه`, `مشکلی نیست`) while others are formal
   (`ببخشید، چه گفتید؟`, `با احترام`, `خوش آمدید`). A1 material usually teaches one register
   consistently. **Decide whether the whole set should be formal or informal** and I will
   normalise it.
2. **`der Herd` = اجاق گاز** — names *gas* specifically; plain `اجاق` may be the better general gloss.
3. **`das Brötchen` = نان کوچک** — descriptive rather than idiomatic. Is `نان بروتشن` or `کلوچه` better?
4. **`die Nudeln` = ماکارونی** — covers pasta/noodles; confirm this reads naturally.
5. **`die Mütze` = کلاه بافتنی** — beanie vs cap distinction; confirm.
6. **`der Cent` = سنت** — confirm the common written form used in Iran.
7. **`gern haben` vs `mögen`** — both currently `دوست داشتن`. Acceptable, but if a distinction is
   wanted, `gern haben` is closer to `خوش داشتن`.
8. **`möchten` = خواستن (مودبانه)** — it is a Konjunktiv II form, not a normal infinitive. The
   parenthetical is doing a lot of work; confirm it reads clearly.
9. **Numbers 13–19** — written as single words (`dreizehn`, `achtzehn`). Note `sechzehn` and
   `siebzehn` drop letters; confirm the spelling entries look right to a teacher.

## Deliberately left as identical synonyms (no action)

These share a Persian gloss and that is correct — they are true synonyms or the same referent:

`anfangen`/`beginnen` (شروع کردن) · `bezahlen`/`zahlen` (پرداخت کردن) · `Ende`/`Schluss` (پایان) ·
`machen`/`tun` (انجام دادن) · `Großmutter`/`Oma` (مادربزرگ) · `Samstag`/`Sonnabend` (شنبه) ·
`gern haben`/`mögen` (دوست داشتن)

## Re-running the checks

```bash
# re-import after editing any JSON under vocabulary/data/
.venv/bin/python manage.py import_a1_words --no-audio

# structure + collision check
.venv/bin/python manage.py check
```

Structure and collision checks were re-run after these edits: **987 rows, 0 structural issues,
7 remaining shared glosses (all listed above as intentional).**
