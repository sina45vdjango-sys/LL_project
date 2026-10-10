# ولینگو — Velingo

A German-learning platform for **Persian speakers**, covering CEFR level **A1**.

The interface is Persian and right-to-left; German content is always rendered
`lang="de" dir="ltr"`, so a German sentence never inherits the page's direction.

---

## What it does

- **24 lessons** across one published course, presented as a guided *journey* rather than
  a wall of text. Each lesson is a sequence of steps — intro, explanation, vocabulary,
  grammar, examples, dialogue, reading, listening, practice, finish — and a lesson only
  gets a step when it actually has the material for it.
- **A vocabulary reference** of 1,018 words with search, level tabs, per-word audio, and
  the real lessons that teach each word.
- **792 exercises** with **server-side grading**: 111 authored across five question
  shapes (multiple choice, true/false, reading, fill-in-the-blank, translation), 24
  generated listening exercises, 358 generated vocabulary/grammar/writing drills that make
  **all 1,018 words** answerable both ways — recognised *and* produced: 905 meaning
  questions, 1,011 typed questions, and grammar drills built from stored word facts (530
  `der` / `die` / `das`, 466 plural, 195 Perfekt-auxiliary) — 92 **sentence** reading
  drills (596 questions) that ask about the lessons' own sentences in both directions, and
  24 **pronunciation** drills (69 questions) that play a word and ask which of two
  similar-sounding words it was, and 183 **dictation** drills (1,056 questions) that play a
  word and ask the learner to write it.
  The article, plural and Perfekt drills are **tagged with the grammar topic they really
  test**, so «آمادگی من» can show grammar performance as grammar rather than as vocabulary
  under another name. Lesson 12 — the mid-course *Wiederholung*, which introduces no new
  word — is drilled from the words it revisits, so the middle of the course is not a wall.
- **Progress that is actually stored.** Signed in, `LessonProgress`, `ExerciseAttempt`
  and `WordProgress` are the record; anonymous visitors get a `localStorage` layer behind
  one module (`static/js/progress.js`).
- **A review surface** built from the learner's own mistakes: the words they answered
  wrong, ranked worst-first, and the real exercises that test those words — so review
  means answering questions again rather than reading a list of them. The same page
  answers for **rules**: a question can carry the grammar topic it really tests, so a
  wrong answer about the plural rule is remembered against that rule, listed with its own
  counters, and paired with the drills that ask about it. The dashboard
  shows a signed-in learner the same plan, and per-exercise results survive a reload. A
  lesson also ends on its own mistakes: the finish step names the words **of that lesson**
  you answered wrong and offers the way back into practising them. The rule lives in one
  place, `vocabulary/review.py` — with its grammar half in `lessons/readiness.py`, because
  that module already owns which question asks about which topic.
- **A mock exam in the shape of the real one.** The official Goethe A1 written exam is 45
  questions on one 65-minute clock (Hören 15 / Lesen 15 / Schreiben 15), scored as the
  exam scores it — each section's raw points × 1.66, so the written part is worth 75 of the
  100 and the pass line is 60. A sitting picks questions from this product's own drills,
  stores the paper it asked, counts down on the server's clock, and keeps the score, so
  sittings can be compared. It also says plainly what it is *not*: the official task types,
  the official marking, and the spoken section's 25 points, which nothing here grades — the
  spoken part is a rehearsal with the exam's phrases, linked to real practice for the ones
  the course teaches.
- **A goal and an honest answer to "how am I doing?"** A learner can state what they are
  learning German for (Ausbildung, university, work, migration, general), where they want
  to get to and by when, and `آمادگی من` turns that plus their own rows into course
  progress, exercise accuracy, vocabulary performance and — when there is a date — the
  weekly pace it implies. There is **no readiness percentage and no CEFR claim**: the page
  shows the numbers it can prove and states, with computed figures, what the data cannot
  answer yet. The arithmetic lives in one place, `lessons/readiness.py`.
- **A daily plan rather than a wall of content.** The dashboard opens on «امروز»: the
  lesson to work on (the one you are inside, or the next one you have not finished) and
  practice for the words whose review time has really arrived — the best exercise that
  tests them, skipping any exercise you have already answered today — followed by what you
  have really done today, counted from your own submissions. When nothing is due yet it
  falls back to the words you answered wrong, so no history is wasted. No streaks, no
  points. A word can honestly be *due* because every answer re-schedules it with an
  adaptive, explainable spaced-repetition algorithm (state, interval, ease and response
  time); the queue lives in `vocabulary/schedule.py` and the plan in `lessons/today.py`.
- **Generated audio** for every word, grammar topic, sentence and lesson block
  (~1,500 MP3 files).
- **A light and a dark theme, and the learner owns the choice.** Both themes are the same 31
  CSS custom properties in `static/css/base.css`, so they cannot drift apart, and an explicit
  choice always beats the OS. Until someone chooses, the interface follows the operating
  system, decided by a small inline script *before the first paint* so there is no flash of
  the wrong theme. Pinning one is a profile setting rather than a browser one, so it follows
  the learner to any device they sign in on.

Everything is browsable without an account. Only `/accounts/profile/` requires a login.

---

## Stack

| | |
|---|---|
| Framework | Django 6.1.1 |
| Database | PostgreSQL (driver: `psycopg` 3) |
| Frontend | Server-rendered Django templates, hand-written CSS, vanilla JS |
| Audio | `edge-tts` (German `de-DE-KatjaNeural`) validated with `ffmpeg` |

Deliberately **no** bundler, no npm, no JS framework, no DRF, no CSS framework. The design
system is a set of CSS custom properties in `static/css/base.css`. It ships **two themes**,
light and dark, and a learner can pin either one on `/accounts/profile/`; the choice is stored
on `UserProfile`, so it follows them to any device they sign in on. Until they choose, the
interface follows the operating system's light/dark setting.

---

## Project layout

```
config/          settings, URLs, the shell context processor (brand + navigation)
accounts/        signup, login, logout, profile; UserProfile
lessons/         levels, courses, lessons, lesson content, the journey, progress
vocabulary/      Word, Grammar, Sentence, WordProgress, word lookup
exercises/       Exercise, Question, Answer, QuestionTarget, ExerciseAttempt
tests/           project-wide template guards (not a feature app)
templates/       the app shell, dashboard and error pages
static/          base/components/shell CSS and shared JS
media/           generated audio (gitignored)
```

A few files are worth knowing about because they hold a rule in one place:

| File | What it owns |
|---|---|
| `lessons/journey.py` | step order, labels, counts and which partial renders each step |
| `lessons/progress.py` | how `LessonProgress` moves |
| `exercises/grading.py` | the verdict for a submitted answer |
| `exercises/runner.py` | the *shape* of an exercise page (never its answers) |
| `exercises/history.py` | which stored attempt counts when reading results back |
| `vocabulary/progress.py` | how `WordProgress` counters move |
| `vocabulary/schedule.py` | the adaptive review schedule (state, interval, ease, due date) — when a word comes back |
| `vocabulary/review.py` | which words a learner should review, and the exercises that test them |
| `exercises/data/pronunciation_pairs.py` | which sound contrasts the pronunciation drill trains, and why they are rules rather than a pair list |
| `exercises/generated.py` | which exercises a command wrote rather than a person, so the vocabulary drills never mistake a generated drill for an authored question |
| `lessons/readiness.py` | progress, accuracy, vocabulary, grammar, coverage, the goal and the deadline pace — and the rules a learner got wrong, with where to practise them |
| `exams/spec.py` | the official exam's own numbers (sections, minutes, items, the ×1.66 factor, the pass mark) and the spoken part's three parts, with the source recorded |
| `exams/paper.py` | which questions a sitting asks, and what it scored — the official arithmetic, in one place |
| `exams/models.py` | a sitting and its per-question record: the paper it asked, and the score that must not move afterwards |
| `lessons/today.py` | today's lesson, today's practice (the words that are due, else your mistakes), and what you already did today |
| `vocabulary/german_text.py` | which part of a mixed German/Persian text gets narrated |
| `config/context_processors.py` | the navigation, shared by desktop and mobile |
| `static/js/progress.js` | the single interface to progress, local or server-backed |

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create the database and a user:

```sql
CREATE DATABASE language_learning;
CREATE USER django_user WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON DATABASE language_learning TO django_user;
```

Then configure the project. `config/settings.py` holds no secret: every value comes from
the environment.

```bash
cp .env.example .env      # then fill in DJANGO_SECRET_KEY and the DB_* values
```

`.env` is gitignored; `.env.example` is committed and contains placeholders only. A
variable already exported in your shell wins over the file, so
`DJANGO_DEBUG=False python manage.py check` works without editing anything. Django
refuses to start when `DJANGO_SECRET_KEY` is missing, and `DEBUG` defaults to the safe
`False`. Generate a key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### The mirror database

A second checkout (`config/settings_mirror.py`, kept out of git) reuses these same
settings and swaps only the database name to `language_learning_mirror`. It exists so
content experiments — re-seeding, re-importing — can run against a throwaway copy
instead of the real data. In a mirror checkout, `manage.py` is pointed at that module, so
every command targets the mirror database; confirm which one you are on before running
anything destructive:

```bash
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
```

### Letting other people try it, on your own network

This is a local run, not a deployment — `runserver` is behind it and it should not be
opened to the internet. Replace the address with yours (`ip -4 addr show | grep inet`):

```bash
DJANGO_DEBUG=False \
DJANGO_SERVE_MEDIA=True \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.42 \
python manage.py runserver 0.0.0.0:8000 --insecure
```

They then open `http://192.168.1.42:8000/`. Every part of that line is load-bearing, and
leaving one out is silent rather than loud:

| Part | Drop it and… |
|---|---|
| `0.0.0.0:8000` | the server listens on loopback only and **nobody else can connect**; |
| `DJANGO_ALLOWED_HOSTS` with your IP | every request answers **400 Bad Request**; |
| `--insecure` | Django stops serving `/static/` once `DEBUG` is off, so **the CSS and JS 404** and the whole site renders unstyled; |
| `DJANGO_SERVE_MEDIA=True` | `--insecure` covers `/static/` only, so **all ~1,500 audio files 404**; |
| `DJANGO_DEBUG=False` | any 500 shows the visitor your settings, including the database password and `SECRET_KEY`. |

Run it against the **mirror** database, which is what `manage.py` already points at: the
accounts and attempts testers create then stay in the throwaway copy.

`check --deploy` reports five warnings here and four of them are correct as they are:
HSTS, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` all assume
HTTPS, and switching them on would break login and make the site unreachable over plain
HTTP on a LAN. The fifth, `ALLOWED_HOSTS`, is what the line above sets.

Two limits worth knowing before you collect feedback: `django.views.static.serve` does not
support Range requests, so audio **plays but cannot be scrubbed** to a position; and there
is no rate limiting, so a person on the network could brute-force a password.

## Loading the content

The files in the repository are the source of truth; the database is built from them. If
the two ever disagree, the file wins and the database is re-imported.

```bash
python manage.py import_a1_words --no-audio   # 1,018 words, from vocabulary/data/*.json
python manage.py import_a1_words --check      # compare, write nothing
python manage.py seed_a1_course               # 24 lessons, grammar, sentences, word links
python manage.py seed_a1_course --check       # validate, write nothing
```

Both are safe to re-run, and both have a `--check` mode — the fast way to confirm the
content files and the database still agree.

Authored exercises are reproducible too:

```bash
python manage.py export_a1_exercises   # database -> exercises/data/a1_exercises.json
python manage.py import_a1_exercises   # exercises/data/a1_exercises.json -> database
```

The export stores references as **text rather than primary keys** (`hallo::OTHER` for a
word, the title for a grammar topic, the German sentence itself), so it lands correctly
on a fresh database. The import matches on natural keys — `(lesson, order)` for an
exercise, `(exercise, order)` for a question, `(question, order)` for an answer — rebuilds
the `QuestionTarget` rows, and never deletes answers, so a learner's stored
`ExerciseAttempt` survives it. The whole import runs in one transaction.

Listening exercises are generated, not authored:

```bash
python manage.py seed_a1_exercises --dry-run   # report first
python manage.py seed_a1_exercises
```

It takes a few of each lesson's own sentences and asks two questions about every one —
*what does it mean* (Persian options) and *which German sentence did you hear* (German
options) — pointing the question's audio at the sentence's existing MP3 rather than
generating a copy. It **deletes and rebuilds** its own output on each run, and the
deletion is scoped to `LISTENING` exercises, so authored exercises are never touched.

> That delete is gated: if any `ExerciseAttempt` exists, the command refuses to run
> unless you pass `--yes-replace-history`. `--dry-run` reports what it would delete.

Vocabulary and grammar drills are generated the same way:

```bash
python manage.py seed_a1_word_drills --dry-run   # report first
python manage.py seed_a1_word_drills
```

Each lesson's own new words (`LessonWord` with `role=NEW`) become four kinds of question,
all built from facts the `Word` row already stores:

| Drill | Question | Where the answer comes from |
|---|---|---|
| معنی | `واژهٔ «X» به چه معنی است؟` | `Word.meaning_fa`; wrong options from the same lesson |
| آرتیکل | `«___ X»` | `Word.article` — `der` / `die` / `das` |
| جمع | `جمعِ «der X» کدام است؟` | `Word.plural`; wrong options from the same lesson |
| Perfekt | `فعل «X» در Perfekt با کدام فعل کمکی می‌آید؟` | `Word.perfect_auxiliary` — `haben` / `sein` |
| نوشتن | `ترجمهٔ «ماشین» به آلمانی؟` | typed, `Word.word` — one answer row, so the runner asks for text |

It is what makes **every one of the 1,018 words** the tested item of a question — and
`WordProgress` only moves when a word is really tested, so without it 870 words could be
listed but never practised. The typed drill exists because recognition is not production:
picking `Auto` out of four options does not prove the learner can write it. Its accepted
answer is the **bare** word (`Land`, not `das Land`), which is exactly what the authored
«ترجمهٔ … به آلمانی؟» questions already accept, so both kinds of typed question are graded
the same way.

Four rules worth knowing. A word that already has an **authored** question gets no second
meaning question, and a word that already has an authored **typed** question gets no second
writing question — the drills being replaced do not count as covering their own words, or a
second run would read its own output as existing content and build almost nothing. The three
grammar drills skip nothing, because nothing asked about an article, a plural or a perfect
auxiliary before them. A meaning or writing question carries **no** grammar target, and a
question is tagged with a rule only when it really asks about that rule — because the
authored questions cannot be tagged at all: nothing in them records which rule they exercise,
and a lesson teaches three or four topics, so a lesson-level tag would make "grammar
accuracy" a relabelled copy of vocabulary accuracy. And a question with no honest wrong
options is **dropped** rather than written without them, which is why there are 437 plural
questions and not 440.

A lesson that introduces no word at all is a **review lesson** (lesson 12, `Wiederholung
A1.1: Das kann ich jetzt`). It gets the same five drills, built from the words it
**revisits** (`LessonWord` with `role=REVIEW` — 40 words there) rather than the ones it
introduces. Without that fallback the one lesson whose whole job is to ask again would have
nothing to practise.

`--batch` only changes how the questions are split, never which ones exist. The command
rebuilds its own output only, identified by its `تمرین واژگان` / `تمرین گرامر` / `تمرین نوشتن`
title prefixes, and carries the same `--yes-replace-history` gate.

Sentence reading drills come from the sentences the lessons already have:

```bash
python manage.py seed_a1_sentence_drills --dry-run   # report first
python manage.py seed_a1_sentence_drills
```

352 sentences are published, each with a Persian translation, and before this only three per
lesson were ever asked about — by ear, in the listening exercise. The rest were shown in the
lesson and never returned. This command asks about them in three directions:

| Drill | Question | Where the answer comes from |
|---|---|---|
| معنی | `معنیِ این جمله کدام است؟` | the German sentence renders as the LTR passage; four Persian translations, wrong ones from the whole level |
| کدام جمله | `کدام جملهٔ آلمانی این معنی را میرساند؟` | the Persian meaning is in the prompt; four German sentences |
| مرتب کردن | `این جمله را با ترتیب درست واژه‌ها بنویس.` | a `SCRAMBLE`: the sentence's words are shown shuffled and the learner types them back in order; the one correct `Answer` row is the sentence itself |

A sentence another exercise already asks about is left alone, and the command finds that in
the rows rather than guessing: authored reading questions point at their sentence with a
`CONTEXT` target, and the listening questions — written before question targets existed — are
recognised by the audio file they play (72 sentences). A sentence question carries **no** word
target, so it never moves `WordProgress`: a learner who misreads a sentence has not said which
word they misread. The wrong options come from the whole level rather than the lesson, because
a lesson's sentences are usually one short text and four options taken from one text are
recognisable as a set instead of being read.

The scramble is the one direction that asks for **production** rather than recognition: the
first two let a learner pick a sentence out of four, which says nothing about being able to put
German word order together, so the third shows the sentence's words shuffled and asks for the
sentence. The words are derived from the single correct `Answer` row by `exercises/runner.py`
(seeded by the question, so two page loads agree), which is why the command stores no scrambled
order of its own and the answer — the order — is never in the page. It is a `SCRAMBLE` exercise,
the one kind the runner decides from the exercise's own type instead of from its answer count.
A one-word sentence gets no scramble (there is no order to get right), and a scramble is left out
of every mock-exam section, because the exam draws questions from many exercises at once and has
no word bank to show it with.

Sound discrimination is the one listening skill nothing else in the product touched, so it
gets its own drill — and it needs no microphone, because *hearing* a contrast is what you
cannot fake with speech recognition:

```bash
python manage.py seed_a1_pronunciation_drills --dry-run   # report first
python manage.py seed_a1_pronunciation_drills
```

One word is played and the learner says which of two words it was. The wrong option is the
word one sound away (`schon` / `schön`, `nein` / `neun`, `Uhr` / `Ohr`), so the choice is a
discrimination rather than a guess, and the prompt names the difference in Persian. Two
options, never four: there is exactly one honest distractor for a minimal pair.

The pairs are not written down anywhere. `exercises/data/pronunciation_pairs.py` lists fifteen
**contrasts** — two spellings that stand for two different sounds — and the command substitutes
one for the other inside every word of the level, keeping the result only when it spells
another published word. So a pair exists exactly when the course really contains both words,
and the drill can never invent vocabulary. On the course as it stands: **38 pairs, 69 questions,
24 exercises, in 22 of the 24 lessons** — with the first words of a pair taught in one lesson
and its partner in another, which is exactly why the pool is the level and not the lesson. A
word with no recording is skipped rather than played silently.

A pronunciation mistake is **about two words at once**, so a question carries no
`QuestionTarget` at all: naming either word as "the one you got wrong" would move
`WordProgress` on a question that never asked what the word means, and would make the
vocabulary drills treat the word as already asked. The attempt is still recorded, so accuracy
and history see it.

### Dictation

Hearing a word and writing it is the other half of ear training, and the one that needs no
microphone at all: the learner types, and the verdict is the same typed-answer comparison the
rest of the product already uses.

```bash
python manage.py seed_a1_dictation_drills --dry-run   # report first
python manage.py seed_a1_dictation_drills
```

A word is played and the learner writes it. Nothing new was needed to render it: a question
with **exactly one answer row** is what makes `exercises/runner.py` show an input instead of
options, the audio is the word's own recording, and a word with no recording is skipped. This
is the exercise that trains `ü`, `ö`, `ä`, `ß`, `ie` against `ei`, and doubled consonants —
things that are learned by hearing a word, never by reading it.

Unlike the sound drill, this question **does** carry a `TESTED_ITEM` target on the word it
plays. A dictation is about one word — the learner heard it and spelled it — so a miss is a
fact about that word, and it has to move `WordProgress` to be reviewable later. That is why
`exercises/generated.py` exists: the vocabulary drills ask "does this word already have a
question?", and the honest answer counts **authored** questions only. Without it, every
dictated word would silently lose its meaning drill.

On the course as it stands: **182 exercises, 1,051 questions, 1,012 words**. Two spellings that
differ only in case (`sie` / `Sie`, `essen` / `Essen`) are dictated once per lesson, because
grading already ignores case and the second question would be the first one asked twice.

### Reading

The course practised reading one line at a time — a single German sentence with its meaning
on offer — which is a translation question wearing a reading label. A1 LESEN asks the learner
to hold a text together and find something *in* it, so every lesson now gets one.

```bash
python manage.py seed_a1_reading_drills --dry-run   # report first
python manage.py seed_a1_reading_drills
```

The text is the lesson's own dialogue (or its first sentences, when it has no dialogue), three
to four consecutive lines, and the questions are the two things an A1 reading task asks: which
line of the text carries this meaning, and which sentence is **not** in the text. The wrong
options to the first are the text's own other lines, so the question can only be answered by
reading it.

On the course as it stands: **24 exercises, 120 questions** — one per lesson. No word target is
written: a learner who misreads a text has not said which word they misread.

### Wortliste coverage

The course's A1 claim is checked against the official list rather than asserted:

```bash
python manage.py report_a1_wortliste         # summary and the words still missing
python manage.py report_a1_wortliste --all   # every missing entry
```

The official Goethe A1 Wortliste (~650 main entries) is kept as data at
`vocabulary/data/wortliste/a1.json` — in a **subdirectory**, because `import_a1_words` loads
every `*.json` directly under `vocabulary/data/` and the official list must never be imported
as course words. Each entry is stored exactly as the PDF prints it (`die Adresse, -n`, `all-`,
`(sich) anmelden`), so it stays traceable to its source; the PDF itself is not committed.

Matching folds the dictionary notation away, not the words: a leading article and the plural
marker after the comma are dropped, `/` and `(...)` are tried both ways, `(sich) X` counts both
with and without the pronoun, and an entry ending in `-` is a stem (`all-` for *alle, alles,
allen*) matched by prefix and reported separately — the one place a match is not exact. It is a
report, not a gate: it always exits 0.

On the course as it stands: **626 of 628 main entries covered (99.7%)**. Five of the original
seven gaps were real vocabulary and are now taught — `ab`, `abfahren`, `der Arbeitsplatz`,
`circa`, `Lieblingsfach`. The two left are covered by other means rather than by a duplicate
row: `der, die, das` is the `Artikel` grammar topic plus the `article` field on every noun,
and `bisschen` is taught as the phrase `ein bisschen`. Another **392** taught words lie beyond
the exam list, because the course is deliberately wider than the exam.

### The exam mode

The exam's own numbers are data, not prose: `exams/spec.py` records the sections, their
minutes, their items, the ×1.66 factor, the 75/25 written-oral split, the 60-point pass mark,
the written minimum below which the oral part cannot save the exam, and the source they came
from (the Goethe Durchführungsbestimmungen, Stand 1. September 2025).

A sitting takes 15 questions per section from the product's own published drills — hearing
from the questions that carry a recording, reading from the questions that carry a passage,
writing from the questions answered by typing — writes the paper it chose into
`ExamRunQuestion`, and runs it on one 65-minute clock held by the server: closing the tab
does not pause it, refreshing does not extend it, and the submission endpoint refuses answers
once the time is over. Answers are graded by `exercises/grading.py` like every other answer,
recorded as `ExerciseAttempt` rows (so the review plan, «آمادگی من» and «امروز» see them too),
and snapshotted onto the paper's own row — which is what keeps a finished sitting's score the
sitting's score.

Live pools on the course as it stands: **1,269 questions for HÖREN, 367 for LESEN and 2,118
for SCHREIBEN**, so a paper is never short of 15 per section.

Two limitations are stated on the page rather than papered over. The mock reproduces the
exam's *shape*, not its task types, because the questions are this product's own. And the
spoken section — 15 minutes and 25 of the 100 points — is **not graded here**: the exam marks
it with two examiners against criteria, and nothing in this product grades speaking. So the
score page answers "did I pass?" honestly instead: it says how many of the spoken 25 points
would still be needed, and when a written score is below 35 it says that even a perfect oral
section could not reach 60 — the exam's own rule. `/exam/sprechen/` is the rehearsal: the
three official parts, the phrases a candidate has to be able to say, and for each phrase the
real questions that practise the course sentence it matches (all 24 phrases today).

Starting a sitting needs an account, because a sitting is stored; the shape of the exam, the
scoring and the instruction words are public, and the glossary marks which of the official
task-sheet words the course teaches (all 10 today).

### Audio

`/media/` is gitignored, so a fresh clone has no audio files. They are generated:

```bash
python manage.py import_a1_words              # word audio, during the import
python manage.py generate_sentence_audio      # sentence audio
python manage.py generate_grammar_audio       # grammar audio
python manage.py generate_lesson_content_audio
```

Each takes `--dry-run`, `--limit`, `--retries` and `--workers`, and only ever fills in
rows that have no audio yet. They need network access (for the speech service) and
`ffmpeg` installed, and they narrate **German only** — the Persian translation that sits
beside a sentence is stripped first (`vocabulary/german_text.py`).

Other useful commands:

```bash
python manage.py validate_a1_content   # read-only content checks
python manage.py export_a1_content     # dump the content back to CSV
python manage.py report_a1_wortliste   # official A1 Wortliste coverage, read-only
python manage.py report_a1_lesson_load # per-lesson word and question load, read-only
python manage.py audit_a1_exercises    # read-only exercise health (add --strict to fail on problems)
```

---

## Tests

```bash
.venv/bin/python manage.py test
```

**774 tests pass, 1 skipped.** The suite covers the models, the lesson journey, the  progress rules, the review schedule (the adaptive scheduler, the due queue and its limits, and that a submitted
  answer moves both), grading, the server-side endpoints, the runner, the review plan (words
  **and** rules), the theme choice (that a saved theme reaches the page, that an unknown one
  is refused, and that one learner's choice does not touch another's), the readiness
  arithmetic (course, exercises, vocabulary, grammar and
  deadline pace), the exam mode (the official numbers, the paper, the scoring incl. the
pass arithmetic, the deadline, and every page), the generated content commands, and a set
of project-wide template guards. Some tests seed content into a throwaway test database, so the run needs
permission to create one.

Use the project's virtualenv interpreter. The system `python` has no `psycopg` and every
management command will fail with `ImproperlyConfigured`.

Read-only fallback when a test database is not available:
`python manage.py validate_a1_content`.

---

## Accessibility and interface conventions

- Tap targets are at least 44px, or 24px where the design is deliberately dense.
- Status is never carried by colour alone — every state has a word attached.
- `prefers-reduced-motion` is honoured.
- The lesson page and the exercise runner are readable with JavaScript off. Every step
  and every question is server-rendered; scripts only *hide* and reveal. Controls ship
  `hidden` so a no-JS page never shows a button that would do nothing.
- German is `lang="de" dir="ltr"`; Persian UI copy follows the page's RTL.

---

## Known gaps

- `SPEAKING` and `WRITING` exercise types are defined in the model and shown in the
  interface, but no exercise uses them — there is no free-text or spoken grading.
- Listening questions have no `QuestionTarget`, so answering one does not move
  `WordProgress`. They test listening, not a single word.
- Only **4 of the 75** grammar topics the course teaches have any question tagged against
them (the article, plural and two Perfekt topics, from the generated drills). The other
  71 rules have no practice at all, so «آمادگی من» cannot measure them and says so with
  its own computed figure. `QuestionTarget` supports a `GRAMMAR` target and the role
exists — this is a content gap, not a code one.
- Every one of the 1,018 words is now the tested item of a question, so a missed word can
  always be practised. That is new: the authored exercises only covered 138 of them, and
  the generated vocabulary drills are what closed the rest.
- The goal form offers the levels that exist in the database, and today only A1 does — a
  learner aiming at B1 cannot say so yet. The code already handles a target above the
  built content (`goal_of` reports `covers_target`); adding an A2/B1 level and course is a
  content decision, not a code change.
- Anonymous progress is not merged into an account on signup.
- No CI pipeline.
