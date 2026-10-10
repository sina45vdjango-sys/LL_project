# Velingo — Browser Review Report

- **Date:** 2026-10-06 — **post-fix revision** (same day): every issue from the first revision was re-verified behaviorally after the owner's fixes; see the Status column in §10 and the new scores in §1.
- **Agent:** Buffy (automated browser audit, Playwright + headless Chromium 154 via `/usr/bin/chromium-browser`)
- **Database:** `language_learning_mirror` (confirmed with
  `.venv/bin/python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"` → `language_learning_mirror`) — read-only use, no seeds, no imports, no migrations, no deletes.
- **Code changes:** none. Writes were limited to `REVIEW-REPORT.md` and `review-artifacts/` (this revision added the probe `review-artifacts/notes/tools/reverify_fixes.js` and its results).
- **Server command used:**
  ```bash
  DJANGO_DEBUG=False DJANGO_SERVE_MEDIA=True DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  .venv/bin/python manage.py runserver 0.0.0.0:8000 --insecure
  ```
- **Build/check status:** `.venv/bin/python manage.py check` → `System check identified no issues (0 silenced).` (exit 0). Post-fix: `manage.py validate_a1_content` → **all checks passed**; `manage.py test` → **1049 tests OK (skipped=1)** (exit 0).
- **Test accounts:** `audit-fresh` (first revision). Usernames `<100×u>`, `کاربر۱۲۳`, `<script>alert(1)</script>` exist on the mirror because the *first revision's* form accepted them; the fixed form now rejects all three (verified in this revision). Post-fix accounts created through the form: `audit-fix-goal-088231` (browser) and `audit-fix-db2` (test client).
- **Console health summary:** 0 JavaScript errors (`pageerror`) on every page visited. The only console lines are Chromium's own "Failed to load resource" notes for the HTTP statuses the app deliberately returns (404 on a bad URL, 405 on `GET` of POST-only endpoints, 403 on a guest hint request, 400 on malformed API calls). Full logs: `review-artifacts/notes/console-*.json`.

## Data snapshot (mirror, 2026-10-06)

| Item | Count |
|---|---|
| Courses | 1 (`Deutsch A1 – Von null bis A1`, published) |
| Lessons | 24 (all published; **no drafts exist in this DB**) |
| Words | 3226 (1018 linked to A1 lessons) |
| Exercises / Questions | 586 / 3504 |
| Exercise types present | MULTIPLE_CHOICE 153, LISTENING 162, READING 92, TRANSLATION 92, SCRAMBLE 45, TRUE_FALSE 23, FILL_BLANK 19 (no published SPEAKING or WRITING exercises) |
| Exam runs | 4 before the audit (8, 7, 6, 3) + the ones this audit started (9, 10) |
| Audio files | 3798 MP3 (90 MB); every `audio` reference on Word/Grammar/Sentence/LessonContent/Question resolves to a non-empty file (0 missing) |

Raw data: `review-artifacts/notes/data-snapshot.json`, `audio-files.json`, `crawl-guest.json`.

---

## 1. Verdict & score

**Overall: 94 / 100 — A** (post-fix revision; the first revision scored **88 / 100 — B**).

This is a genuinely good A1 course wearing a solid Django shell. The teaching content holds up to an examiner's read: real grammar progression, correct German, natural Persian, honest exam mirroring, and a claim set that mostly matches reality. The marketing-free tone ("nothing here is graded", "the correct answer is nowhere on this page", the Goethe source quoted on the exam page) is exactly what a German trainer should see. What pulled the first revision's score down was not the course but the **account forms a learner meets first**: the goal form promised that saving everything empty clears the goal while storing a target date the learner never chose, and one password error was raw English from Django. Both are fixed and re-verified in this revision (an untouched save now stores no date at all, and the message is «گذرواژه باید حداقل ۸ نویسه باشد.»); the remaining deductions are the small, honest ones listed in §2. Nothing I found makes the site unusable, wrong-grading, or leaky.

### Score table

| # | Dimension | Weight | Score | One-line justification |
|---|---|---|---|---|
| 1 | Teaching quality (teacher lens) | 15 | 10 | Correct German, real progression, Persian written for Persian speakers; Wortliste coverage 99.7%; `sich` now introduced in lesson 10, where a reflexive verb is actually taught; the only remaining dud is C2 (45 words vs 30 drilled, unannounced). |
| 2 | Lesson UX & content rendering | 15 | 10 | All 24 lessons / 195 steps render; stepper, audio, links all work; 0 console errors; scramble tokens are now bare words (BUG-10 verified fixed). |
| 3 | Exercise engine correctness | 20 | 9 | Grading matches the stored answer, feedback is staged, no answer leaks, hints never reveal; only by-design limits (speaking ungraded). Unchanged by this revision — nothing in the engine was reported broken. |
| 4 | Navigation, links, buttons | 10 | 9 | 1195/1195 lesson-page links → 200; every nav item resolves; small nit unchanged: the sidebar still duplicates the bottom nav in the DOM. |
| 5 | Persian/RTL + German/LTR | 10 | 10 | 392 German elements on lesson 1, all `dir="ltr"`; the one unmarked German word on `/exam/` (BUG-04) is now `<span lang="de" dir="ltr">ankreuzen</span>` — verified live. |
| 6 | Visual consistency & theming | 5 | 8 | Both themes verified, `meta theme-color` follows the token, no-flash verified by construction (script before CSS), not measured on a real paint (unchanged). |
| 7 | Mobile / responsive | 10 | 9 | 390px inside a same-origin iframe: 0 px horizontal overflow on 14 pages, bottom nav appears, sidebar hides, forms usable (unchanged). |
| 8 | Accessibility (basics) | 5 | 9 | One `h1` per page, no heading jumps, every input labelled, 320px-wide inputs and 53px buttons on mobile, 3px visible focus ring; the five credential inputs now carry `autocomplete` (WCAG 1.3.5 — BUG-12 fixed); still no contrast-tool audit. |
| 9 | Error handling & edge cases | 5 | 9 | 404/405/403/400 all clean Persian pages, junk input never 500s; both reported defects — the English validator message and the spurious "passwords differ" error — are fixed and verified on all three failing-password cases. |
| 10 | Trust signals for the Ausbildung portfolio | 5 | 9 | No debug leaks, all audio real and seekable, honest claims; the goal form's false promise is gone (verified in the DB) and `validate_a1_content` is green; the one honesty gap left is C2 (the unannounced 15 review-queue words in lesson 1). |

Weighted average 9.35 → **94/100 (A)**. (First revision: 8.75 → 88/100 — B. Rounding follows the rubric: weighted average ×10, half-up as before: 9.35 → 93.5 → 94.)

> **Would I show this to a German trainer?** Yes, and I would walk them through a lesson and the exam rather than the account pages. The lesson flow and the exam are the parts that read as professional: the grammar is explained the way a teacher explains it, the exercises teach rather than quiz, and the exam page says out loud what it does not reproduce ("پرسش‌ها تمرین‌های خودِ همین دوره‌اند، نه برگهٔ رسمی گوته"). The two things that had to be fixed before a demo are fixed: the goal form now keeps its own promise (all-empty really clears the goal, and a date is stored only if chosen), and the password message is Persian — nothing on the site now contradicts itself in front of a trainer.

---

## 2. Top 10 things to fix (ranked by impact)

> **Post-fix revision:** this is the first revision's ranked list, kept in order as the record of what was wrong. The status tag after each ID records what this revision verified; the description below it states the state as found, and the "Fix:" sentence is the fix that was applied by the owner. Only the two NOTEs are unchanged, and both are documentation notes rather than defects.

1. **BUG-01 (MAJOR) — ✅ FIXED (verified live + in the database)** — `/accounts/goal/`: the three Jalali date menus have **no empty option**, so the form can never submit an empty date. Saving an untouched form (the documented "clear the goal" action) stores **۱ فروردین ۱۴۰۵** (a past date the learner never chose). Fix: add a blank choice (`("", "انتخاب نشده")`) to `target_year`/`target_month`/`target_day` so "empty" can actually be empty.
2. **BUG-02 (MAJOR) — ✅ FIXED (verified live)** — `/accounts/signup/`: typing a short password prints **`This password is too short. It must contain at least 8 characters.`** — raw framework English inside a Persian form. Fix: give `MinimumLengthValidator` a Persian message in `AUTH_PASSWORD_VALIDATORS`.
3. **BUG-03 (MAJOR) — ✅ FIXED (verified live)** — `/accounts/signup/`: when `password1` fails validation, `password2` **always** also reports «دو گذرواژه یکسان نیستند.» even when both boxes hold the same text. Fix: skip the comparison when `password1` is not in `cleaned_data`.
4. **BUG-05 (MINOR) — ✅ FIXED (verified live)** — the username field accepts Persian digits (`کاربر۱۲۳`) and `<script>alert(1)</script>` although the help text promises only `حروف انگلیسی، رقم و نویسه‌های @ . + - _`. Output is escaped (no XSS), but the promise is not enforced. Fix: a `RegexValidator` matching the help text.
5. **BUG-06 (MINOR) — ✅ FIXED (verified live)** — a 100-character username is accepted and created with no maximum shown in the UI (field max is 150).
6. **BUG-07 (MINOR) — ✅ FIXED (verified via CLI)** — `validate_a1_content` fails: 9 «article/gender mismatch» rows, all plural-only nouns (`die Eltern`, `die Ferien`, `die Geschwister`, `die Großeltern`, `die Lebensmittel`, `die Leute`, `die Möbel`, `die Papiere`, `die Pommes frites`). The data is right and the **check** is wrong (a Pluraletantum has no gender) — but a repo whose own health check is red reads badly. Fix: teach the validator about plural-only nouns.
7. **BUG-04 (MINOR) — ✅ FIXED (verified live)** — `/exam/`: the paragraph `کسی که «ankreuzen» را نفهمد…` quotes German without `lang="de" dir="ltr"`, while the word list right below it marks the same word correctly.
8. **BUG-10 (MINOR) — ✅ FIXED (verified live)** — scramble drills show punctuation inside the tokens (`danke.`, `gut,`, `heißt`); a word-order drill is easier to read if the token is the bare word and punctuation is added in the target sentence.
9. **BUG-11 (WEAKNESS) — ✅ FIXED (verified in the database)** — `/lessons/1/`: `sich` ("خود (ضمیر انعکاسی)") is published as a new lesson-1 word although no reflexive verb is taught anywhere near it.
10. **BUG-09 (NOTE) — ℹ️ UNCHANGED (by design)** — `/lessons/progress/import/` and `/lessons/1/progress/` are POST-only endpoints (GET → 405, and 403 for a guest on import). Correct, but a documenter following the page map will call it broken; one sentence in `AGENTS.md` would prevent that.

**Also re-verified in this revision:** **BUG-12 (WEAKNESS) — ✅ FIXED** — all five credential inputs now carry `autocomplete` (`username`, `email`, `new-password` ×2, `current-password`), seen in the rendered HTML. **BUG-08 (NOTE) — ℹ️ UNCHANGED** — `/vocabulary/lookup/` without `?q=` still returns `400 {"error": "missing query parameter"}`; that is the AJAX contract, not a defect.

---

## 3. What is genuinely good

- **The lesson journey works end to end.** 24/24 lessons walked, 195 steps visited by clicking the real step chips; the stepper moves (`1 / 8 → 2 / 8 → 1 / 8`), nothing is hidden, nothing is empty, and the JS-off fallback (all steps rendered as one document) is real.
- **Content that a teacher would approve of.** `content-lessons-1-12-24.txt` shows correct German, Persian that sounds like a person, and grammar ordered the way it must be: `sein` → regular verbs → verb-second → negation (`nicht`/`kein`) → separable verbs → accusative → dative prepositions → Perfekt → modals → subordinate clauses. Lesson 12's «اشتباه‌های رایج فارسی‌زبانان» (`Ich bin 20 Jahre` → `Ich bin 20 Jahre alt`) is the best single page in the product.
- **Honesty as a design trait.** The exam page names its source and its limits; the runner says where answers go and hides the controls when JS is off; `/exam/sprechen/` refuses to invent a speaking score; `/readiness/` says its numbers come only from real work.
- **The answer is really never on the page.** Verified per type: typed/order answers absent from the HTML, all `data-flag` spans hidden before submission, no `is_correct` token in exercise or exam HTML; the correct option is only revealed by the server response after a miss.
- **Audio is complete and seekable.** 1123 audio URLs referenced by lessons → all 200; `Range: bytes=0-1023` → `206` with `Content-Range` on every sample; a grammar clip played (`currentTime 2.31s`, `paused:false`) and seeked (`13.35s → 14.0s`).
- **Light pages.** 52–93 KB, 8–12 requests, `load` 68–134 ms, 149–2159 DOM nodes on the pages measured (`perf-a11y.json`).
- **Ownership isolation on the exam.** Other learners' runs (`/exam/runs/3/`, `/6/`, `/7/`, `/8/`) return 404 to a different signed-in user.
- **Badges are earned, not decorated.** `/lessons/today/` showed no badge before lesson 1 was completed and «اولین درس» after — no grey locked wall, exactly as the project rule requires.

---

## 4. Teacher review

Read as a Goethe A1 examiner looking at a portfolio, with a deep read of lesson 1 (first), lesson 12 (the review lesson) and lesson 24 (largest vocabulary load: 148 new words), plus the grammar catalogue, the Perfekt auxiliaries of all verbs, the Wortliste report and the exercise audit.

**Does it teach A1, or show words?** It teaches. Every lesson is a shape, not a list: intro → agenda → lead → vocabulary → grammar → examples → dialogue → reading/listening → practice → finish, and each material step is justified by content that exists (`lessons/journey.py`). Grammar is not decoration: lesson 1 already reaches the verb-second rule and the `du`/`Sie` distinction, lesson 12 consolidates with a reading text, lesson 19 does Perfekt, and lesson 24 puts the whole level in three tables. The 392 German elements on a lesson page are all marked `lang="de" dir="ltr"`.

**Is the German correct?** In everything I read, yes: capitalisation of nouns, Umlauts, `der/die/das`, plurals (`der Morgen → die Morgen`, `das Bad → die Bäder`, `der Euro → die Euros`), `Perfekt` auxiliaries (all 39 `SEIN` verbs are movement/change-of-state/stative: `gehen`, `sterben`, `werden`, `unterwegs sein`, `zu sein` — no errors), word order (`Morgen trinke ich Kaffee.`, `Ich stehe um sieben Uhr auf.`), and the politeness register (`Wie bitte?`, `Gern geschehen`, `Sie` capitalised). I found no wrong German.

**Are the Persian translations natural?** They read like a Persian teacher wrote them, not a machine: «شب بخیر (هنگام ورود)» vs «شب بخیر (هنگام خواب)» for `Guten Abend`/`Gute Nacht`, «او (مؤنث)؛ آن‌ها» for `sie`, «چرا (پاسخ مثبت به سؤال منفی)» for `doch`. The register explanations («با دوست … du می‌گوییم؛ با غریبه‌ها … Sie») are the kind of note only a person who has taught Persian speakers writes.

**Vocabulary.** 626 of 628 official A1 Wortliste main entries covered (99.7%), verified with the project's own read-only `report_a1_wortliste`; 392 course words are taught beyond the list, which the report itself labels informational. Duplicates: none found in the sampled lessons; `Word` identity is `(word, word_type)` and the drill generator counts a word as covered only if a *written* question exists, so near-duplicates are hard to create by accident. Level fit: nearly everything is A1; the reference bank in lesson 24 (`der Sonnabend`, `das Apartment`, `das Geburtsjahr`) is deliberately a bank, and the page says so.

**Do the exercises teach the right skill?** Recognition and production are separated properly. Choice drills (meaning, article, plural, Perfekt) train recognition; `TRANSLATION`, `SCRAMBLE`, dictation and the writing drills train production, and the writing drills accept the answer **without** the article, matching the authored translation questions. `audit_a1_exercises` reports zero problems across 586 exercises / 3504 questions (no missing answers, no duplicate options, no answer-in-prompt, no empty text). The ramp is sensible: lesson 1 asks 4-question multiple choice; lesson 19 asks Perfekt and separable-verb questions; the mystery is that lesson 1's intro calls its vocabulary 45 words while the drills cap at 30 — the remaining words stay reachable in the review queue, which the lesson load report (`report_a1_lesson_load`) explicitly shows.

**Audio.** I cannot judge pronunciation quality — I will not pretend otherwise. What I measured: every referenced clip exists, returns 200, and supports `Range` (206), and a grammar clip plays and seeks in the browser. Which item a clip belongs to matches the exercise: listening questions reference sentence-level MP3s, minimal-pair drills reference the word's own MP3, dictation references the word's MP3, and words without audio are skipped rather than given a silent player.

**Exam.** `/exam/` mirrors the real format: HÖREN 20 min / LESEN 25 / SCHREIBEN 20 / SPRECHEN 15, 15 items each, raw × 1.66, written max 75 + spoken 25 = 100, pass 60, written minimum 35 — and it quotes the Durchführungsbestimmungen as its source. It is honest about what it cannot reproduce (task types and the human marking of SCHREIBEN/SPRECHEN) on the page itself. Speaking practice promises no score and delivers a rehearsal.

**Content problem table**

| # | Severity | Where | What | Evidence |
|---|---|---|---|---|
| C1 | WEAKNESS → ✅ FIXED | `/lessons/1/` | `sich` was published as a lesson-1 new word with no reflexive verb near it. Now it is a lesson-10 new word — the first lesson that conjugates `sich anziehen` / `sich ausziehen`; the live DB row is `(lesson 10, NEW)`. | this revision's live check |
| C2 | WEAKNESS | `/lessons/1/` vocabulary step | 45 words in the step, 30 drilled; the intro does not tell the learner that 15 of them are only in the review queue. | `report_a1_lesson_load` vs lesson 1 step |
| C3 | MINOR → ✅ FIXED | `/exercises/5500/` (scramble) | Tokens carried punctuation (`danke.`, `gut,`); they are now bare words (`danke`, `gut`, `Auch`, `heißt`…), verified on the live page. | this revision's live check + `exercise-sample.json` |
| C4 | NOTE | `/lessons/12/` | `das Essen \| plural=die Essen` — the plural is rare/colloquial; harmless but a picky trainer may blink. | `content-lessons-1-12-24.txt` |
| C5 | NOTE → ✅ FIXED | content health | The 9 plural-only nouns are no longer a FAIL; `validate_a1_content` reports them as an informational note and **all checks pass**. | this revision's CLI run |

---

## 5. Learner walkthrough log (Phase 2)

> **Post-fix revision:** this is the first revision's walkthrough, kept as the chronological record. The two places it ran into defects (the 100-character signup at step 2 and the goal date at step 4) are fixed and re-verified — see §10 for the per-issue status.

1. **Land on `/` as a guest** — Persian, RTL, one `h1`, "خوش آمدی" only after login; as a guest the dashboard still explains the product (1959 chars of text) and every nav item is reachable except the ones that need an account. No broken element, no console error. Impression: it is obvious what this is and what to do first.
2. **Sign up** at `/accounts/signup/` — four fields, Persian labels, the username rule and the password rule visible *before* typing. Submitting empty gives three Persian «این فیلد لازم است.» and keeps what I typed. On success you land on the onboarding goal step with «✓ حساب شما ساخته شد. خوش آمدید!» and an already logged-in header. The 100-character username case came back **accepted**, which logged me in and dropped me on `/accounts/goal/?onboarding=1` — that was the moment I noticed the username promise is not enforced (BUG-05/06). Screenshots: `20-signup-desktop-light.png`, `21-signup-errors-desktop.png`.
3. **Onboarding goal step** — the framing ("قدم ۱ از ۲ · هدف تو") is clear and says every field is optional. I set A2 + آوسبیلدونگ + a date, saved, and landed on `/readiness/` with «✓ هدفت ذخیره شد.» and the honest line «هدفت A2 است، ولی محتوای ساخته‌شده فعلاً تا A1 است.» Reloading the goal page showed my answers still there.
4. **Then I emptied the goal** — and this is where the site contradicted itself: the form says leaving everything empty clears the goal, but the three date menus cannot be emptied, and after saving I had a target date of **۱ فروردین ۱۴۰۵** I never picked (BUG-01). On a fresh account the menus default to ۱۴۰۵/فروردین/۱. Screenshot: `26-goal-desktop-light.png`, `29-goal-desktop-dark.png`.
5. **`/lessons/today/`** — one node per skill, one clear active node, "شروع روز" reachable in one click. As a brand-new account there were **no badges**, which is the honest behaviour the project promises.
6. **Lesson 1 end to end** — read every step, played clips, clicked next/prev, then «درس را کامل کردم» → the button becomes «کاملشده» and the eyebrow changes to «درس را کامل کردی». Back on `/lessons/today/`, «اولین درس» had appeared. Nothing about the flow confused me; the only friction was wanting to jump straight to practice and having to notice the agenda links (which do work).
7. **Wrong answers on purpose** — first miss holds the answer back («یک بار دیگر تلاش کن — این بار با دقت بیشتر.»), second miss reveals «پاسخ درست: سلام» plus a word card with the article, plural, pronunciation and meaning. That is the teaching moment the design promises and it lands.
8. **Hints** — after misses the راهنما button appears; the text came back as «گزینهٔ درست این شکل است: س _ ا _» (strength 2) and does **not** contain the answer (`hintLeaksAnswer: []`).
9. **Review queue** — before: a generic explanation. After missing `hallo` twice: the queue lists `hallo` with the four exercises that test it. The claim "this list is built from your own answers" is literally true.
10. **Exam** — index → run: 45 questions, sections in order, a server countdown ticking (64:59 → 63:24), answer, «پایان آزمون و ثبت نتیجه» asks «آزمون تمام شود و نتیجه ثبت شود؟» and then shows a real report (`0 پاسخ درست از 45 پرسش · 2 پرسش پاسخ داده شد`, per section HÖREN 2 از 15, and the 35-point written rule). After the end, a new answer is refused with `{"error": "exam is finished"}`. Impression: this is the most convincing part of the site.
11. **Come back to `/readiness/` after real work** — the page is still "ساختشده از کارهایی که واقعاً انجام دادهای" and now reflects it. It never showed me a fabricated number during the whole walkthrough.

**Console/network while walking:** zero `pageerror` anywhere; the only failed requests are the deliberately-returned 404/405/403/400 statuses listed in §13.

---

## 5b. Accounts & forms audit (signup / login / goal / profile / theme)

### Field inventory (from the rendered page, `accounts-audit.json`)

| Form | Fields found (id / label) | `required` | `help_text` visible | `autocomplete` | Direction |
|---|---|---|---|---|---|
| Signup | `id_username` / «نام کاربری» | yes | «حروف انگلیسی، رقم و نویسه‌های @ . + - _ · حداکثر 30 نویسه» | `username` | label RTL, input LTR-ish (no explicit `dir`) |
| | `id_email` / «ایمیل (اختیاری)» | no | — | `email` | — |
| | `id_password1` / «گذرواژه» | yes | «حداقل ۸ نویسه؛ نه بسیار ساده و نه فقط عدد.» | `new-password` | — |
| | `id_password2` / «تکرار گذرواژه» | yes | — | `new-password` | — |
| Login | `id_username`, `id_password` / «نام کاربری», «گذرواژه» | yes | — | `username` / `current-password` | — |
| Goal | `current_level`, `target_level`, `reason`, `target_year`, `target_month`, `target_day` — Persian labels, `empty_label` «هنوز نمی‌دانم» / «فعلاً هدفی تعیین نکرده‌ام» / «انتخاب نشده» | no | date hint present | n/a | RTL; Persian digit labels, Latin submitted values |

Submit button: signup «ساخت حساب», login «ورود», goal «ذخیرهٔ هدف» / «ذخیره و دیدن برنامه» — all 320 px wide, 53 px tall, in the viewport at 390 px.

**Could a first-time Persian speaker fill this form without guessing?** For **signup and login: yes** — every field has a real `<label>` (not a placeholder), both guidance texts are rendered before you fail, the optional email is labelled as optional, and the errors appear next to the field that caused them, in Persian, with my input preserved. For the **goal form: yes, now** — the three date menus open on «انتخاب نشده» and an all-empty save really clears the goal (verified in the database); a half-filled date is still caught with «تاریخ هدف را کامل انتخاب کن: سال، ماه و روز.». This was the one form the first revision could not call fillable-without-guessing.

### Validation cases (each one submitted for real)

| Case | Input | Message shown | Verdict |
|---|---|---|---|
| empty submit | all empty | «این فیلد لازم است.» ×3 (username, password1, password2) | good |
| whitespace only | `"   "` | «این فیلد لازم است.» (username kept as typed) | good |
| bad email | `not-an-email` | «یک ایمیل آدرس معتبر وارد کنید.» | good |
| short password | `abc` / `abc` | password1: «گذرواژه باید حداقل ۸ نویسه باشد.» · password2: **no error** | ✅ fixed (BUG-02, BUG-03) |
| digits only | `12345678` | password1: «این رمز عبور بسیار رایج است.» · password2: **no error** | ✅ fixed (spurious second error gone; re-verified) |
| common password | `password` | password1: «این رمز عبور بسیار رایج است.» · password2: **no error** | ✅ fixed (spurious second error gone; re-verified) |
| mismatched confirmation | `AuditPass-2026!` / `OtherPass-2026!` | password2: «دو گذرواژه یکسان نیستند.» | good |
| 100-char username | `u`×100 | **refused**: «نام کاربری نباید بیشتر از 30 نویسه باشد.» | ✅ fixed (BUG-06) |
| Persian digits in username | `کاربر۱۲۳` | **rejected**: «نام کاربری فقط می‌تواند شامل حروف انگلیسی، رقم و نویسه‌های @ . + - _ باشد.» | ✅ fixed (BUG-05) |
| `<script>` in username | `<script>alert(1)</script>` | **rejected** with the same charset message (the value is echoed escaped) | ✅ fixed (BUG-05); no XSS either way |
| 2-char username | `ab` | «نام کاربری باید حداقل 3 نویسه باشد.» | good |
| duplicate username | `audit-tester` | «این نام کاربری قبلاً استفاده شده است.» next to the field | good |
| duplicate email | `audit@example.com` (already used by `audit-tester`) | **accepted, account created** — email is optional and not unique | NOTE |
| login, unknown user | `no-such-user-xyz` | «نام کاربری یا گذرواژه درست نیست.» | good |
| login, wrong password | `audit-tester` / wrong | **exactly the same message** | good (no user enumeration) |
| login, empty | — | «این فیلد لازم است.» ×2 | good |
| goal, target below current | current A2, target A1 | no error (the form allows it; the cross-field rule needs both set) | NOTE |
| goal, empty submit | nothing touched | **no error; the goal is stored empty** — `target_date=None`, no levels, no reason (checked straight in the DB) — and the menus reopen blank | ✅ fixed (BUG-01) |
| goal, partial date | year only | «تاریخ هدف را کامل انتخاب کن: سال، ماه و روز.» | ✅ good (now reachable, and caught) |

Other form findings:

- **No framework English anywhere**: the minimum-length message was the one exception and is now Persian (`accounts/validators.py`, re-verified on the live form); the other three Django validators already resolve to Persian through the catalog.
- **No leaks**: no stack trace, no settings, no template error on any form failure.
- **Keyboard**: Tab order follows the visible order (agenda links → step content → controls); focus is visible everywhere (3px solid accent outline); the forms are ordinary `POST` forms with `novalidate` and server-side errors, so Enter submits.
- **Password managers**: fixed — all five credential inputs carry `autocomplete` (`username`, `email`, `new-password` ×2 on signup; `username`, `current-password` on login), read from the rendered HTML in this revision.
- **After signup** (verified with a brand-new account `audit-welcome`): you land on `/accounts/goal/?onboarding=1`, the nav switches to the logged-in state (account link + logout form), and a success message is shown: «✓ حساب شما ساخته شد. خوش آمدید!». The next step is spelled out on the page as «قدم ۱ از ۲ · هدف تو».
- **Logout** is a POST form in the sidebar/account menu (this is also why a `button[type=submit]` click on `/accounts/goal/` hits logout first — a real trap for the next auditor, not a bug). Clicking it lands on `/accounts/login/` with «✓ با موفقیت خارج شدی.».
- **Profile**: no `None`, no `undefined`, no unexplained zeros; all edit links resolve (`/readiness/`, `/accounts/goal/`, `/`).
- **Theme** (`/accounts/theme/`, POST only): `dark` → `data-theme-mode="dark"`, `data-theme="dark"`, `meta theme-color = #0f1116`; `light` → `#fff8f2`; `system` → follows the OS. The switch persists across reloads (it lives on the profile, not localStorage). No-flash verified by construction: the inline resolver script sits in `<head>` before the stylesheets and reads `data-theme-mode`; I did not capture a real first paint to prove the absence of a flash frame.
- **Dark mode re-check**: signup, goal, login, profile all re-screenshotted in dark (`28-signup-desktop-dark.png`, `29-goal-desktop-dark.png`) — contrast on labels, hints and error text holds.
- **Mobile 390 px** (same-origin iframe; the site sends `X-Frame-Options: SAMEORIGIN`, so a same-origin parent is required): each form shows 4 (signup) / 2 (login) labelled fields, help texts visible, errors Persian and visible with the fields, submit button in the viewport, 0 px horizontal overflow. Screenshots: `signup-mobile.png`, `signup-error-mobile.png`, `login-mobile.png`, `login-error-mobile.png`, `goal-mobile.png`.

---

## 6. Lesson-by-lesson table (all lessons)

Every published lesson was opened and every step visited by clicking its chip; the stepper next/prev buttons were clicked on each lesson; every link on every lesson page was resolved with an HTTP request. `Buttons` = distinct button labels/texts seen across the lesson's steps; `Audio` = `<audio>` elements present.

| Lesson | Steps | Buttons | Links | Audio | Issues | Score |
|---|---|---|---|---|---|---|
| 1 Hallo! Begrüßung | 8 | 50 | 70 | 51 | C2 45 words vs 30 drilled (C1 `sich` fixed — now lesson 10) | 9 |
| 2 | 8 | 50 | 70 | 49 | — | 10 |
| 3 Zahlen, Alphabet | 8 | 49 | 70 | 48 | — | 10 |
| 4 Familie und Personen | 8 | 52 | 76 | 51 | — | 10 |
| 5 Beruf und Arbeit | 8 | 48 | 70 | 47 | — | 10 |
| 6 Tagesablauf und Uhrzeit | 8 | 50 | 68 | 49 | — | 10 |
| 7 Essen und Trinken | 8 | 47 | 67 | 46 | — | 10 |
| 8 Im Restaurant und im Café | 8 | 48 | 70 | 47 | — | 10 |
| 9 Einkaufen und Preise | 8 | 48 | 67 | 47 | — | 10 |
| 10 Kleidung und Farben | 8 | 49 | 69 | 48 | — | 10 |
| 11 Wohnen und Möbel | 8 | 51 | 70 | 50 | — | 10 |
| 12 Wiederholung A1.1 | 8 | 49 | 57 | 48 | C4 `die Essen` plural (NOTE) | 9 |
| 13 Freizeit und Hobbys | 8 | 50 | 70 | 49 | — | 10 |
| 14 Wetter und Jahreszeiten | 8 | 48 | 70 | 47 | — | 10 |
| 15 Sport, Verabredungen | 8 | 50 | 70 | 49 | — | 10 |
| 16 Orientierung in der Stadt | 8 | 49 | 70 | 48 | — | 10 |
| 17 Reisen, Verkehr und Hotel | 8 | 48 | 70 | 47 | — | 10 |
| 18 | 8 | 50 | 70 | 49 | — | 10 |
| 19 Gestern und heute: Perfekt | 9 | 51 | 74 | 50 | — | 10 |
| 20 Feste, Feiern, Glückwünsche | 9 | 50 | 72 | 49 | — | 10 |
| 21 Telefonieren, E-Mail, Post | 9 | 49 | 72 | 48 | — | 10 |
| 22 Schule, Lernen, Prüfungen | 8 | 51 | 70 | 50 | — | 10 |
| 23 | 8 | 49 | 70 | 48 | — | 10 |
| 24 Abschluss A1 + Wortschatz-Bank | 8 | 59 | 69 | 58 | — | 10 |

Totals: **24 lessons, 195 steps, 1195 distinct page links (all 200), 1123 audio clips, 0 console errors, 0 hygiene hits** (`null`, `None`, `{{`, `TODO`, `lorem`, `undefined`), 0 German elements missing `dir="ltr"`. Screenshots: `01-lesson-1-desktop.png` … `24-lesson-24-desktop.png`, plus `32-lesson1-finish-desktop.png`, `33-lesson1-check-desktop.png`.

Per-lesson sub-pages: `/lessons/<pk>/progress/` (POST-only → 405 on GET, by design), `/lessons/<pk>/review/` (renders, 200), `/lessons/<pk>/check/` (renders, 200, screenshot `33-…`).

---

## 7. Exercise & exam audit

One representative exercise per type, answered **correctly all the way to the results screen**, then a second pass answering **wrong twice** to watch the staged reveal, then the API edge cases.

| Type | Instances checked | Correct run | Wrong ×2 | Rendering | Issues |
|---|---|---|---|---|---|
| MULTIPLE_CHOICE (`/exercises/21/`) | 1 ex / 4 q | 4 از 4, دقت ۱۰۰٪, «همهٔ پاسخ‌ها درست بود.» | second-try note, then «پاسخ درست: سلام» + word card | options LTR, flags hidden before submit | — |
| TRANSLATION (`/exercises/22/`) | 1 ex / 2 q | 2 از 2 | reveal works | input `lang="de" dir="ltr"` | — |
| FILL_BLANK (`/exercises/23/`) | 1 ex / 2 q | 2 از 2 | reveal works | — | — |
| READING (`/exercises/24/`) | 1 ex / 3 q | 3 از 3 | reveal works | German passage rendered above the prompt, LTR | — |
| TRUE_FALSE (`/exercises/25/`) | 1 ex / 2 q | 2 از 2 | reveal works | — | — |
| LISTENING (`/exercises/3500/`) | 1 ex / 4 q | 4 از 4 | reveal works | audio control present, MP3 200/206 | — |
| SCRAMBLE (`/exercises/5500/`) | 1 ex / 4 of 10 q | running 4 correct answers gave 4 correct | reveal shows the sentence | tokens shuffled, answer not on the page, tokens now bare words | — (C3 fixed, verified live) |
| chat (`/exercises/chat/21/`) | 1 | n/a (ungraded by design) | n/a | 11 conversation turns, page states it is not graded | — |
| dialogue (`/exercises/dialogue/21/`) | 1 | n/a | n/a | 11 turns, links back to the chat framing | — |
| session (`/exercises/session/`) | 1 | 15 questions from one lesson | answered 3, feedback shown | — | — |

**Answer-leak check (the project's non-negotiable rule).** For every typed/order question of the sampled exercises the correct answer is absent from the initial HTML; for choice questions every `data-flag` span is `hidden` before submission and no `is_correct`/`data-correct` token appears anywhere; on the exam paper (45 questions) `is_correct` is absent and all **240** flag spans are hidden; the correct option is only sent in the JSON response after a submission. `typedAnswerLeaks: []` for all seven types.

**Option shuffle.** Reloading the same exercise keeps the option order (seed = question pk) and grading uses the option id, not the position — verified by comparing radio values across reloads (`optionOrderStable: true`).

**Hints.** Guest → `403 {"error": "no account"}` (documented). Signed in after two misses → `200` with strength 2 and a masked form («س _ ا _»); the answer is not in the hint, and the following correct/incorrect submission still works.

**Word-progress side effects.** Missing `hallo` twice moved it into `/vocabulary/review/` with the four exercises that test it; the word card appeared on the second miss. (The project's rule that pronunciation drills do *not* label a word failure is enforced in code — no `QuestionTarget` for those drills — and I saw no pronunciation drill in the review queue.)

**Adversarial tests (all run against every sampled exercise)**

| Test | Expected | Actual |
|---|---|---|
| `GET /exercises/<pk>/submit/` | 405 | 405 (×7) |
| `POST` empty body / `{}` | 400 or a graded empty answer | 400 `unknown question` (no question id) / graded wrong with `correct:false` |
| whitespace-only typed answer | graded wrong, no 500 | wrong, word card shown |
| 5000-character answer | rejected or graded, no 500 | 200, graded wrong |
| Persian digits / emoji / `<script>` text | graded wrong, escaped | graded wrong, echoed escaped in JSON and HTML |
| malformed JSON body | 400 | 400 `{"error": "invalid JSON"}` |
| unknown question id | 400 | 400 `{"error": "unknown question"}` |
| unknown option id | 400 | 400 |
| double submit of one answer | two graded rows, no 500 | 200 both times, history grows (by design) |
| entity that does not exist (`/exercises/999999/`) | 404 | 404 |
| hint without a question id | 400 | 400 |
| exam: `GET …/submit/` | 405 | 405 |
| exam: submit after the run finished | refused | 400 `{"error": "exam is finished"}` |
| exam: another user's run | 404 | 404 (runs 3, 6, 7, 8) |
| exam: finish twice | refused | 403 |

**Exam arithmetic check.** On the finished run the report read `0 پاسخ درست از 45 پرسش · 2 پرسش پاسخ داده شد`, «0 از 75» written, HÖREN 2 از 15 answered / 0 correct, and explained the 35-point written minimum («حتی 25 امتیاز کامل بخش گفتن هم به 60 نمی‌رساند»). That matches `exams/spec.py` (45 items × 1.66 → 75 written + 25 spoken = 100, pass 60).

**What I did not run in the exam:** I did not sit the full 65-minute clock out, so the *timer-expiry* refusal was verified by the finished-run refusal plus `time_is_up(run)` reading in `exams/views.py`, not by waiting for a real timeout. The paper I ran contained the real 45 questions and the real server deadline; only the expiry moment itself is untested.

---

## 8. Cross-cutting findings

- **Navigation / IA.** Sidebar (desktop), app bar, bottom nav (≤899 px), account menu, brand link all resolve to 200 (`crawl-guest.json`). Active state is set with `aria-current` on the current step and the current nav item; I did not find a nav item that lands on the wrong page. Nit: the sidebar markup is present in the DOM at 390 px (hidden by CSS) — harmless but it doubles the nav markup in the page.
- **RTL / LTR.** `<html lang="fa" dir="rtl">` on every page. Lesson 1 alone has 392 `lang="de"` elements; **all** carry `dir="ltr"`. Mixed Persian sentences with German words render with correct punctuation order in the samples I read. The one exception found in the first revision — the `/exam/` paragraph quoting «ankreuzen» — is fixed: it now renders as `<span lang="de" dir="ltr">ankreuzen</span>` (verified live).
- **Theme.** Light and dark both verified on home, lesson, exercise, words, exam, today, signup, login, goal, profile. `meta theme-color` is written from the `--bg` token (`#fff8f2` light / `#0f1116` dark). The resolver script is inline in `<head>` before any stylesheet, so the wrong theme cannot paint first; the `/accounts/theme/` choice is stored on the profile, not in localStorage, and survives reload.
- **Error pages.** 404 (`/this-page-does-not-exist/`, `/lessons/999999/`, `/vocabulary/words/999999/`, `/exercises/999999/`) → the Persian 404 template with working "بازگشت به داشبورد" and «مسیر یادگیری» links, 364 characters of body, no stack trace. 405 (`GET /accounts/theme/`, `GET /exercises/<pk>/submit/`, `GET /lessons/1/progress/`) → «این آدرس با این روش باز نمی‌شود». 403 for a guest on `/lessons/progress/import/`. 400 for malformed API calls. A paginated page out of range (`/vocabulary/words/?page=999999`) returns 200 with the last page instead of an error — graceful. The 500 template was inspected, not triggered (see limitations).
- **Accessibility basics.** One `h1` per page, no heading-level jumps, every input has a `<label for>`, no `<img>` without `alt` (there are almost no images), every `<button>` has text or an `aria-label`, audio elements carry `controls` and an `aria-label`, a skip link exists, the stepper is keyboard-operable, and Tab produces a visible 3px outline on every stop I sampled. Progress bars carry `role="progressbar"` with `aria-valuenow`.
- **Performance sanity.** Home 73 KB / 10 requests / DOMContentLoaded 260 ms; lesson 1 93 KB / 12 requests / 121 ms / 2159 nodes; exercise 91 KB / 9 requests / 91 ms; word book 53 KB / 8 / 105 ms; exam 54 KB / 8 / 133 ms; today 52 KB / 8 / 68 ms (dev server, localhost, mirror data). No asset is obviously oversized; the biggest single item is the 138 KB lesson HTML.
- **Console health.** Zero `pageerror` everywhere. The only console lines are "Failed to load resource" for statuses the app returns on purpose: 404 (`/this-page-does-not-exist/`), 405 (`GET /accounts/theme/`, `GET /lessons/1/progress/`, `GET /lessons/progress/import/`, `GET /exercises/21/submit/`), 403 (`/lessons/progress/import/` as a guest, `/exercises/21/hint/` as a guest), 400 (`/vocabulary/lookup/` without `?q=`).
- **Content hygiene sweep.** For `TODO`, `Lorem`, `lorem`, `foo`, `undefined`, `None`, `null`, `{{`, `}}`, `بزودی`, `placeholder`: no hits on any page. The single `null` match on `/` is the course title «Von null bis A1». No mojibake, no raw template leftovers.
- **Draft invisibility.** Cannot be tested positively: this database contains **no** unpublished lesson, exercise, word or course. Every learner-facing queryset I read filters `is_published=True`, and the "does not exist" paths return 404 — but that is code inspection, not a live test (limitation).
- **Resilience.** I killed the server mid-audit (curl → connection refused) and restarted it; home, a lesson and a media file all answered 200 immediately afterwards, and the walk continued.
- **Mirror safety.** Every command used `.venv/bin/python`; no `migrate`, no seed, no import, no delete. The only writes are the rows the app itself creates when a visitor signs up, answers a question, finishes a lesson or starts an exam run.

---

## 9. Mobile (390×844) findings

Method: a same-origin parent page (`http://127.0.0.1:8000/accounts/profile/`) with an `<iframe>` sized to 390×844, then measured **inside** the frame (`window.innerWidth === 390` on every page). The iframe method is required by the project because Chrome will not shrink a window below ~500 px; it works here because the site sends `X-Frame-Options: SAMEORIGIN` (a cross-origin/`about:blank` parent is blocked — which is what my first attempt showed).

| Page | innerWidth | document scrollWidth | Overflow | Sidebar visible | Bottom nav |
|---|---|---|---|---|---|
| home | 390 | 390 | 0 | no | yes |
| today | 390 | 390 | 0 | no | yes |
| lessons list | 390 | 390 | 0 | no | yes |
| lesson 1 | 390 | 390 | 0 | no | yes |
| exercise 21 | 390 | 390 | 0 | no | yes |
| exercise 5500 | 390 | 390 | 0 | no | yes |
| exam index | 390 | 390 | 0 | no | yes |
| words | 390 | 390 | 0 | no | yes |
| review | 390 | 390 | 0 | no | yes |
| profile | 390 | 390 | 0 | no | yes |
| signup | 390 | 390 | 0 | no | yes |
| goal | 390 | 390 | 0 | no | yes |
| readiness | 390 | 390 | 0 | no | yes |
| login | 390 | 390 | 0 | no | yes |

- **Breakpoint:** sidebar layout above 900 px, app bar + bottom nav at 390 px — the switch is where the project says it is; I saw no intermediate width misbehave (the 500–899 band is the one I sampled least).
- **Tap targets:** e.g. «شروع روز» 92×53, form submit 320×53, login/exit buttons 53×44 (≥44 px). Hidden controls report 0×0, which is correct.
- **Long German / long Persian text:** no element wider than the viewport on any page (`wideElements: []`), so nothing clips; the wide-element scan covers every descendant of `body`.
- **Forms at 390 px:** signup shows 4 labelled fields with both help texts above the fold; the empty submit keeps the layout and shows the three Persian errors under the fields; the submit button stays in the viewport.
- **Audio on mobile:** players are full-width rows inside the lesson; the lesson's 51 clips are the same elements as desktop, and seeking works in the same player.
- Screenshots: `home-mobile.png`, `today-mobile.png`, `lesson-list-mobile.png`, `lesson-mobile.png`, `exercise-mobile.png`, `exercise-scramble-mobile.png`, `exam-mobile.png`, `words-mobile.png`, `review-mobile.png`, `profile-mobile.png`, `readiness-mobile.png`, `signup-mobile.png`, `signup-error-mobile.png`, `login-mobile.png`, `login-error-mobile.png`, `goal-mobile.png`, `readiness-mobile.png`.

---

## 10. Issue list (the complete table)

> **Post-fix revision:** the **Status** column is new. The Expected/Actual columns still record the first revision's findings; the repro steps were re-run in this revision where the status says FIXED.

| ID | Severity | Status | Area | Page / URL | Steps to reproduce | Expected | Actual | Evidence | Suggested fix |
|---|---|---|---|---|---|---|---|---|---|
| BUG-01 | MAJOR | ✅ FIXED | Accounts / goal | `/accounts/goal/` | Sign up fresh → land on the onboarding goal step → click «ذخیره و دیدن برنامه» without touching anything (or after setting levels, try to leave the date empty) | Goal saved with no date; filling everything empty clears the goal, as the page's own hint says | The three Jalali menus have no empty option, so a date is always submitted; a fresh account stores **۱ فروردین ۱۴۰۵**, a past date nobody chose, and the goal panel then shows «تاریخ هدف ۱ فروردین ۱۴۰۵» | `review-artifacts/notes/accounts-audit.json` (`goalDateMenusHaveEmptyChoice`, `goalCleared`), `screenshots/26-goal-desktop-light.png`, live fresh-account probe (audit-fresh) | Add a blank choice to `target_year`/`target_month`/`target_day` (the `clean()` already handles "all three empty → no date"), and keep the "clears the goal" hint truthful |
| BUG-02 | MAJOR | ✅ FIXED | Accounts / signup | `/accounts/signup/` | Submit `username=audit-case2`, `password1=abc`, `password2=abc` | A Persian message about the minimum length | password1 shows **`This password is too short. It must contain at least 8 characters.`** — raw framework English in a Persian form | `accounts-audit.json` case `short password`; screenshot `21-signup-errors-desktop.png` | Give `MinimumLengthValidator` an `error_messages` entry (Persian) in `AUTH_PASSWORD_VALIDATORS`, like the other three validators already resolve to Persian through the catalog |
| BUG-03 | MAJOR | ✅ FIXED | Accounts / signup | `/accounts/signup/` | Submit two **identical** passwords that fail the strength rule (`abc`, `12345678`, `password`) | Only the real problem is reported | A second, false error appears on `password2`: «دو گذرواژه یکسان نیستند.» | `accounts-audit.json` cases `short password` / `digits only` / `common password` | In `clean_password2`, skip the comparison when `password1` is not in `cleaned_data` |
| BUG-04 | MINOR | ✅ FIXED | RTL / direction | `/exam/` | Open `/exam/`, read «کسی که «ankreuzen» را نفهمد…» | German marked `lang="de" dir="ltr"`, as the word list below it does | The paragraph quotes a German word with no direction marking | `perf-a11y.json` (`latinNotMarked`) | Wrap the inline German in the same `<span lang="de" dir="ltr">` |
| BUG-05 | MINOR | ✅ FIXED | Accounts / signup | `/accounts/signup/` | Sign up with `کاربر۱۲۳` or `<script>alert(1)</script>` | Rejected, because the help text promises `حروف انگلیسی، رقم و نویسه‌های @ . + - _` | Accepted and created; the value is escaped in HTML (no XSS), so the risk is quality, not security | `accounts-audit.json` cases `persian digits username` / `script username` (+ the two accounts that now exist on the mirror) | A `RegexValidator` matching the help text |
| BUG-06 | MINOR | ✅ FIXED | Accounts / signup | `/accounts/signup/` | Sign up with a 100-character username | Rejected, or a stated maximum | Accepted and created (`max_length=150`), with no maximum shown to the learner | `accounts-audit.json` case `100-char username` + user `uuuu…` on the mirror | Lower the cap and state it in the help text |
| BUG-07 | MINOR | ✅ FIXED | Content health | `manage.py validate_a1_content` | Run the project's own read-only validator | All checks pass | `FAIL German word data is consistent (9 problem(s))` — `die Eltern`, `die Ferien`, `die Geschwister`, `die Großeltern`, `die Lebensmittel`, `die Leute`, `die Möbel`, `die Papiere`, `die Pommes frites` «article/gender mismatch: … (gender None)» | CLI output captured in this session | The data is right (plural-only nouns have no gender): teach the validator that rule so the check goes green |
| BUG-08 | NOTE | ℹ️ UNCHANGED (by design) | Vocabulary | `/vocabulary/lookup/` | `curl /vocabulary/lookup/` without `?q=` | — | `400 {"error": "missing query parameter"}` | `crawl-guest.json` | Nothing to fix (AJAX endpoint); worth a line in the page map so an auditor does not chase it |
| BUG-09 | NOTE | ℹ️ UNCHANGED (by design) | Lessons | `/lessons/progress/import/`, `/lessons/1/progress/` | `GET` both URLs | — | 405 (and 403 for a guest on import) — they are POST-only endpoints | `loggedin-flow.json`, `crawl-guest.json` | Document them as endpoints in `AGENTS.md` |
| BUG-10 | MINOR | ✅ FIXED | Exercise UX | `/exercises/5500/` (scramble) | Open a scramble question and read the token chips | Bare words in the tray | Tokens carry punctuation (`danke.`, `gut,`, `heißt`) | `exercise-sample.json`, screenshot `ex-5500-scramble-desktop.png` | Strip trailing punctuation for display; the graded answer is unaffected |
| BUG-11 | WEAKNESS | ✅ FIXED | Content | `/lessons/1/` | Open lesson 1's vocabulary step and look for `sich` | A word the lesson actually uses | `sich` («خود (ضمیر انعکاسی)») is taught as a new word although no reflexive verb appears | `content-lessons-1-12-24.txt` | Move `sich` to the reference bank (lesson 24) or to the first lesson that teaches a reflexive verb |
| BUG-12 | WEAKNESS | ✅ FIXED | Accounts / signup | `/accounts/signup/`, `/accounts/login/` | Look at the five credential inputs | Browser can offer to fill/save them | No `autocomplete` attributes (`autocomplete: null` on all of them) | `accounts-audit.json` (`signupInitial`, `loginInitial`) | Add `autocomplete="username" / "email" / "new-password" / "current-password"` |

---

## 11. TASTE / opinions (clearly separated from bugs)

1. The single biggest visual weakness on a phone is that the lesson page is 2000+ DOM nodes and 51 audio buttons; on desktop it reads as a study page, but scrolling a phone through 45 words is long. A sticky step header would help.
2. The practice step's nodes say «حالا / بعدی / تمام» — good, but the list of 25 exercises behind «همهٔ تمرینهای این درس» is a wall on a phone; three at a time would read better.
3. `/lessons/today/` and `/readiness/` both explain themselves in prose at the top; on the fifth visit a learner will scroll past it. A one-line summary would be enough.
4. The English `English:` glosses are cleverly hidden from the Persian page, but they still occupy the stored body; if the product is ever translated, this is the field to split.
5. The word card after a miss is the best teaching surface in the product and is currently only reachable after being wrong twice. I would happily see it also on the word page.
6. `دقت: ۱۰۰٪` after four questions feels slightly congratulatory; a "4 از 4" alone would be more honest at that sample size.
7. The exam's 45-question paper answered in one sitting is faithful but heavy for a hobby project's first-time visitor; a "short paper" option exists only as the separate 12-question step test.
8. Scramble drills showing the shuffled tokens is right, but the tokens are underlined-looking chips that invite drag-and-drop; typing is the only input, so a hint like «بنویس» on the tray would prevent the misread (the label exists below, I still tried to drag one).

---

## 12. Coverage & limitations

**Covered**

- All 24 published lessons, all 195 steps, clicked step-by-step: `lesson-walk.json` (per-lesson steps, buttons, links, audio counts, console errors) + one desktop screenshot per lesson.
- Every link found on every lesson page (1195 unique) resolved: `page-links.txt` → all 200.
- Every audio URL referenced on a lesson page (1123) resolved: `audio-urls.txt` → all 200; `Range` → 206 on 10 samples across word/sentence/content/grammar; play + seek verified in the browser on a grammar clip.
- Audio file inventory across the whole database (3798 files, 0 missing, 0 zero-length).
- Exercise engine: 7/7 published types (no SPEAKING/WRITING exercises are published), 21 questions answered correctly to the results screen, wrong-answer paths run twice per type, hints fetched with and without an account, option-shuffle stability, ~60 adversarial API calls.
- Exam: index, one full paper started and finished (run 9), the score report, the after-finish refusal, another user's runs, `/exam/step/` (12-question station) and `/exam/sprechen/`.
- Accounts: signup (13 cases), login (4 cases), goal (5 cases), profile, theme switching in both directions, dark-mode re-check, and the same forms at 390 px.
- **Post-fix re-verification (this revision):** all 12 reported issues re-checked — signup cases and the whole goal flow (incl. both directions of the date menus) through the live browser, the goal DB state through the app's own view, `/exam/` markup and `autocomplete` via HTTP, scramble tokens on the live page, and `validate_a1_content` via CLI; results in `review-artifacts/notes/reverify-fixes.json` and `reverify-passwords.json` (probes: `tools/reverify_fixes.js`, `tools/reverify_passwords.js`).
- Cross-cutting: navigation, direction, themes, error pages, accessibility basics, page weight/timing, console health, hygiene sweep, server-kill resilience, draft-visibility code paths.

**Sampled, not exhaustive**

- Wrong-answer paths: 2 questions per exercise type (14 questions), not all 3504.
- Hints: requested for one question per type at strength 2.
- Mobile: 14 pages + 4 form states; the 500–899 px band was the least-sampled (I did not screenshot every page at 800 px).
- Session runner: one session (15 questions), 3 answered.
- Chat/dialogue: one exercise each.

**Not tested, and why**

- **Audio pronunciation quality.** I have no way to judge German pronunciation; I only verified existence, delivery, playback and seeking.
- **The 500 page.** Not triggered (the app is well-guarded); it was inspected as a template only.
- **`/lessons/progress/import/` as a working import.** It is POST-only and needs the localStorage payload the browser writes; I confirmed the endpoint's method contract, not a real import.
- **Draft invisibility.** This mirror contains no unpublished lesson, exercise, word or course, so the rule could only be verified by reading the querysets.
- **Theme flash.** Verified by construction (inline resolver before the stylesheet), not with a first-paint capture.
- **Screen-reader and contrast-tool testing.** Label/heading/focus checks were done in the DOM; no axe/WAVE run and no screen reader.
- **Full 65-minute exam expiry.** The finished-run refusal was verified; the timeout moment itself was not waited out.
- **`manage.py test`.** The first revision deliberately did not run it. This revision ran the full suite: **1049 tests OK (skipped=1)** in 115 s (exit 0), plus targeted `test accounts` (83 OK) and `test exercises` (341 OK, skipped=1) runs. It still cannot prove pronunciation quality or UI polish — only that the code's own rules hold.

**Progress checklist**

- Phase 0 setup (DB check, `check`, server, data snapshot): done
- Phase 1 teacher review (lessons 1, 12, 24 + all grammar + Perfekt auxiliaries + Wortliste): done
- Phase 2 learner walkthrough (guest → signup → onboarding → lesson 1 → wrong answers → hints → review queue → exam → readiness): done
- Phase 3 all 24 lessons, every step, every link, every audio clip: done
- Phase 4 exercise engine + adversarial + exam: done
- Phase 5 cross-cutting (nav, RTL, theme, errors, a11y, perf, hygiene, resilience): done
- Phase 6 mobile 390 px (iframe method) + dark mode: done
- Phase 7 report: done
- Post-fix revision (re-verify all reported issues → new score): done

**Self-audit answers**

- All published lessons, every step: **yes** (24 rows = 24 lessons, 195 step visits).
- Every button clicked / every link inventoried: **links yes** (all 1195 resolved); **buttons no** — the 47–59 distinct buttons per lesson were enumerated and the interactive ones (stepper, audio toggles, finish, runner controls, hint) were clicked in representative places; I did not click all 1123 audio play buttons, I verified their URLs instead. Stated as such.
- Every question type, some answered wrong on purpose: **yes** (7/7 published types).
- Answer not in the HTML before submitting: **yes**, per exercise and on the exam paper.
- Both themes, both viewports (iframe): **yes**.
- Signup/login/goal filled as a first-time user, every validation case, screenshots in both themes and on mobile: **yes**.
- Every finding has a URL, repro steps and evidence: **yes** (see the evidence column).
- `BUG` / `WEAKNESS` / `TASTE` separated: **yes** (§10 vs §11).
- Recorded what could not be tested: **yes** (above).

---

## 13. Raw data appendix

All raw files live under `review-artifacts/notes/` (JSON/text) and `review-artifacts/screenshots/` (106 PNGs).

**Console errors and failed requests by page group**

| Page group | `pageerror` | Console lines | Failed/bad responses |
|---|---|---|---|
| Guest page map (`crawl-guest.json`) | 0 | 3 | 404 `/this-page-does-not-exist/`; 405 `GET /accounts/theme/`; 403 `GET /lessons/progress/import/`; 400 `GET /vocabulary/lookup/` |
| Lessons 1–24 (`lesson-walk.json`) | 0 | 0 | 0 |
| Exercises (`exercise-audit2.json`) | 0 | 0 | 400 `POST /exercises/21/submit/` ×3 (adversarial: unknown question, unknown answer id, empty body); 403 guest hint |
| Signed-in flow (`loggedin-flow.json`) | 0 | 2 | 405 `GET /lessons/1/progress/`; 405 `GET /lessons/progress/import/` |
| Exam (`exam-flow.json`) | 0 | 2 | 400 `POST /exam/runs/9/submit/` (before a question id; and after finish) |
| Mobile (`console-mobile.json`) | 0 | 0 | 0 |
| Accounts (`console-accounts.json`) | 0 | 1 | 405 `GET /accounts/theme/` |

**Audio.** DB references: word 3226/3226, grammar 75/75, sentence 347/353, content 143/143, question 900/3504 — every referenced file present and non-empty. Lesson-referenced URLs: 1123, all 200. Range sample: `206` + `Content-Range: bytes 0-1023/<size>` + `Accept-Ranges: bytes` on all 10. Playback sample: `/media/contents/audio/content-3-d157qebt.mp3` — `currentTime 2.31 s`, `duration 14.35 s`, `paused false`, `readyState 4`; seek 13.35 → 14.0 s.

**Dead links.** None found (1195 lesson-page links + every nav/footer/account link → 200 or a deliberate redirect). The only non-200s are documented above.

**Timings and weights (dev server, localhost, mirror)**

| Page | Requests | Transfer | DOMContentLoaded | load | DOM nodes |
|---|---|---|---|---|---|
| `/` | 10 | 73 KB | 260 ms | 261 ms | 259 |
| `/lessons/1/` | 12 | 93 KB | 121 ms | 127 ms | 2159 |
| `/exercises/21/` | 9 | 91 KB | 91 ms | 92 ms | 411 |
| `/vocabulary/words/` | 8 | 53 KB | 105 ms | 111 ms | 578 |
| `/exam/` | 8 | 54 KB | 133 ms | 134 ms | 266 |
| `/lessons/today/` | 8 | 52 KB | 68 ms | 68 ms | 149 |

**Read-only project checks run**

- `.venv/bin/python manage.py check` → no issues.
- `.venv/bin/python manage.py validate_a1_content` → **all checks passed** (post-fix; in the first revision: 1 failed check, `German word data is consistent`, 9 plural-only nouns — now an informational note). Same counts: 24 lessons, 143 blocks, 1315 word links, 75 grammar topics, 353 sentences, 1018 words.
- `.venv/bin/python manage.py report_a1_wortliste` → 626/628 main entries (99.7%), 2 missing, 392 taught beyond the list.
- `.venv/bin/python manage.py report_a1_lesson_load` → 19 lessons teach more than the 30-word drill cap; drills are capped correctly.
- `.venv/bin/python manage.py audit_a1_exercises` → 586 exercises / 3504 questions, no content problems.
- `.venv/bin/python manage.py test` (post-fix revision) → **1049 tests OK (skipped=1)**, exit 0.

**Artifacts index**

| File | What it holds |
|---|---|
| `crawl-guest.json` | guest page map: status, title, lang/dir, overflow, console per page |
| `lesson-walk.json` / `all-links.json` / `all-audio.json` | per-lesson steps, buttons, links, audio, stepper behaviour, console |
| `page-links.txt` / `audio-urls.txt` | the exact URL lists that were resolved |
| `exercise-sample.json` / `exercise-audit2.json` | questions, options, kinds, correct answers and every exercise check |
| `accounts-audit.json` | full form snapshots, all validation cases, theme, links, mobile metrics |
| `loggedin-flow.json` / `exam-flow.json` | completion, badges, XP, hints, review queue, session, chat, exam |
| `mobile-audit.json` / `mobile-audit.out` | 390 px metrics for 14 pages |
| `perf-a11y.json` | weight/timing, a11y basics, direction and hygiene sweeps |
| `console-*.json` | console/pageerror/network logs per phase |
| `server.log` | the runserver log for the whole audit |
| `reverify-fixes.json` / `reverify-passwords.json` | post-fix re-verification: signup cases, goal menus + DB state, both password-probe rounds |
| `tools/reverify_fixes.js`, `tools/reverify_passwords.js` | the two Playwright probes added by the post-fix revision |
| `screenshots/` | 106 PNGs referenced throughout this report |

---

*Report only. No application code, template, migration, data file or database row was modified by this audit; the only writes were this report, `review-artifacts/`, and the rows the application itself creates when a visitor signs up, answers, completes a lesson or starts an exam run (the post-fix revision added two such throwaway accounts on the mirror; the test suite builds and destroys its own test database). The owner's fixes themselves were made before this revision started and are outside it — this revision only read them and exercised their behaviour.*
