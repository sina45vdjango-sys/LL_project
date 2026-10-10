# REVIEW-PROMPT.md — Full browser audit of Velingo

> **How to use this file:** hand the whole file to a fresh agent that has a real browser
> (Playwright / Chrome DevTools MCP) and shell access to this repo. It is self-contained:
> setup, scope, checklists, evidence rules, grading and the exact report format are all here.
> Read it fully before starting. Do not skip Phase 3 or Phase 4.

---

## 0. Mission

You are auditing **Velingo**, a Django website that teaches **German at A1 level to
Persian speakers**. The site is Persian and right-to-left; German text inside it must be
left-to-right.

You will produce **ONE** Markdown report file, in **English**, with:

- a **teacher's review** (is this actually good teaching material for Goethe A1?), and
- a **real learner's hands-on walkthrough** of the whole site, in a browser, page by page,
  clicking every button and every link there is.

The owner is building this as a **portfolio project for an Ausbildung application**. Treat
it as if a German trainer might open it tomorrow. Say what is genuinely good, and say what
is broken or weak — with proof.

**You will NOT change any code.** Report only. (Creating the report file and the screenshot
folder is the only writing you do.)

---

## 1. Non-negotiable rules

1. **Report only. Zero code changes.** Do not edit templates, CSS, JS, Python, migrations,
   data files. Do not run `makemigrations`, `migrate`, `git commit`, `git push`, or install
   packages. Your write access is limited to:
   - `REVIEW-REPORT.md` (the deliverable)
   - `review-artifacts/` (screenshots and any raw notes)
2. **Never destructive.** No `DELETE`, `DROP`, `TRUNCATE`, no seed/import commands, no
   wiping DB rows. Read-only against the database.
3. **Confirm which database you are on before doing anything DB-related:**
   ```bash
   .venv/bin/python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
   ```
   This repo normally points `manage.py` at the disposable **mirror** database. If it points
   at the real one (`language_learning`), say so in the report and still continue — but be
   extra careful: read-only, no writes of any kind.
4. **Always use `.venv/bin/python`** for `manage.py`. The system Python has no `psycopg`.
5. **Evidence or it did not happen.** Every claim of "works" or "broken" needs a URL, the
   exact action, the observed result, and a screenshot or console/network detail. "Looks
   fine" without enumeration is not an acceptable finding.
6. **Be fair, and be specific.** Separate:
   - `BUG` — something is objectively wrong (500, dead link, missing audio, wrong answer
     marked correct, text overflowing, wrong German, wrong translation).
   - `WEAKNESS` — it works but is weak (confusing flow, weak exercise, no feedback).
   - `TASTE` — a design preference. List these last and label them clearly as opinions.
   Never inflate a `TASTE` item into a `BUG`.
7. **Exit status matters.** Never pipe a command that you are using as a check through
   `tail`/`head` in a way that hides its exit code.
8. **The correct answer must never be visible in the HTML.** This is a stated project rule.
   Verify it actively (see Phase 4), don't assume it.

---

## 2. Setup (do this first)

### 2.1 Start the site

For a local browser audit, with the mirror DB already in place:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Run the server in the background, wait until it answers, and keep checking that it is still
alive between phases. If static files or audio return 404 while running with `DEBUG=False`,
use this (project-documented) variant instead:

```bash
DJANGO_DEBUG=False \
DJANGO_SERVE_MEDIA=True \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
.venv/bin/python manage.py runserver 0.0.0.0:8000 --insecure
```

If the server dies or the port is taken, fix it and note it in the report. Do not silently
continue with a dead server.

### 2.2 Get the data facts yourself

Before reviewing, record the current numbers (they may differ from the ones below):

```bash
.venv/bin/python manage.py shell -c "
from lessons.models import Lesson, Course
from vocabulary.models import Word
from exercises.models import Exercise, Question
from exams.models import ExamRun
print('courses', Course.objects.count())
print('lessons', Lesson.objects.count(), 'published', Lesson.objects.filter(is_published=True).count())
print('words', Word.objects.count())
print('exercises', Exercise.objects.count(), 'questions', Question.objects.count())
print('exam runs', ExamRun.objects.count())
"
```

At the time this prompt was written the mirror had roughly: **24 published lessons,
1 course, ~3.2k words, 586 exercises, 3504 questions**. State the real numbers in the report.

### 2.3 Build your page map and your todo list

Use `write_todos`. The phases below are the plan. Do not collapse them.

### 2.4 Sessions may be interrupted — checkpoint as you go

Write findings into `REVIEW-REPORT.md` **incrementally**, not at the very end. After each
lesson and each exercise type, append what you found and tick a progress checklist at the
bottom of the report (e.g. `Phase 3: lessons 1–7 done`). If the run dies, a later agent must
be able to resume from the file. Save screenshots as you take them, not afterwards.

---

## 3. The page map (all routes to cover)

Lessons
- `/` — dashboard
- `/readiness/` — "my readiness" (progress, accuracy, coverage, grammar, goal)
- `/lessons/` — lesson list
- `/lessons/today/` — the single "today" board (path, XP, streak, badges)
- `/lessons/courses/<pk>/` — course detail
- `/lessons/<pk>/` — **lesson detail (the main lesson flow)**
- `/lessons/<pk>/progress/`, `/lessons/<pk>/review/`, `/lessons/<pk>/check/`
- `/lessons/progress/import/`

Vocabulary
- `/vocabulary/words/`, `/vocabulary/words/level/<code>/`, `/vocabulary/words/<pk>/`
- `/vocabulary/review/` — spaced-repetition review queue
- `/vocabulary/lookup/` — search

Exercises
- `/exercises/` — exercise list
- `/exercises/session/` — session runner
- `/exercises/<pk>/` — exercise detail (the runner)
- `/exercises/chat/<pk>/`, `/exercises/dialogue/<pk>/`
- `/exercises/<pk>/submit/`, `/exercises/<pk>/hint/` (JSON endpoints)

Exams
- `/exam/` — exam index
- `/exam/start/`, `/exam/step/` (short station), `/exam/sprechen/`
- `/exam/runs/<pk>/`, `/exam/runs/<pk>/submit/`, `/exam/runs/<pk>/finish/`

Accounts
- `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`
- `/accounts/profile/`, `/accounts/goal/`, `/accounts/theme/`

Error & shell
- 404 (`/this-page-does-not-exist/`), 405, 403, 500 templates
- Global sidebar / app bar / bottom nav, theme (light + dark), `<html lang/dir>`

---

## 4. Phase 1 — Teacher review (do this with the browser open, but write about the content)

Play a **German A1 teacher / Goethe-Zertifikat A1 examiner**. For the whole course and a
representative deep read of at least three lessons (lesson 1, the review lesson, and the
lesson with the biggest vocabulary load), judge:

- Does it actually teach A1, or just present words? Is there a grammar progression?
- Is German correct — spelling, capitalisation of nouns, Umlauts, articles, plurals,
  `Perfekt` auxiliaries, word order, politeness forms?
- Are the **Persian translations** natural and correct, or machine-sounding / wrong?
- Is vocabulary appropriate for A1 (not B1 words)? Is it in the official Goethe A1
  Wortliste spirit? Any duplicate or near-duplicate entries?
- Do exercises test the right skill (recognition vs production)? Is there enough practice
  per item? Is the difficulty ramp sensible across the 24 lessons?
- **Audio**: you cannot judge pronunciation quality — say so explicitly. What you *can*
  judge: does every word/sentence/grammar clip exist, load, play, and seek? Are the
  audio-referenced items the ones the exercise asks about?
- Exam section: does `/exam/` mirror the real A1 format (sections, timing, weighting,
  pass mark)? Is the speaking practice meaningful?
- Exam honesty: is anything stated as fact that isn't (levels, Goethe alignment, claims on
  the README/home page)? Flag overclaiming as `WEAKNESS`.

Write this as a short essay plus a table of concrete content problems with lesson/word
references.

---

## 5. Phase 2 — Learner walkthrough with a fresh account

Play a **Persian speaker preparing for an Ausbildung** who has never seen the site.

1. Land on `/` as a **guest**. Note the first impression, what you understand, what you
   cannot do without an account, and whether anything is broken for guests.
2. **Sign up a fresh account** at `/accounts/signup/` (something like `audit-tester` with a
   throwaway password — mirror DB only).

   **The owner's specific worry: the forms must be obviously legible.** Someone who has
   never seen the site must understand every field without guessing. Audit the signup form
   field by field, and screenshot it (desktop + mobile, light + dark).

   - **Legibility**: is every field actually visible and labelled in Persian, and is it
     obvious what belongs in it? Are required fields marked? Is the password rule stated
     *before* you fail it? Is the submit button obvious and clearly labelled? Is any field
     pushed off-screen, clipped, or hidden behind a scroll at 390px?
   - **Labels, not just placeholders**: a field must not rely on placeholder text alone —
     the label must still be there after you start typing.
   - **Field inventory**: list every field the form shows (username, email, password,
     confirm-password, anything else). Is confirmation even asked? Note anything missing
     that a real signup needs.
   - **Direction / RTL**: Persian labels RTL, Latin username/email/password inputs LTR, no
     bidi glitch in labels, placeholders, or error text.
   - **Validation**, each case separately: empty submit, whitespace-only, bad email format,
     password too short / all digits / too common, mismatched confirmation, duplicate
     username, duplicate email, 100-character username, Persian digits in the username,
     `<script>` in a text field. For each: does it fail gracefully, is the error shown next
     to the right field, is it readable Persian (not raw Django English), and is the input I
     already typed preserved so I do not retype it?
   - **No leaks**: no stack trace, no settings, no framework English such as
     `This field is required.`
   - **Keyboard + basics**: tab through the form in a sensible order, every input has a real
     `<label>`/aria-label, focus is visible, Enter submits.
   - **Password managers**: `autocomplete` attributes present so a browser can fill the form.
   - **After signup**: where do you land? Is there a welcome or a clear next step? Are you
     logged in? Does the nav switch to the logged-in state?
   - **Login** (`/accounts/login/`) and **logout**: same legibility and validation audit; a
     wrong password must not reveal whether the username exists; logout returns somewhere
     sensible.
3. Go through `/accounts/goal/` and `/accounts/profile/`:
   - **Goal form**: is it clear what the goal is for and how to set it? Do the options /
     target date make sense, and do they actually save? Reload — are my answers still there?
     Does an empty or invalid submit show a readable Persian error? Does the goal then show
     up in `/readiness/` or `/lessons/today/` the way the site claims it should?
   - **Profile**: is every value correct for my fresh account (no `None`, no unexplained
     zeros, no other user's data)? Are the edit links and the logout control obvious and
     working?
   - **Theme** (`/accounts/theme/`: light / dark / system): the switch persists after reload,
     there is **no flash of the wrong theme**, and each form above gets re-checked once in
     dark mode.
   - **Links**: click every link on signup, login, goal and profile and confirm each one
     resolves to a real page.

   Concretely, the forms you must inspect are:
   - Signup — fields: `username`, `email`, `password1`, `password2`. Two pieces of guidance
     text (`help_text`) exist in the code and **must be visibly rendered**: the username
     rule (English letters, digits, `@ . + - _`) and the password rule (at least 8
     characters, not too simple, not digits only). If either is missing on the page, that
     is a real finding, because the user is then guessing.
   - Goal — fields: current level, target level, reason, and a target date built from three
     separate Jalali menus (year / month / day).

   **Known design decisions — do NOT report these as bugs:**
   - Email is optional on purpose (its label says so).
   - Submitting the goal form completely empty is a legitimate action that *clears* the
     goal — it must not be treated as a validation failure.
   - The goal date is three Jalali dropdowns, not the browser's native date picker; that is
     deliberate so the Persian interface stays Persian.
   - Password strength rules come from Django's validators wrapped in Persian messages.

   What you *should* judge: are those Persian messages natural and actually shown, is the
   guidance text readable before you fail, and does anything on these pages look like an
   unfinished form.
4. Follow **"today"** (`/lessons/today/`) as a beginner would: which node is active, what
   does it tell you to do, can you get to a lesson from here in one click?
5. Do **lesson 1 end to end as a real learner**: start it, read every step, play every audio
   clip, answer every exercise, get things wrong on purpose at least twice, use a hint at
   least once, and check whether the experience makes you want to continue. Write down
   exactly where you got confused.
6. Check XP / streak / badges (`/lessons/today/`): do the numbers change after real work?
   Is the badge wall honest (no grey locked wall — project rule)?
7. Come back later in the walkthrough and check `/readiness/` — does it now reflect what you
   actually did, or does it show zeros / nonsense?

Write the whole walkthrough as a chronological log: step → what you clicked → what happened
→ how it felt. This section must read like a human used the site, not like a test matrix.

---

## 6. Phase 3 — Deep, lesson-by-lesson audit (ALL lessons, every step)

The owner explicitly asked for **all 24 published lessons, every step, every button**. Do not
sample. For each lesson `pk` (1..N published), open `/lessons/<pk>/` and:

- Walk **every step**: intro, agenda, lead, vocabulary, word rows, grammar, sentences,
  practice, finish (the step templates are `steps/_intro.html`, `_agenda.html`, `_lead.html`,
  `_vocabulary.html`, `_word_row.html`, `_grammar.html`, `_sentence.html`, `_sentences.html`,
  `_practice.html`, `_finish.html`, `_block.html`).
- **Click every button**: next / previous step, play audio, mark-complete, jump-to-exercise,
  show-answer where allowed, collapse/expand, pagination, and any link on the page. Confirm
  each one does something real (URL changes, DOM updates, no console error, no dead `#`).
- **Inventory every link on the page** and confirm it resolves (200, sensible page, no
  redirect loop). Report dead or misleading links individually.
- Check the **rendering**: Persian text RTL, German text `lang="de" dir="ltr"`, no mojibake,
  no raw `None` / `undefined` / template leftovers, no overlapping or clipped text, no
  horizontal scrollbar, numbers rendered correctly.
- Check **audio per lesson**: every player loads (200, non-empty), plays (currentTime
  advances), and **seeks** (Range request → 206, since the project serves media with Range
  support). Note any clip that is missing, silent, or 404.
- Open `/lessons/<pk>/progress/`, `/lessons/<pk>/review/`, `/lessons/<pk>/check/` for the
  lesson and exercise each.
- Confirm the "draft is invisible" rule: unpublished content must never appear in a list or
  a detail page.
- Take a **desktop screenshot** of each lesson's main screen and a **mobile screenshot** of
  the flow (see Phase 6).

Record one row per lesson in the report with: step count, buttons checked, links checked,
audio clips checked, problems found, and a per-lesson score.

---

## 7. Phase 4 — Exercise engine audit (maximum coverage, and try to break it)

The owner asked for **maximum coverage**, not a spot check. Go to `/exercises/`,
`/exercises/session/`, `/exercises/<pk>/`, plus `/exercises/chat/<pk>/` and
`/exercises/dialogue/<pk>/`.

Cover **every question type**, several instances of each, and answer some **deliberately
wrong** to test the feedback path:

- multiple choice (recognition)
- article / plural / Perfekt drills
- free-text typing (word dictation, translations)
- listening (audio → choose)
- pronunciation / minimal pairs (audio → which word did you hear)
- dictation (audio → type the word)
- scramble (word order)
- reading comprehension with a passage
- true/false, fill-in-the-blank
- chat and dialogue delivery modes, and the session runner

For each type, verify:

1. **Rendering** — prompt, audio player, options, RTL/LTR, no clipped German, no layout
   break with long options, image/audio present.
2. **Correct answer submission** → accepted, feedback sensible, score increments.
3. **Wrong answer submission** → clearly explained, the right answer shown *after*
   submission, no shaming, retry behaviour defined.
4. **Answer not leaked before submission** — inspect the page source / network payload
   *before* submitting. The correct answer must not be in the HTML or in the initial JSON.
5. **Hints** — call the hint flow (`/exercises/<pk>/hint/`) and confirm it is staged and
   never reveals the final answer outright, as the project claims.
6. **Option shuffle** — the correct option's position should be stable on reload (seeded by
   question pk) and grading must use the stored answer, not the position.
7. **Word progress side-effects** — solving/failing a word question should move
   `WordProgress` / the review queue where the project says it should, and must not move it
   where the project says it must not (e.g. pronunciation drills are not labelled as a
   word failure). Verify by observing the review queue and readiness page before/after.
8. **Adversarial tests** (run all of them, note the result of each):
   - submit empty and whitespace-only
  - (for every account form too — see Phase 2: the signup / login / goal forms get the same
    bad-input treatment, since a fresh learner meets those forms before any exercise)
   - submit a 5000-character answer
   - submit Persian digits, quotes, emoji, `<script>` text
   - double-click submit / submit twice rapidly
   - press Back after submitting and re-submit
   - reload the page after submitting
   - open the submit endpoint directly with a GET (expect 405)
   - open an exercise id that does not exist or is unpublished (expect 404 / hidden)
   - navigate away mid-exercise and return — is state consistent?
   - check the browser console and network tab for errors and failed requests on every page
9. **Exam flow** (`/exam/`): start, run a section, answer, submit, finish, and read the
   score report. Confirm the **timer is server-side** (submitting after time is rejected —
   the browser timer is display only). Do the short step test (`/exam/step/`) and the
   speaking practice (`/exam/sprechen/`). Check the score maths against the stated weighting
   and pass mark. If a full run is too expensive, say exactly what you did and did not run.

Give each exercise type its own row: checked N instances, what broke, representative
screenshot.

---

## 8. Phase 5 — Cross-cutting checks

Run these across the whole site and record results:

- **Navigation & IA**: sidebar (`includes/sidebar.html`), app bar, bottom nav, account menu,
  brand link. Every nav item must resolve and the active state must be correct.
- **RTL / LTR correctness**: Persian RTL everywhere, German always `dir="ltr" lang="de"`.
  Check mixed-direction paragraphs (Persian sentence containing a German word) for broken
  punctuation order.
- **Theme**: light and dark, every main page, plus `/accounts/theme/` switching. No flash of
  the wrong theme on reload; `<meta name="theme-color">` updates; contrast on key text.
- **Error pages**: `/this-page-does-not-exist/` (404), a GET against a POST-only endpoint
  (405), and the 500 template by inspection. No stack traces, no settings/secrets leaked, no
  blank page, working "go home" link.
- **Accessibility basics**: keyboard-only traversal of the main flow, visible focus outline,
  alt text on meaningful images, labels on inputs, heading order, colour contrast on
  critical text, audio controls reachable.
- **Performance sanity**: page weight, count of requests, any obviously huge asset, time to
  interactive on the lesson page and the exercise page. Report numbers, not adjectives.
- **Console health**: zero errors on every page you visit. List every error/warning you saw
  with the page it came from.
- **Content hygiene sweep**: search the rendered pages for placeholder text, `TODO`, `lorem`,
  `test`, `foo`, English leftovers, Persian typos, `بزودی`, empty states with broken layout.
- **Resilience**: kill/restart the server once mid-run and confirm the site recovers and you
  can continue.

---

## 9. Phase 6 — Responsive / mobile

Test **both** desktop (1280×800) and mobile (390×844).

Project rule: **responsive testing must be done inside an iframe.** Chrome will not shrink a
window below ~500px, so a "390px" window still measures ~500px. Load the site in an iframe
with the iframe's own width set to 390 and verify the layout inside it. Confirm:

- at **≥900px**: sidebar layout; at **≤899px**: app bar + bottom nav, and that the switch
  happens where the project says it does
- nothing overflows horizontally, tables/lists/pagination reflow, tap targets are usable
- the lesson flow and the exercise runner are both usable on a phone
- long German words and long Persian sentences wrap instead of clipping
- audio players are usable on mobile layout

Screenshot the mobile flow for at least: home, today, lesson list, one full lesson, one
exercise of each type, exam index, profile, and **the signup and goal forms, including one
with a validation error showing**.

---

## 10. Evidence and screenshot rules

- Save screenshots under `review-artifacts/screenshots/` with
  `NN-<area>-<page>-<desktop|mobile>.png` (e.g. `07-lesson-003-desktop.png`).
- Keep raw notes, console dumps and network details in `review-artifacts/notes/`.
- In the report, reference screenshots by path. A finding with no screenshot and no
  reproducible steps is not a finding.
- Keep quoted UI strings **verbatim in their original language** (Persian/German) — do not
  translate them inside quotes.

---

## 11. Grading rubric (score every dimension 0–10, then weight)

| # | Dimension | Weight | What a 10 looks like |
|---|---|---|---|
| 1 | Teaching quality (teacher lens) | 15 | Correct A1 content, real progression, exercises that teach |
| 2 | Lesson UX & content rendering | 15 | Every step clear, every button works, nothing broken |
| 3 | Exercise engine correctness | 20 | Grading right, feedback good, answers never leaked, hints staged |
| 4 | Navigation, links, buttons | 10 | Every link resolves, active states right, no dead ends |
| 5 | Persian/RTL + German/LTR correctness | 10 | Natural Persian, perfect German, correct direction everywhere |
| 6 | Visual consistency & theming | 5 | One design language, both themes correct, no flash |
| 7 | Mobile / responsive | 10 | Real 390px usable, no overflow, correct breakpoint |
| 8 | Accessibility (basics) | 5 | Keyboard path, focus, labels, contrast |
| 9 | Error handling & edge cases | 5 | No 500s, clean 404/405, resilient to junk input |
| 10 | Trust signals for the Ausbildung portfolio | 5 | No debug leaks, audio all real, honest claims |

**Overall** = weighted average ×10 → a 0–100 score, plus a letter:
A ≥90 · B 80–89 · C 70–79 · D 60–69 · F <60.
Give the overall number and letter prominently, plus a one-paragraph "would I show this to a
German trainer?" verdict.

Scores must be justified by the findings. If you give a 9 in a dimension and list three
`BUG`s in it, fix the score or explain.

---

## 12. The report file: exact structure

Deliver one file, `REVIEW-REPORT.md`, in English, with this shape:

```markdown
# Velingo — Browser Review Report

- Date / agent / DB name / server command used
- Data snapshot (lessons, words, exercises, questions, exam runs)
- Build/check status, console health summary

## 1. Verdict & score
- Overall score /100 + letter + one-paragraph verdict
- Score table (the 10 dimensions, weight, score, justification in one line)

## 2. Top 10 things to fix (ranked by impact)
1. … (severity, page, one-line fix suggestion)

## 3. What is genuinely good
- (short, honest, no flattery)

## 4. Teacher review
- Long-form assessment + content problem table

## 5. Learner walkthrough log (Phase 2)
- Chronological: step → action → result → impression

## 5b. Accounts & forms audit (signup / login / goal / profile / theme)
- One row per form: fields found, labels clear?, validation cases passed/failed,
  RTL/LTR, dark mode, mobile, screenshots
- Explicit answer: could a first-time Persian speaker fill this form without guessing?
- Every validation failure case: input used → message shown → good/bad

## 6. Lesson-by-lesson table (all lessons)
| Lesson | Steps | Buttons | Links | Audio | Issues | Score |

## 7. Exercise & exam audit
- One row per question type: instances checked, results, issues
- Adversarial test results table (each test: expected vs actual)

## 8. Cross-cutting findings
- Navigation / RTL / theme / error pages / a11y / performance / console

## 9. Mobile (390×844) findings

## 10. Issue list (the complete table)
| ID | Severity | Area | Page/URL | Steps to reproduce | Expected | Actual | Evidence | Suggested fix |

## 11. TASTE / opinions (clearly separated from bugs)

## 12. Coverage & limitations
- Exactly what was covered, what was sampled, what could not be tested and why
- Progress checklist (which phases/lessons completed)

## 13. Raw data appendix
- Console errors, failed requests, audio 404s, dead links, timings
```

Severity scale: `BLOCKER` (site unusable / wrong grading / data leak),
`MAJOR` (broken button/link/audio, wrong German, layout break), `MINOR` (cosmetic or
annoying), `NOTE` (observation).

---

## 13. Self-audit before you submit

Answer these honestly at the end of the report. If any answer is "no", go back and finish.

- Did I open **all** published lessons and walk **every** step? (count rows = lesson count)
- Did I click **every** button and inventory **every** link per lesson, or did I claim I did?
- Did I cover **every** question type and answer some wrong on purpose?
- Did I verify the correct answer is not in the HTML **before** submitting?
- Did I test both themes and both viewports (with the iframe method for mobile)?
- Did I fill the signup, login and goal forms as a first-time user, run every validation
  failure case, and screenshot each form in both themes and on mobile?
- Does every finding have a URL, repro steps, and evidence?
- Did I separate `BUG` / `WEAKNESS` / `TASTE` honestly instead of padding the list?
- Did I record what I could **not** test (audio quality, unavailable flows) as a limitation
  rather than as a pass?

---

## 14. What NOT to do

- Do not refactor, "improve", or fix anything in the code.
- Do not run migrations, seeds, imports, or any write command against the database.
- Do not commit or push.
- Do not install packages or change config.
- Do not create more than the one test account you need.
- Do not report a page as "checked" if you only looked at the top of it.
- Do not finish with a summary that a non-technical reader could have written without
  opening the site.
