# گام‌به‌گام — GamBeGam

A German-learning platform for **Persian speakers**, covering CEFR level **A1**.

The interface is Persian and right-to-left; German content is always rendered
`lang="de" dir="ltr"`, so a German sentence never inherits the page's direction.

---

## What it does

- **24 lessons** across one published course, presented as a guided *journey* rather than
  a wall of text. Each lesson is a sequence of steps — intro, explanation, vocabulary,
  grammar, examples, dialogue, reading, listening, practice, finish — and a lesson only
  gets a step when it actually has the material for it.
- **A vocabulary reference** of 1,008 words with search, level tabs, per-word audio, and
  the real lessons that teach each word.
- **111 exercises** across six question shapes (multiple choice, true/false, reading,
  fill-in-the-blank, translation) with **server-side grading**.
- **Progress that is actually stored.** Signed in, `LessonProgress`, `ExerciseAttempt`
  and `WordProgress` are the record; anonymous visitors get a `localStorage` layer behind
  one module (`static/js/progress.js`).
- **A review surface** built from the learner's own mistakes, and per-exercise results
  that survive a reload.
- **Generated audio** for every word, grammar topic, sentence and lesson block
  (~1,500 MP3 files).

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
system is a set of CSS custom properties in `static/css/base.css`, and the interface is
**dark-only**.

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

Create the database and a user, then point `config/settings.py` at it:

```sql
CREATE DATABASE language_learning;
CREATE USER django_user WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON DATABASE language_learning TO django_user;
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> **Note:** `SECRET_KEY`, `DEBUG` and the database credentials are currently written
> directly into `config/settings.py`. Moving them to environment variables is a known
> to-do; do not deploy this configuration as it stands.

---

## Loading the content

Two commands reproduce almost all of the content from files in the repository:

```bash
python manage.py import_a1_words      # 1,008 words, from vocabulary/data/*.json
python manage.py seed_a1_course       # 24 lessons, grammar, sentences, word links
```

Both are safe to re-run. `seed_a1_course --check` validates the data modules and writes
nothing, which is the fast way to confirm the content files are still consistent.

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

> The 111 **authored** multiple-choice, true/false, reading, fill-in-the-blank and
translation exercises are still not reproducible from files: they exist only in the
database they were written in. A fresh clone gets the generated listening exercises and
nothing else.

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
```

---

## Tests

```bash
python manage.py test
```

The suite covers the models, the lesson journey, the progress rules, grading, the
server-side endpoints, the runner, and a set of project-wide template guards. Some tests
seed content into a throwaway test database, so the run needs permission to create one.

Use the project's virtualenv interpreter (`python` from the activated venv). The system
interpreter has no `psycopg` and every management command will fail with
`ImproperlyConfigured`.

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

- The 111 authored exercises are not reproducible from files (see above); only the
  generated listening exercises are.
- `SPEAKING` and `WRITING` exercise types are defined in the model and shown in the
  interface, but no exercise uses them — there is no free-text or spoken grading.
- Listening questions have no `QuestionTarget`, so answering one does not move
  `WordProgress`. They test listening, not a single word.
- Anonymous progress is not merged into an account on signup.
- `LANGUAGE_CODE` is `en-us`, so Django's own password-validator messages appear in
  English on an otherwise Persian interface.
- Three detail views have no `is_published` guard (`WordDetailView`,
  `ExerciseDetailView`, `ExerciseSubmitView`).
- No CI pipeline.
