# AGENT_MEMORY.md

Internal notes for future coding agents. **Never store passwords, API keys, tokens or secrets here.**

Last updated: Phase 9 — frontend audit, responsive polish & branded error pages.

---

## 1. Project

Django German-learning platform (CEFR A1) for **Persian-speaking** learners. UI is
**Persian, RTL (dir="rtl")**; German content is rendered `lang="de"` / `dir="ltr"`.

- **Stack:** Django **6.1.1**, PostgreSQL, server-rendered Django templates, vanilla
  JS + hand-written CSS. **No DRF, no bundler, no JS framework, no npm.**
- **Note:** `AGENTS.md` claims "Django 4.2 + DRF" — that is **out of date**. There is no
  DRF in `requirements.txt` (Django + edge-tts only).
- Run commands (see `AGENTS.md`): the project lives in `Language_Learning/`.

### Apps
| App | Notes |
|---|---|
| `accounts` | `UserProfile` model only (user, current_level, native_language). No views/urls yet. |
| `lessons` | `LanguageLevel → Course → Lesson → LessonContent / LessonWord / LessonGrammar / LessonSentence`. |
| `vocabulary` | `Word`, `Grammar`, `Sentence`. Includes AJAX `vocabulary:word-lookup`. |
| `exercises` | `Exercise → Question → Answer / QuestionTarget`. |
| `tests` | **Stub** (empty models/views/urls). Not implemented. |

### Data of record
- Lessons/grammar/sentences/words are reproducible from `lessons/data/*` and
  `vocabulary/data/*.json` via `import_a1_words` and `seed_a1_course`.
- **Exercises are NOT reproducible** — there is no seed/generate command for them;
  the 111 exercises exist only in the database. (Known issue, see §5.)
- Live data: 1 level (A1), 1 course, 24 published lessons, 143 content blocks,
  1,305 word links, 75 grammar topics, 339 sentences, 1,008 words (100% audio),
  111 exercises / 296 questions / 755 answers (all published).
- `/media/` (all generated audio, ~1,541 files) is **gitignored** — a fresh clone has
  no audio files. QA of audio depends on local media.

---

## 2. Frontend redesign — decisions (approved)

| Decision | Choice |
|---|---|
| Stack | Keep server-rendered Django templates + enhanced vanilla JS/CSS. No bundler, no DRF. |
| Theme | **Dark-only**, single polished theme. The light/dark toggle was removed. |
| Auth | Django built-in `LoginView` / `LogoutView` + a `UserCreationForm` subclass. **No new user model, no migrations.** Implemented in Phase 2. |
| Access model | Anonymous-first: everything browsable, login optional. |
| Desktop nav | RTL sidebar + content. Mobile: bottom nav. |
| Brand | Working name **«گام‌به‌گام» / GamBeGam** (not permanently locked). Logo = Concept 3 "monogram + path", implemented as inline SVG in `templates/includes/brand.html`. The name lives in **`settings.BRAND`** — rename it there only. |
| Logo/fonts | Custom inline-SVG wordmark. **No external webfont dependency.** |
| Local progress | `localStorage` behind a `progress.js` module — still the behaviour for **anonymous visitors** (see §6). |
| Learner progress (Phase 8) | Backend-owned: `LessonProgress`, `ExerciseAttempt`, `WordProgress`. Signed in → the server is the source of truth; anonymous → `localStorage`. |

### Out of scope for the frontend redesign
Progress models, SRS backend, subscription, premium/trial entitlement, payment,
AI backend, DRF, new learning/content models, **database migrations**.

**That was the redesign's scope, not a standing ban on the project.** Phase 8 (below) was
asked for by the user and added the three progress models, their migrations and two JSON
endpoints. Before refusing a change because of the paragraph above, read §3 for the current
phase. Still **not** in scope until someone asks: SRS/mastery fields (`mastery`, `is_known`,
`next_review_at`, `review_streak`, `difficulty`), `CourseProgress`, `StudySession`, any
analytics or streaks.

---

## 3. Current phase / status

**Phase 0 — Design foundation: COMPLETE.**
**Phase 1 — App shell & navigation: COMPLETE.**
**Phase 2 — Authentication: COMPLETE.**
**Phase 3 — Dashboard: COMPLETE.**
**Phase 4 — Learning path: COMPLETE.**
**Phase 5 — Lesson journey: COMPLETE.**
**Phase 6 — Exercise experience: COMPLETE.**
**Phase 7 — Vocabulary, grammar, dialogue & listening polish: COMPLETE.**
**Phase 8 — Backend progress integration: COMPLETE.** `exercises/0003` (`response_text` +
nullable `answer`) was applied with the user's explicit approval, and both browser passes are
green (see §8).
**Phase 9 — Frontend audit, polish & error pages: COMPLETE.** Not a redesign either. Every
route was opened in Chromium at 390/768/1024/1440 and the fixes are the ones the rendered
pages actually proved (see §8 for the check counts and §5.9/§5.10 for what is left).
**Phase 10 — Backend coding style (the `accounts` style): COMPLETE.** Not a redesign and not a
behavior change. Every Python file in the project was rewritten in the simple, read-it-top-to-
bottom style the user wrote `accounts` in (see §7): no type hints, no `getattr`/`setattr`, no
single-use private helpers where a plain line works, plain `if`/`elif`/`else` instead of
compact expressions, and label lookups as explicit `if key in dict` instead of
`dict.get(key, default)`. **JS, CSS and HTML were deliberately left alone** — the user is
handling the frontend separately. `manage.py check` and `makemigrations --check` are clean, and
the whole runnable test set is green (§8). The pass also turned up two pre-existing problems:
the stale `accounts` tests (fixed, §5.31) and a missing `vocabulary.german_text` module that
breaks two audio commands (§5.30, still open).

Phases ahead (approved order):
10. (next brief not issued yet — a cross-lesson completion/review surface was still open
   when Phase 7 was reported)
11. QA

A short Phase 7 recap: the vocabulary app was rebuilt on the product's own components, the
lesson journey's grammar/dialogue/vocabulary presentation was polished, and there is now
**one** audio system for the whole product (`templates/includes/audio_control.html` +
`static/js/audio.js`) instead of three.

A short Phase 9 recap: the multi-line `{# #}` bug from Phase 0 had **regressed** (4 leaks,
one of them added in Phase 8) — fixed, and now guarded by `tests/tests.py`. Disabled `.btn`
controls had no styling at all, so the stepper's ends and the finish button now look
inactive. The learning path and the exercise index got their *effective* tap areas measured
(a stretched `::after` makes the whole card the target) instead of their anchor box. Two new
branded error pages, `templates/404.html` (extends the app shell) and `templates/500.html`
(standalone — Django renders it with no context), plus the missing favicon, which removes the
last console error on every page.

A short Phase 8 recap: not a redesign. The three progress models and their migrations
**already existed in the repo with no code behind them**; Phase 8 wired them up — a
server-side grading endpoint that writes `ExerciseAttempt` rows and moves `WordProgress`
counters, a lesson-progress endpoint that saves the resume step and completion, and two new
modules (`lessons/progress.py`, `vocabulary/progress.py`, `exercises/grading.py`) holding the
rules. The frontend kept its architecture: `progress.js` stayed the single interface, so
`lesson_status.js`, `dashboard.js` and `path.js` needed **no changes at all**.

---

## 4. Files changed

### Phase 0 — design foundation

| File | Change |
|---|---|
| `static/css/base.css` | Rewritten as the single **dark-only** token source. Added legacy token aliases. Removed theme-toggle styles. |
| `templates/base.html` | `color-scheme` → dark; removed the pre-paint theme script and all theme-toggle JS. Nav/messages JS kept. |
| `templates/includes/navbar.html` | Removed the light/dark toggle button. |
| `lessons/templates/lessons/lesson_detail.html` | Added `data-lookup-url` to the reader container (revives word lookup). |
| `lessons/static/lessons/js/lesson_reader.js` | Container selector → `.reader-page[data-lookup-url]`; tokenised element list updated to current reader classes. |
| `lessons/static/lessons/css/reader_modern.css` | Lightened three light-mode-only text colours (grammar + note badges, listening role) so they stay legible on the dark-only theme. |
| `exercises/static/exercises/css/exercise.css` | Lightened two light-mode-only text colours (exercise type badge, context tag). |
| `vocabulary/tests.py` | Replaced the theme-toggle assertion with a dark-theme assertion (deliberate, see §6). |
| `AGENT_MEMORY.md` | Created. |

### Phase 1 — app shell & navigation

| File | Change |
|---|---|
| `config/context_processors.py` | **New.** Single source of truth for `brand`, `nav_items` and `home_url`; resolves each nav URL and derives the active state from the request's `app_name`. |
| `config/settings.py` | Added the `BRAND` dict and registered `config.context_processors.shell`. |
| `config/urls.py` | Added a **named** `home` route (`/` → lessons list) as a temporary stand-in for the Phase 3 dashboard. |
| `templates/base.html` | Rewritten as the app shell: sidebar + content on desktop, app bar + bottom nav on mobile. Removed the old mobile dropdown JS. |
| `templates/includes/sidebar.html` | **New.** Desktop sidebar with brand, nav and account foot. |
| `templates/includes/app_bar.html` | **New.** Mobile top bar. |
| `templates/includes/bottom_nav.html` | **New.** Mobile bottom navigation. |
| `templates/includes/nav_links.html` | **New.** Shared link list rendered by *both* navigation surfaces. |
| `templates/includes/nav_icon.html` | **New.** Inline line icons keyed by `NAV_ITEMS[].icon`. |
| `templates/includes/brand.html` | **New.** Concept 3 monogram mark + two-tone wordmark. |
| `templates/includes/navbar.html` | **Deleted** — replaced by the shell partials. |
| `static/css/shell.css` | **New.** Sidebar, app bar, bottom nav, brand mark, shell breakpoints. |
| `static/css/base.css` | Removed the replaced top-navbar rules and their media queries; tokens and primitives unchanged. |
| Lesson / vocabulary / exercise templates | Page titles and the word-detail breadcrumb read the product name from `settings.BRAND` instead of a hardcoded string. |

### Phase 2 — authentication

| File | Change |
|---|---|
| `accounts/signals.py` | **New.** `post_save` receiver on `User` that creates the matching `UserProfile` (`created` guard keeps it off the `last_login` saves). Code only — no model, no migration. |
| `accounts/apps.py` | `ready()` imports the signals module so the receiver is registered. |
| `accounts/forms.py` | **New.** `LoginForm` (subclasses `AuthenticationForm`) and `SignUpForm` (subclasses `UserCreationForm`, adds optional email). Persian labels/help text, Persian messages for the common errors, shared `field__input` class on every widget. |
| `accounts/views.py` | **New.** `signup` (creates the account, signs the user in, redirects to profile) and `profile` (login-required, `get_or_create`s the profile). |
| `accounts/urls.py` | **New** `app_name = "accounts"` with `login/`, `logout/`, `signup/`, `profile/`. Login uses `redirect_authenticated_user=True`. |
| `config/settings.py` | `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`. |
| `templates/includes/account_menu.html` | **New.** One account control rendered by the sidebar *and* the app bar (anonymous → login/signup; signed in → profile + POST logout). |
| `templates/includes/sidebar.html`, `app_bar.html` | Now include the shared account menu. |
| `accounts/templates/accounts/` | **New:** `login.html`, `signup.html`, `profile.html`, `_form_fields.html`. |
| `static/css/auth.css` | **New.** Auth layout plus `.panel` / `.field` / `.btn` / `.detail-list` primitives, loaded only by the auth pages. |
| `static/css/shell.css` | Added `.account__*` styles and a ≤430px rule that drops the app-bar signup pill so the header never overflows. |
| `accounts/tests.py` | **New.** 18 tests (was an empty stub). |

### Phase 3 — dashboard

| File | Change |
|---|---|
| `lessons/views.py` | **New `DashboardView`.** One published course + its published lessons (real rows only), the word/exercise totals for the quick actions, and a `lessons_payload` of `{id, order, title, minutes, url}` handed to the browser. Nothing personal is read or claimed server-side. |
| `config/urls.py` | `/` now renders `DashboardView` instead of redirecting to the lessons list. |
| `config/context_processors.py` | Added the **داشبورد** nav item (matched by `view_name` because the route lives at project level) and an icon key for it. |
| `templates/includes/nav_icon.html` | Added the `home` icon. |
| `templates/dashboard.html` | **New.** The product home: continue-learning card, honest local progress, recent device activity, course/level card, quick actions, path preview, empty states, optional account CTA. |
| `static/css/dashboard.css` | **New.** Dashboard-only layout + breakpoints. |
| `static/css/components.css` | **New.** `.panel` / `.btn` / `.muted` promoted out of `auth.css` once a second page needed them; now loaded globally by `base.html`. |
| `static/css/auth.css` | Its duplicated primitives were removed in favour of `components.css`. |
| `static/js/progress.js` | **New.** The entire `localStorage` abstraction (`window.GamProgress`) — see §6. |
| `static/js/dashboard.js` | **New.** Layers local progress onto the server-rendered page (continue card, bar, activity, path window). The page is complete without it. |
| `static/js/lesson_visit.js` | **New.** The single writer: records that a lesson was opened. |
| `templates/base.html` | Loads `components.css` and `progress.js` globally. |
| `lessons/templates/lessons/lesson_detail.html` | `data-lesson-id` on the reader container + loads `lesson_visit.js`. |
| `lessons/tests.py` | Added `DashboardTests` (9 tests) and the imports for them. |
| `accounts/tests.py` | The old “home redirects to the lessons list” assertion became “home renders the dashboard anonymously” — `/` is a real page now. |

**Design rule for this page:** it answers *where am I*, *what is next*, *how do I continue* —
and nothing else. It must never grow into an analytics/admin dashboard, and it must not
invent statistics. Anything personal comes from the browser, and the page says so.

### Phase 4 — learning path

| File | Change |
|---|---|
| `lessons/views.py` | `LessonListView` rebuilt as the path: **no pagination**, one group per published course (with a level), in level order. `CourseDetailView` reuses the same context builder for a single course. Added shared helpers `_lesson_payload()`, `_published_courses()` and `_path_context()` — the dashboard now calls `_lesson_payload` too instead of building the same rows inline. |
| `lessons/templates/lessons/lesson_list.html` | Rewritten from a card grid into the trail: header, progress bar, next-step row, level tabs, per-course group, and a `<ol>` of steps. Still the same template name, so `course_detail.html` (which extends it) and the `lesson-list` URL name are untouched. |
| `lessons/static/lessons/css/lesson_path.css` | **New.** The trail: spine, markers, step cards, the five step states, and a deliberately re-proportioned mobile layout. |
| `lessons/static/lessons/css/lessons.css` | Removed the now-unused grid rules (`.lesson-grid`, `.lesson-tile*`, `.lesson-meta`, `.lesson-summary`) and narrowed the media queries to what is still used. |
| `static/js/lesson_status.js` | **New, shared.** Pure classification: completed / current / started / upcoming / available, plus counts and percent. No DOM, no copy. Loaded globally by `base.html`. |
| `static/js/path.js` | **New.** Paints the trail from `progress.js` + `lesson_status.js`. |
| `static/js/dashboard.js` | Refactored onto `lesson_status.js` — the dashboard and the path now share one definition of "the current lesson". Also handles the all-lessons-finished case instead of still offering lesson 1. |
| `static/css/components.css` | Added the `.progress` / `.progress__fill` primitive (one progress bar for both pages). |
| `static/css/dashboard.css` | Dropped `.dash-bar*` in favour of the shared primitive. |
| `templates/dashboard.html` | Uses `.progress`; the count label now says **کامل‌شده** (see the measure note in §7). |
| `lessons/tests.py` | Added `LearningPathTests` (11 tests). |

**Path-state logic (the important part).** `lesson_status.js` owns it, and both pages
read it, so they cannot disagree:

- **current** = the lesson last opened *if it is unfinished*, otherwise the **first lesson
  not yet finished**. `currentId` is `null` only when the whole course is finished.
- **completed** = `status === "completed"` in localStorage.
- **started** = opened before but neither completed nor the current step.
- **upcoming** = not opened and further along than the current step.
- **available** = not opened but not further along (or nothing is current yet).
- Lesson order comes from the **payload order**, which the server builds in `Lesson.order`
  order. If a course ever needs different sequencing, that is the single place to change.

**Visual rule (do not regress this).** `upcoming` is a *position on the trail*, not a lock.
Nothing is gated in this phase, so upcoming steps get **no dimming, no locked styling** — the
only signal is the spine: solid behind you, dashed ahead. An earlier draft dashed and muted
the cards, which a new learner would reasonably read as "these lessons are unavailable".
Status is never carried by colour alone either: every step has a text chip and completed
steps swap their number for a check mark.

### Phase 5 — lesson journey

The lesson page stopped being a document and became a sequence of small steps. **Step
order, labels, counts and the partial that renders each step are defined in exactly one
place: `lessons/journey.py`.** A lesson only gets a step when the data for it exists.

| File | Change |
|---|---|
| `lessons/journey.py` | **New.** `build_journey(blocks, grammar_links, sentence_links, word_page, exercises)` → the ordered step list; `content_step_count()` for the agenda. No database writes, no knowledge of the browser. |
| `lessons/views.py` | `LessonDetailView` builds the journey from published rows only and passes `steps`, `journey_step_count`, `material_step_count`, `journey_percent`, `previous_lesson`, `next_lesson`. The vocabulary step is paginated (`WORDS_PER_STEP = 24`). |
| `lessons/templates/lessons/lesson_detail.html` | Rewritten: compact header, progress, chip row, every step rendered in full, one stepper bar, the lookup popover. |
| `lessons/templates/lessons/steps/` | **New partials:** `_intro`, `_vocabulary`, `_grammar`, `_sentences` (+ `_sentence`), `_practice`, `_finish`, and the shared `_agenda`, `_block`, `_lead`, `_word_card`. |
| `lessons/templates/lessons/_audio_control.html` | Reworked into one accessible control (button + real `<audio>` + `<noscript>` download fallback) reused by blocks, grammar topics, sentences and words (`icon_only=True` on word cards). |
| `lessons/static/lessons/css/lesson_journey.css` | **New.** Header, chips, steps, word/sentence/grammar/exercise lists, sticky mobile action bar, and transitions gated behind `prefers-reduced-motion: no-preference`. |
| `lessons/static/lessons/css/lessons.css` | Trimmed to the path furniture plus the shared audio control; the dead reader grid/tab rules are gone. |
| `lessons/static/lessons/css/reader_interactions.css` | **Deleted** — the last retired reader stylesheet (the rules that were still needed moved into `lesson_journey.css`). |
| `lessons/templates/lessons/_lesson_sidebar.html` | **Deleted** — included nowhere since the shell rewrite (old §5.4). |
| `lessons/static/lessons/js/lesson_steps.js` | **New.** The stepper: shows one step, syncs chips/progress/`#step-…`, remembers the step, and owns the "mark complete" button — revealed only when storage actually works. |
| `lessons/static/lessons/js/lesson_reader.js` | Container and `[data-lookup]` list updated for the journey markup; word cards are still excluded on purpose (no nested interactives). |
| `static/js/progress.js` | Added `positions` to the stored shape with `setLessonPosition(id, index)` / `lessonPosition(id)` so the stepper can resume. |
| `static/css/shell.css` | The lesson page gets a narrower reading column (`content--lesson`). |
| `lessons/tests.py` | Added `LessonJourneyTests` (18 tests). |
| `exercises/tests.py` | The lesson-page display test now asserts the journey's practice step (old §5.3). |

**How the journey is built (the important part).** `journey.py` maps real content to steps:

    intro · explanation · vocabulary · grammar · examples · dialogue · reading · listening · practice · finish

- `intro` and `finish` always exist; every other step appears **only if the lesson has it**.
  Live lesson 12 has no exercises and no dialogue, so its journey is
  `intro · explanation · vocabulary · grammar · examples · reading · finish`.
- Content blocks feed the step they belong to: `EXPLANATION` + `NOTE` → explanation,
  `VOCABULARY` → vocabulary, `GRAMMAR` → grammar, `EXAMPLE` → examples,
  `DIALOGUE` → dialogue. An unmapped block type falls back to the explanation step.
- Sentence roles earn one step each (`EXAMPLE`, `DIALOGUE`, `READING`, `LISTENING`), and a
  step appears if it has sentences **or** a prose block about it.
- `practice` lists the lesson's published exercises with a real question count and links to
  the existing exercise page. Grading is **not** reimplemented here.
- **Every step is rendered server-side in full.** The `.js` class (added in `base.html`) only
  *hides* the inactive ones, so with JavaScript off the lesson is one readable document, the
  stepper buttons are absent, and the completion button stays hidden.
- German is always `lang="de" dir="ltr"`; translations and UI copy follow the page's RTL.

**Do not put step copy in a template.** To add a step, give it an entry in `_STEP_SPEC`
(label, title, hint, unit, template) plus a partial — the chip row, the agenda, the counters
and the progress bar all read from that one definition.

**Django `{# … #}` comments are single-line only** (bug found and fixed in Phase 5). A
multi-line `{# … #}` is *not* a comment — Django emits it as literal text. That leaked **110
visible comment blocks per lesson page**, and because one of them contained the characters
`<audio>`, the browser parsed a stray media element that swallowed the real audio controls,
leaving every play button zero-sized and unclickable. All 13 offenders now use
`{% comment %} … {% endcomment %}`. Use that form for anything longer than one line.

### Phase 6 — exercise experience

The exercise list and the exercise page were redesigned, and the two stylesheet
inconsistencies from §5.14 are gone (see "CSS cleanup" below). The lesson journey is
untouched: its practice step still just links to the exercise page.

| File | Change |
|---|---|
| `exercises/runner.py` | **New.** `build_runner(exercise)` → the question list the runner renders (kind, options, expected answers, passage, explanation, media), `scoreable_count()`. Presentation facts only — no DB writes, no grading. |
| `exercises/views.py` | `ExerciseListView`: published exercises of published lessons in published courses only, with a `question_count` annotation, plus `question_total` / `lesson_count`. `ExerciseDetailView`: builds the runner context and finds the next published exercise in the same lesson. |
| `exercises/models.py` | Added `TYPE_LABELS` / `DIFFICULTY_LABELS` and the `type_label` / `difficulty_label` **properties** (Persian). Properties only — no field, so **no migration** (`makemigrations --check` is clean). `get_type_display()` stays English for the admin. |
| `exercises/templates/exercises/exercise_list.html` | Rewritten. Unscoped: grouped by lesson (a heading per lesson + a 4–5 card grid) instead of 111 identical cards. Scoped (`?lesson=N`): one header + cards with the instruction. Real empty states. |
| `exercises/templates/exercises/_exercise_card.html` | **New.** One card, shared by both list modes; the whole card is the single action, so the CTA is a `<span>` (no nested interactive). |
| `exercises/templates/exercises/exercise_detail.html` | Rewritten as the runner: every question server-rendered, one on screen, hidden answer material, inline feedback, results state. No inline JS left in the template. |
| `exercises/static/exercises/css/exercise_list.css` | **New.** The list card rules that used to live in the misnamed `reader_modern.css`, on canonical tokens. |
| `exercises/static/exercises/css/exercise.css` | Rewritten for the runner on canonical tokens; the duplicated `.card` rule and the light-theme leftovers are gone. |
| `exercises/static/exercises/js/exercise_runner.js` | **New.** The runner state module (below). |
| `lessons/static/lessons/css/reader_modern.css` | **Deleted.** Its last consumer was the exercise list. |
| `lessons/templates/lessons/steps/_practice.html` | Type/difficulty labels now come from the model properties instead of an if-chain in the template. |
| `static/css/base.css` | Added the shared `.sr-only` utility; **removed the legacy token aliases** (see below). |
| `exercises/tests.py` | +27 tests: the list, the runner page, and `build_runner` itself, all on a fixture that builds one exercise per real type (a test DB has none of them). |

**The question kind is derived, never assumed (the important part).** `runner.py` decides
from the real `Answer` rows, not from `Exercise.type`:

| Kind | Rule | Which live questions |
|---|---|---|
| `choice` | more than one answer row → pick a rendered option | all 92 `MULTIPLE_CHOICE`, all 46 `TRUE_FALSE`, all 69 `READING`, and the 38 `FILL_BLANK` questions authored with distractors |
| `text` | exactly one answer row → type the answer | all 46 `TRANSLATION` and the 5 `FILL_BLANK` questions with no distractors |
| `none` | no answer row at all → shown, labelled as unchecked, **left out of the score** | none today (0 rows in the live DB), but the runner must not invent a verdict |

Live spread worth remembering: `MULTIPLE_CHOICE` = 23 exercises / 92 questions / 4 options each;
`TRUE_FALSE` = 23 / 46 / 2; `READING` = 23 / 69 / 2 (each question carries a `CONTEXT`
sentence — that is the passage); `FILL_BLANK` = 19 / 43 (1, 2 or 3 answers); `TRANSLATION` =
23 / 46 (one expected answer). 89 of 296 questions have an explanation; **no** question has
audio or an image, so those blocks render only when the data appears.

**`Question.order` is lesson-wide, not per-exercise.** A lesson's `TRUE_FALSE` exercise
really does start at question 12, so the runner numbers questions by their **position** and
never prints `Question.order` as "question N of M". The old page showed the raw order.

**Runner state model** (`exercises/static/exercises/js/exercise_runner.js`, one IIFE, no
dependencies):

    index                        current question (0-based)
    state[i] = { submitted, outcome }   outcome: 'correct' | 'wrong' | null
    scoreable                    questions with data-kind != "none"

- The **answers live in the DOM the server rendered**: the correct option carries
  `data-correct`, and a typed answer's expected value sits in a **hidden**
  `.runner-expected__value` span that is revealed only after a miss. Grading reads those, so
there is no second schema to keep in sync.
- Typed answers are compared **normalized**: whitespace collapsed, trailing punctuation
  stripped, case-insensitive (so `GUTE  nacht!` matches `gute Nacht`). Every `Answer` in the
  database uses the `EXACT` match type; `ANY_OF` / `CONTAINS` exist in the model but are not
  exercised by any row, so they are **not implemented**.
- Flow: submit (never before an answer exists — an unanswered submit shows an inline
  message), then the result, then `بعدی` is *revealed*. It is withheld until the question is
  submitted, so a run always covers every question. The last question's action is
  `دیدن نتیجه`.
- Options are disabled and inputs are `readOnly` after submitting; going back to a
  submitted question shows its state unchanged, and its answer block stays revealed.
- Retry resets everything (state, options, inputs, feedback, flags) and returns to question 1.
- **Nothing is persisted.** A reload restarts the exercise; no result is claimed to be
  remembered. No `localStorage` key was added — progress storage is still `GamProgress`,
  for lessons only.
- Results use real counts only: `correct / scoreable`, accuracy %, and the list of missed
  questions (each a button that jumps back to it). Primary action = back to the lesson,
  plus the next exercise in that lesson when there is one. No mastery/level claim anywhere.

**One progress indicator, not two.** The bar is a real `role="progressbar"`
(`aria-label="پیشرفت تمرین"`, min 1, max = question count) and is the only progress
control; the visible "سؤال N از M" sits once, in the current question's eyebrow. The bar is
hidden for a one-question exercise and stays hidden when JavaScript is off (with one
question on screen there is nothing to progress through).

**Progressive enhancement, same rule as the lesson page.** Only `.js .runner-q:not(.is-active)`
hides the other questions, and the controls ship `hidden` — so with JavaScript off all
questions are readable, there is no dead `بررسی پاسخ` button, and a `<noscript>` note says
checking needs JavaScript. A no-JS run cannot be graded at all (grading is client-side).

**CSS cleanup (the §5.14 job).** `reader_modern.css` is deleted; the exercise list has its
own stylesheet in the `exercises` app on canonical tokens; the six undefined classes
(`exercise-list-card`, `exercise-list-grid`, `exercise-list-header`, `exercise-list-title`,
`exercise-list-subtitle`, `nav-back-link`) and the borrowed `reader-exercise-*` /
`difficulty-*` names are gone, replaced by an `ex-*` naming that belongs to the app.
`exercise.css` was also rewritten (it was light-theme only and duplicated `.card`).

### Phase 7 — vocabulary, grammar, dialogue & listening polish

The goal was that vocabulary, grammar, dialogue and listening stop looking like separate old
pages. Nothing below needed a model, a migration or a new dependency.

| File | Change |
|---|---|
| `templates/includes/audio_control.html` | **New (moved** out of `lessons/templates/lessons/_audio_control.html`**).** The one audio control for every playable item: lesson prose blocks, grammar topics, sentences, vocabulary words (list + detail + lesson cards) and exercise question audio. Prefix scheme `{{ prefix }}-{{ pk }}` (`block-`, `grammar-`, `sentence-`, `word-`, `q-`) is asserted by tests. |
| `static/js/audio.js` | **New (moved** from `lessons/static/lessons/js/lesson_audio.js`**).** Reveals the `hidden` button, toggles play/pause, stops every other player, reports loading/error via a `role="status"` span, keeps `aria-expanded` in sync. Loaded globally by `base.html`. |
| `lessons/templates/lessons/_audio_control.html`, `lessons/static/lessons/js/lesson_audio.js`, `vocabulary/static/vocabulary/js/word_audio.js` | **Deleted.** The vocabulary app had its own second implementation; it is gone, along with the whole `vocabulary/static/vocabulary/js/` directory. |
| `static/css/components.css` | Gained the audio-control styles (its old home was `lessons.css`) and the shared **`.chip`** badge primitive, which the journey `.tag` base now extends. |
| `lessons/static/lessons/css/lessons.css` | Audio rules removed (they moved to `components.css`) — it is now only the path furniture. |
| `lessons/static/lessons/css/lesson_journey.css` | Dialogue laid out as a **script** (speaker beside the German line via grid areas, stacked on phones — never a chat transcript), paragraph rhythm for grammar/prose, chip base unified with `.chip`. |
| `lessons/templates/lessons/steps/_block.html`, `_grammar.html`, `_sentence.html`, `_word_card.html` | Include path → `includes/audio_control.html`. Grammar renders the stored explanation with `linebreaks` as **real paragraphs** (`<p>`s) instead of one wall of `<br>`; the text itself is untouched. Sentences publish their real `data-role` (and a speaker only where the data has one). |
| `lessons/templates/lessons/lesson_detail.html` | The stepper module still owns stepping; audio is global now. |
| `templates/base.html` | Loads `static/js/audio.js` for every page. |
| `exercises/templates/exercises/exercise_detail.html`, `_exercise_card.html`, `exercises/static/exercises/css/exercise.css`, `exercise_list.css` | Migrated to the shared `.chip` primitive and the shared audio include (question audio was previously unreachable). |
| `vocabulary/models.py` | `Word.type_label` / `gender_label` properties (Persian copy; **properties, not fields** — no migration). |
| `vocabulary/views.py` | Published-only list; level tabs annotated with real published counts (with an **explicit `order_by`** — the aggregate silently dropped the model ordering, see §5); word detail now supplies the real lessons that teach the word and the real exercises that test it. |
| `vocabulary/templates/vocabulary/word_list.html`, `word_level_list.html`, `_pagination.html` | Rewritten as a dense scannable **row** list (not a decorative grid): German term as an LTR link, per-row audio, Persian meaning, type/level chips, one page-state line, labelled pagination. |
| `vocabulary/templates/vocabulary/word_detail.html` + `vocabulary/static/vocabulary/css/{word_list,word_detail}.css` | Rewritten as a focused study screen (word → audio → meaning → grammar facts → where it is taught → what tests it) on canonical tokens. |
| `lessons/static/lessons/js/lesson_reader.js` | Tokenises only elements that opt in with `data-lookup` (prose blocks, grammar bodies, German sentences — **never** a word card, whose term is already a link), marks tokens `lang="de"`, and keeps the popover clear of the fixed bottom nav by reading `--bottom-nav-h`. |
| `vocabulary/tests.py` | 5 → **26 tests.** |

### Phase 8 — backend progress integration

The user's brief for this phase: wire the existing progress models up, keep the code plain
and readable, do not redesign the lesson page, do not install anything. Two decisions were
put to the user before any code was written, and both were answered:

1. **Typed answers need somewhere to live.** `ExerciseAttempt.answer` is a FK to `Answer`,
   and a typed question has exactly one `Answer` row (the correct one) — so a *wrong* typed
   answer had no row to point at. Decision: **make `answer` nullable and add
   `response_text`**, so nothing a learner types is thrown away.
2. **How often to save the resume point.** Decision: **one small POST per step** (guarded so
   the same step is not sent twice in a row), because a step change is real learner activity
   and it makes `current_step` truthful without depending on `pagehide`.

| File | Change |
|---|---|
| `exercises/models.py` | `ExerciseAttempt`: `answer` → `blank=True, null=True`, **new** `response_text` (CharField 500), a class docstring explaining the two ways an answer is stored, and `__str__`. New migration `exercises/0003_exerciseattempt_response_text_and_more`. |
| `lessons/models.py`, `vocabulary/models.py` | `LessonProgress.__str__` only (methods need no migration). `WordProgress` untouched — it already matched the brief. |
| `lessons/progress.py` | **New.** The lesson-progress rules, stated once: `record_step` (creates the row on the first visit, never rewrites `started_at`), `complete_lesson` (keeps the *first* `completed_at`), `progress_dict` (the five facts the frontend relies on), `progress_state` (the `{source, lessons, lastLessonId}` payload the page scripts already read). |
| `lessons/views.py` | `LessonProgressView` (**new**, `LoginRequiredMixin` + `raise_exception`, POST JSON, 405 on GET, 400 on an unknown step). `LessonDetailView` now computes `resume_step` (the index of the stored step in the journey, `None` when it no longer exists) and always adds `progress_state`. `_path_context` gained the `user` parameter; `DashboardView`, `CourseDetailView`, `LessonListView` pass the same payload. |
| `lessons/urls.py` | `lessons/<pk>/progress/` → `lesson-progress`. |
| `exercises/grading.py` | **New.** `normalize()` (collapse whitespace, drop trailing punctuation, lowercase — the same rule the browser used, so previously-accepted answers still pass) and `grade()`, which returns the verdict plus the rows the attempt is stored with, or `None` when a submission genuinely cannot be judged (no authored answer, or an option of another question). |
| `vocabulary/progress.py` | **New.** `tested_word()` (only the `TESTED_ITEM` target counts — `CONTEXT` words are ignored) and `record_word_progress()` (one attempt, plus the correct/wrong counter and its timestamp). |
| `exercises/views.py` | `ExerciseSubmitView` (**new**, no login required: everyone is graded, only a signed-in learner is recorded). `_response_time()` drops unusable values (not a number, negative, or > 1 h) instead of rejecting the submission. `ExerciseDetailView`'s docstring now says the answers are deliberately absent. |
| `exercises/runner.py` | `build_runner` no longer emits `expected` or `explanation` — the page carries no answers. It is now only the *shape* of the page (kind/options/passage). |
| `exercises/urls.py` | `exercises/<pk>/submit/` → `exercise-submit`. |
| `lessons/admin.py`, `exercises/admin.py`, `vocabulary/admin.py` | Read-mostly `ModelAdmin`s for the three progress models, so the new data can be inspected. |
| `templates/base.html` | `meta[name="csrf-token"]` — both POSTing scripts read it. |
| `static/js/progress.js` | Reads an optional `#progress-state` JSON and, when present, becomes **server-backed**: `read()` returns it and the write helpers stop touching `localStorage` (`serverBacked` is exposed for the page scripts). Anonymous behaviour is byte-for-byte the same. |
| `lessons/static/lessons/js/lesson_steps.js` | Reads `data-progress-url` / `data-resume-step`, POSTs each step (guarded), and asks the server *before* claiming a lesson is complete. Resume order is `#step-…` → server → `localStorage` → 1. |
| `exercises/static/exercises/js/exercise_runner.js` | Submits to `data-submit-url` instead of grading: the verdict, the right option, the expected answers and the explanation all come from the response. Measures each question with `performance.now()` (clock starts when the question comes on screen) and sends it as `response_time`. Failed requests keep the question open with a retry hint. |
| `exercises/templates/exercises/exercise_detail.html` | `data-submit-url`; `data-correct` and the server-rendered expected answer/explanation are **gone** (the response fills them); the disclosure says where an answer goes, conditioned on being signed in. |
| `lessons/templates/lessons/lesson_detail.html` | `data-progress-url` + `data-resume-step` (signed-in only) and the `progress-state` script. |
| `templates/dashboard.html`, `lessons/templates/lessons/lesson_list.html` | The `progress-state` script plus honest copy that depends on `user.is_authenticated` ("this browser" vs "your account"). `course_detail.html` inherits from `lesson_list.html`, so it is covered. |
| `lessons/templates/lessons/steps/_finish.html`, `_practice.html` | Where progress/answers are kept is now conditional instead of always claiming "this browser". |
| `lessons/tests.py` | +26 tests (`LessonProgressTests`, `LessonProgressEndpointTests`). |
| `exercises/tests.py` | +26 tests (`ExerciseSubmissionTests`, `WordProgressTests`, `GradingTests`) and three rewritten runner tests (§5.2). |

### Why the token aliases were needed (and are now gone)
`base.css` is the single source of truth. Older stylesheets (`reader_modern.css`, the old
`exercise.css`, and parts of `lessons.css`) referenced variable names that **were never
defined**, which silently broke borders/backgrounds/colors:

| Legacy name | Canonical token |
|---|---|
| `--border` | `--line` |
| `--foreground` | `--fg` |
| `--muted-foreground` | `--muted` |
| `--card` | `--surface` |
| `--accent-foreground` | `--on-accent` |

Phase 0 aliased those five names onto the canonical tokens. **Phase 6 removed the alias
block** (and the two old stylesheets) once a project-wide search found zero consumers left
— verified with a grep for each name before deleting. **Do not reintroduce them:** a rule
that references an undefined token silently renders transparent or inherit, which is how the
original bugs hid.

Canonical tokens: `--bg --surface --surface-alt --fg --muted --line --accent
--accent-soft --on-accent --success --warning --danger --info --shadow`.

### Phase 9 — frontend audit, polish & error pages

| File | Change |
| --- | --- |
| `tests/tests.py` | The app was an empty stub; it now holds project-wide template guards: no template may contain a multi-line `{# #}` comment (the Phase 0 bug class — it had regressed to 4 leaks), and **both error pages must render**, the 500 with an empty context exactly as Django renders it. |
| `templates/404.html` (new) | Extends `base.html`, so the sidebar/bottom nav render normally (`page_not_found` passes the request, so the context processors run). Says the likeliest real reason — an unpublished lesson or a moved page — and offers three ways back. |
| `templates/500.html` (new) | **Standalone on purpose.** Django renders the 500 template with *no* context, so `base.html`'s `brand`/`nav_items`/`home_url` would be empty. Loads `base.css` + `components.css` only, and is the one place outside `settings.BRAND` where the product name is written by hand. |
| `static/img/favicon.svg` (new) | The brand monogram, same curves as `templates/includes/brand.html`. Without it every page asked for `/favicon.ico` and logged the only console error in the product (§5.10). |
| `templates/base.html` | `<link rel="icon">` + `<meta name="theme-color">`; the three multi-line `{# #}` comments became `{% comment %}` (one was added in Phase 8). |
| `static/css/components.css` | `.btn:disabled` / `.btn[aria-disabled="true"]` (there was **no** disabled styling at all), `.error-page*`, and `min-width: 44px` on the icon-only audio button. |
| `static/css/shell.css`, `static/css/dashboard.css` | Spacing/rhythm fixes found in the audit. |
| `lessons/static/lessons/css/lesson_journey.css` | The stepper's chrome and chips; `lesson_steps.js` now uses `disabled` + `بعدی: <next step>` on the next button. |
| `vocabulary/static/vocabulary/css/word_list.css` | `.vrow__term` gets a real 44×44 target on touch-sized screens (≤1023px) where the row has the whitespace — including `min-width: 44px`, because two-letter words like "zu" collapsed to 23px wide and missed WCAG 2.2 AA. |
| `lessons/templates/lessons/steps/_block.html`, `_grammar.html` | Removed the `.step-block__audio` / `.grammar-topic__audio` wrappers: Phase 7 moved those rules into `components.css` and left the names behind, so they were divs with no rules around an already self-spacing control. |
| Also edited | `lessons/templates/lessons/{lesson_list,lesson_detail}.html`, `lessons/static/lessons/css/lesson_path.css`, `exercises/templates/exercises/exercise_list.html`, `exercises/static/exercises/css/exercise_list.css` |

### Phase 10 — follow-up: `LoginView` honours `?next=`

A **behaviour change**, made after the style pass, on the user's request. It exists because of
§5.31: three `accounts` tests were asserting redirects the views never performed, and for one of
them the honest answer turned out to be *"the test is right and the view is incomplete"*.

| File | Change |
| --- | --- |
| `accounts/views.py` | New module-level `_next_url(request)` reads the destination from `request.POST["next"]` first, then `request.GET["next"]`, else `""` — the same precedence Django's own `LoginView` uses. `get` passes it into the template, and `post` redirects to it after `login()`. Nothing else changed: the default is still `accounts:profile`. |
| `accounts/tests.py` | The stale `test_login_honours_the_next_parameter` came back in the other direction, and three more were added: the **login page must render the hidden `next` field** (that is the seam — the form posts to `/accounts/login/` with no query string on it, so the query string alone would lose the destination), the **form-carried** value is honoured, and an **off-site** value is refused. `accounts` is now 21 tests. |

**Two things that make this safe, and both matter:**

1. **The template was already ready.** `accounts/templates/accounts/login.html` has rendered
   `{% if next %}<input type="hidden" name="next" value="{{ next }}">{% endif %}` since Phase 2 —
   only the view never supplied `next`, so the field never appeared. No template change was
   needed, and none was made.
2. **The destination is not trusted.** `url_has_allowed_host_and_scheme(next_url,
   allowed_hosts={request.get_host()}, require_https=request.is_secure())` gates the redirect.
   Without it, `/accounts/login/?next=https://evil.example` would make the login page an **open
   redirect** that hands a freshly signed-in visitor to another site. **Never drop that check,
   and never simplify the redirect to a bare `redirect(request.GET.get("next"))`.**

Nothing in the product links with `?next=` today (no view uses `login_required` without
`raise_exception`), so this is plumbing that is correct and ready rather than one in use. It is
what `LOGIN_URL = 'accounts:login'` in `config/settings.py` implies, and it is covered by tests
so it cannot rot unnoticed.

### Phase 10 — backend coding style

No file was added or removed. Every change is a rewrite of existing Python in the `accounts`
style; behavior is unchanged. Paths carry a `*` when only the style changed.

| File | Change |
| --- | --- |
| `exercises/grading.py` * | `normalize()` no longer chains three calls in one line. `grade()` lost `next((… ), None)` and `any(… for …)`: the chosen option is a plain `for`/`break` loop, and the typed-answer comparison sets `is_correct` in a loop. |
| `exercises/runner.py` * | `scoreable_count()` counts in a loop instead of `sum(1 for …)`. |
| `exercises/views.py` * | The `from lessons.models import Lesson` that sat *inside* `ExerciseListView.get` moved to the top. The next-published-exercise `next((… ), None)` is now a `for`/`break`. `question_total` and `lesson_count` are computed in one loop instead of a generator sum and a set comprehension. |
| `lessons/views.py` * | The resume-step lookup (`step_keys = […]; … .index(…)`) is now `enumerate` + `break`, so it never builds a throwaway list. `hours_total` sums in a loop. |
| `lessons/progress.py` * | `_iso()` is an explicit `if value is None: return None`. |
| `lessons/journey.py` * | Dropped `from __future__ import annotations`; `content_step_count()` counts in a loop. |
| `vocabulary/views.py` * | Removed the three imports that were duplicated inside `WordLookupView.get` (`Q` was already imported at the top). The results list is built in a `for` loop with `word` as the name, not a comprehension over `w`. `word_total` sums in a loop. |
| `vocabulary/progress.py` * | `tested_word()` returns through an explicit `if target is None`. |
| `exercises/models.py`, `vocabulary/models.py` * | `type_label` / `difficulty_label` / `gender_label` use `if key in LABELS` + direct access, **not** `LABELS.get(key, fallback)`. `QuestionTarget.__str__` picks its target with `if`/`elif`/`else` instead of `a or b or c`, and `Word.__str__` builds the article in an `if`. |
| `lessons/models.py` * | Removed a **duplicated** `from django.db import models` / `from django.conf import settings` pair that sat in the middle of the file, added the missing blank lines between top-level classes, and dropped a stray `#db/django` inline comment. No field changed, so no migration. |
| `config/context_processors.py` * | `home_url` is resolved with two `if` checks instead of an `or`-chain. (This file already used the explicit `if "app_names" in item` shape the user asked for, and keeps its small `resolve()` / `is_active()` helpers.) |
| `lessons/management/commands/seed_a1_course.py` * | Dropped `from __future__ import annotations` and every annotation. `counters["a" if created else "b"] += 1` became a real `if`/`else`. The sentence tuple is unpacked by index with length checks, not `(list(row) + ["", …])[:4]`. The summary output's two nested f-string ternaries became named `lessons_updated` / `contents_updated` fragments. |
| `lessons/management/commands/export_a1_content.py` * | Dropped `from __future__ import annotations` and every annotation. The large CSV row comprehensions were **kept on purpose** — see the note below. |
| `lessons/management/commands/validate_a1_content.py` * | Dropped `from __future__ import annotations` and every annotation. The "every level word is linked" check is now an `if`/`else` building one list. |
| `vocabulary/management/commands/import_a1_words.py` * | Dropped `from __future__ import annotations` and every annotation. The `pending` dict comprehension is a loop. `_render_all` was renamed to `render_audio_all` (it was private with a single caller) and its `for … else` retry trick is now an explicit `rendered` flag. `asyncio.gather(*(…))` takes a built task list. `created = updated = skipped = 0` became three lines. |
| `generate_lesson_content_audio.py`, `generate_grammar_audio.py`, `generate_sentence_audio.py` * | The parallel-worker block was the least readable code in the project: a one-line dict comprehension **and** a conditional generator of `(row, job)` tuples. It is now a plain `if options["workers"] > 1:` with a real `for` over `as_completed`, and a plain `else` branch for the single-worker case. `generated += publish(…, path)` became `if publish(…): generated += 1`. The inline `subprocess.run([...])` argument list became a named `command` list. `generate_sentence_audio.py` also had tangled imports (two `BaseCommand` imports, `subprocess` stranded away from the other stdlib imports, and an invisible `de-DE-KatjaNeural` literal) — sorted and given the `VOICE` constant its two siblings already had. |
| `lessons/tests.py` * | Dropped `from __future__ import annotations` and `-> tuple[int, ...]`. |

**One thing kept on purpose.** `seed_a1_course.py` still sorts with
`lessons.sort(key=lambda item: item["order"])`. A sort key is the one case where a lambda is the
plain answer; the alternatives (`operator.itemgetter`) need an extra import and are no easier to
read. The `export_a1_content.py` CSV-row comprehensions were also left in place: each one builds
one flat row per lesson from a fixed set of columns, and expanding six of them into nested loops
would have tripled the file for no gain in clarity.

---

## 5. Known issues (pre-existing, not yet fixed)

> **`python manage.py test lessons` currently cannot run at all.** `setUpTestData` calls
> `seed_a1_course`, whose validator exits the process on data errors, so the runner aborts
> with **no summary** (exit code 1, 26 tests never execute). Run it with a pipeline and you
> will not notice — the shell reports the pipeline's exit code. Root cause (verified,
> read-only, via `manage.py seed_a1_course --check`): the lesson data modules reference
> vocabulary that does not exist in the DB/JSON:
> - `entschuldigung` (lowercase) in `a1_lessons_a.py:130`, `a1_lessons_b.py:678,1679` —
>   the data has `Entschuldigung` (OTHER) and `entschuldigen` (VERB). Case mismatch.
> - `gern haben` in `a1_lessons_a.py:1140` — the data has `gernhaben` (VERB).
>
> This is a **data** bug, not a code bug. It is **out of Phase 0 scope** and is left
> untouched on purpose (`AGENTS.md`: do not fix out-of-scope bugs unreported/unasked).
> Fixing it means deciding the canonical vocabulary entries, then updating both the
> lesson data modules and the JSON — get a human decision first.
>
> **It truncates the whole suite, not just `lessons`.** `python manage.py test` prints
> “Found 124 test(s)” (Phase 6) but the run dies as soon as the seeding class is reached,
> so *no* test command currently reports full coverage — the dots stop and there is no
> summary. `lessons.tests.DashboardTests`, `LearningPathTests`, `LessonJourneyTests`, plus
> the whole `exercises`, `accounts` and `vocabulary` suites, avoid the seeding class and
> are runnable on their own.

1. **Exercises are DB-only** — no seed command; cannot be reproduced on a fresh DB/CI.
2. **RESOLVED in Phase 8.** Exercise grading moved to the server and the answer left the
   page: there is no `data-correct` attribute and no expected-answer text in the HTML any
   more. `exercises/grading.py` decides the verdict, `ExerciseSubmitView` records it, and the
   runner draws the feedback from the response. `build_runner` is now only the *shape* of the
   page (kind/options/passage) — **do not put the correct answer back into it**, and keep the
   three rewritten runner tests intact (§8) since they are what stops that regression.
   Still client-side: the score tally on the results screen, which is summed from the verdicts
   the server already returned.
3. **RESOLVED in Phase 5.** `exercises/tests.py` →
   `LessonExerciseDisplayTest.test_lesson_detail_page_offers_its_exercises` now asserts the
   journey markup (`data-journey-step="practice"` plus a real link per exercise), and
   asserts that a lesson with **no** exercises does not grow an empty practice step.
4. **RESOLVED in Phase 5.** The orphaned `lessons/templates/lessons/_lesson_sidebar.html`
   was deleted along with the retired reader stylesheets.
5. **RESOLVED in Phase 5, finished in Phase 7.** The stray `+.btn-prev-section:disabled`
   selector went with the old reader-era rules; `lessons.css` is now only the path furniture
   (its audio-control rules moved to `static/css/components.css` in Phase 7).
6. **`guide.py`** is stale duplicate model code (gitignored, not imported). Do not rely on it.
7. `AGENTS.md` describes DRF/Django 4.2 — inaccurate (see §1).
8. `tests` app is a stub but is still listed in `INSTALLED_APPS` and in the navbar as
   "آزمون (not ready)".
9. **RESOLVED in Phase 5.** The ~24 unstyled reader classes went with the reader itself;
   the journey templates own their own stylesheet (`lesson_journey.css`). Six classes on the
   journey are deliberately left without rules because they are wrappers or label spans that
   inherit everything they need: `agenda__item`, `agenda__label`, `ex-item__cta` (a `.btn`,
   sitting on a `.btn--primary`), `journey-chip__label` (read by `lesson_steps.js`),
   `nav-link__label`. Phase 9 removed the other two, `step-block__audio` and
   `grammar-topic__audio` — see §4. A class in a template with no rule anywhere is a smell,
   not a bug: check whether a *stale name* is hiding before adding a rule for it.
10. **RESOLVED in Phase 9.** `/favicon.ico` used to 404 on every page — the only console
    error and the only 4xx the product ever produced. `static/img/favicon.svg` plus a
    `<link rel="icon">` in `base.html` and `500.html` fixed it; confirmed in Chromium at all
    four widths (the browser now requests `/static/img/favicon.svg` → 200 and never probes
    `/favicon.ico`). Note: Django's **debug** 404 page still probes `/favicon.ico`, so the
    console noise reappears while `DEBUG = True` on a 404 route only — that is Django's
    page, not ours.
11. **Django's password-validator messages are still in English.** Our own form labels and the common errors are Persian, but messages raised by `AUTH_PASSWORD_VALIDATORS` ("This password is too short.", "This password is too common.") are translated from `LANGUAGE_CODE`, which is `en-us`. Setting `LANGUAGE_CODE = 'fa'` would localise those (and Django's admin) automatically; it was left alone because it is a global change outside the auth scope. **Decision needed.**
12. **RESOLVED in Phase 6.** The light-mode-only colours in `reader_modern.css` /
    `exercise.css` are gone with those files: the reader stylesheet was deleted and the
    exercise stylesheets were rewritten on canonical tokens. The legacy token aliases had
    no consumers left, so the alias block was removed from `base.css` too (see §4).
13. **The learning path renders every published lesson of every published course, with no
    pagination and no collapsing.** That is the point at 24 lessons (a path that breaks
    across pages stops being a path), but if a level ever grows into the hundreds, revisit:
    render on demand, or collapse long runs of completed steps behind a summary step.
14. **RESOLVED in Phase 6.** `reader_modern.css` is deleted, the exercise list has its own
    `exercises/css/exercise_list.css`, and the six undefined classes are gone. The list page
    now loads `base.css` + `components.css` (both global) + its own stylesheet only — it no
    longer borrows `lessons.css`.
15. **The exercise detail view is reachable for an unpublished exercise, and for an exercise
    of an unpublished lesson.** The list filters both out (Phase 6) and the lesson page is
    unreachable when unpublished, but `ExerciseDetailView` still has no `is_published`
    guard, as before. Nothing in the live data is affected (111/111 exercises published).
    Left alone deliberately: it is a pre-existing gap outside the Phase 6 scope.
16. **PARTLY RESOLVED in Phase 8.** Every submission is now a stored `ExerciseAttempt`, so
    the history survives. What is still session-only is the *run*: reloading starts the
    exercise over and that run's "questions to revisit" list is gone. Nothing reads the stored
    attempts back yet — no "carry on with this exercise" and no per-exercise score on the
    library page. That needs a new query/endpoint, not a model change.
17. **RESOLVED in Phase 8.** `_finish.html`, `_practice.html`, the dashboard and the path now
    say where progress is kept, conditioned on `user.is_authenticated`, instead of always
    claiming "this browser". The blocked-storage message is still shown (and the button still
    withheld) when there is nowhere to write — but `lesson_steps.js` now checks
    `serverBacked` first, because a signed-in learner with localStorage blocked is unaffected.
    `dashboard.js` and `path.js` got the same guard so they cannot print "this browser blocks
    storage" over server-backed progress — and the browser pass then caught the other half:
    `path.js` was also *overwriting* that line with «پیشرفت روی همین مرورگر ...» for a
    signed-in learner. Both scripts now branch on `progress.serverBacked` (§8).
18. **Lookup opens on `focusin`, so tabbing fetches one word per focus.** Responses are
    checked against a generation counter and cached (200 entries), so it is bounded, but a
    debounce would be kinder on a slow connection.
19. **`WordDetailView` has no published guard** — same shape as §5.15. The list and the
    lookup filter `is_published=True`, the detail view does not; all 1,008 live words are
    published, so nothing is reachable today. Pre-existing, left alone deliberately.
20. **The vocabulary app has no search or filter, and none was invented.** Server-side there
    is only the level tab and `?page=`. Real search means a `?q=` filter on `WordListView`
    (a backend change), not a form that filters what is already on screen.
21. **`/media/` is gitignored**, so a fresh clone has no audio at all (all ~1,541 files are
    generated). Every player then points at a 404 and the shared control's `role="status"`
    span reports it; the `<noscript>` download link is the only no-JS path. Exercise question
    audio is wired up but **no live question has audio**, so that branch is unexercised by
    real data.
22. **RESOLVED in Phase 7.** The vocabulary page's old player left a visible button that did
    nothing when JavaScript was off. The shared component ships `hidden` and is revealed by
    `static/js/audio.js`, so with JS off there is no dead control — just the download link.
23. **Phase 7 moved two files instead of copying them** (`_audio_control.html` and
    `lesson_audio.js` → `templates/includes/` and `static/js/`). If you are looking for the
    old paths in git history, they are deletions, not renames with content changes.
24. **`ExerciseSubmitView` has no `is_published` guard**, same shape as §5.15: it loads any
    `Exercise` by pk. Grading is harmless and recording needs a login, and all 111 live
    exercises are published, so nothing is reachable today — but it inherits the gap rather
    than fixing it. Guard both views together if it is ever fixed.
25. **`WordProgress` counters are read-modify-write.** `record_word_progress` loads the row,
    increments and saves, so two submissions for the same word arriving at the same instant
    could lose one increment. Deliberate: the brief asked for plain code over an
    `F()`-expression/`update()` construction, and one learner cannot really submit twice at
    once. Switch to `F()` + `update()` only if this ever becomes real traffic.
26. **Nothing merges an anonymous visitor's `localStorage` history into their account.**
    Signing in switches to the server record and leaves the device's old entries alone (they
    are still on the device, just unread). A merge is a design decision nobody has made yet.
27. **The runner records one attempt per submission, including after "تلاش دوباره".**
    Retrying and answering the same question again adds another `ExerciseAttempt`. That is the
    point (history, not a tally) — but any future "how many questions did this learner get
    right?" number has to decide which attempt counts, most likely the latest one
    (`ExerciseAttempt.Meta.ordering` is `-created_at`).
28. **Two advisory tap-target sizes are accepted on purpose (Phase 9 audit).** The lesson
    title link at the top of an exercise group (`.ex-group__title a`) measures **358×37**: the
    whole group heading is the target via a stretched `::after`, it is 358px wide, and it
    clears WCAG 2.2 AA (24×24) comfortably. The `.vrow__term` in the vocabulary list is 29px
    tall on **pointer** screens (≥1024px) and 37→44px wide/tall on touch screens (≤1023px) —
    that row is deliberately dense where a mouse is used, and the row's only other control is
    the audio button. Both are the 44px *comfort* guideline, not a failure. If you widen one,
    check the row/card rhythm first: the dense rows are 24 words on a page.
29. **The favicon is duplicated by hand.** `static/img/favicon.svg` cannot read the CSS
    custom properties, so `#0f1116` and `#7caeff` are written into it. Change them if `--bg`
    or `--accent` ever move. Same for `templates/500.html`'s `theme-color`, which also hardcodes
    `#0f1116` (as does `base.html`).
30. **`vocabulary/german_text.py` does not exist, so two management commands cannot run.**
    `lessons/management/commands/generate_lesson_content_audio.py` and
    `vocabulary/management/commands/generate_grammar_audio.py` both do
    `from vocabulary.german_text import spoken_text` at module level, and there is no such
    module (verified: no file, and `german_text` appears nowhere else in the repo). Running
    either command — or even importing it — raises `ModuleNotFoundError`. Found during the
    Phase 10 style pass; **left alone** because it is a pre-existing bug outside that pass and
    fixing it means deciding where `spoken_text` should live. The other three audio/import
    commands (`generate_sentence_audio`, `import_a1_words`, `seed_a1_course`) import fine.
31. **RESOLVED in Phase 10.** Three `accounts` tests were stale against the app's own views
    and asserted redirects that never happen. Found during the style pass (which did **not**
    touch `accounts`), confirmed pre-existing with `git stash` (the committed `accounts/tests.py`
    is an empty stub, so these tests came from the same uncommitted working tree), and fixed on
    the user's decision — **the views are right, the tests changed**:
    - `test_post_logout_signs_the_user_out` expected `/`; `LogoutView` redirects to
      `accounts:login`, which is where the «با موفقیت خارج شدید.» message is shown.
    - `test_profile_requires_login` expected `?next=…`; `ProfileView.get` redirects to
      `accounts:login` with no `next`, because there is no protected page to return to — the
      learning content is public.
    - `test_login_honours_the_next_parameter` asserted a capability `LoginView` does not have
      (it ignores `?next=` and always lands on the profile). Renamed to
      `test_login_lands_on_the_profile_even_with_a_next_parameter`, so the test name no longer
      promises something the view does not do.
    The whole `accounts` suite is now **21 tests, green**, and the `?next=` half was then
    **implemented rather than deleted** — see the entry below.

---

## 6. Temporary solutions & replacement points

| Temporary | Where | Replace with |
|---|---|---|
| `localStorage` progress, **anonymous visitors only** | `static/js/progress.js` (`window.GamProgress`) still owns the storage (key `gam.progress.v1`: `lessons` statuses + `positions` step index); read by `dashboard.js`, `path.js` and `lesson_steps.js` | Nothing, unless anonymous progress should live on the server too — that needs an identity for a visitor (a nullable `user` or a session key) and nobody has asked for one. **Keep every read/write behind `GamProgress`**: only that file knows which mode is active. |
| Where the two modes meet | `progress.js` reads an optional `#progress-state` (`json_script`, rendered by the dashboard, the path and the lesson page for a signed-in learner from `lessons/progress.py::progress_state`) and then treats the server as the record — writes stop going to `localStorage`, `serverBacked` becomes true, and the lesson page's stepper POSTs the steps itself | Nothing. **Extend `progress_state()` rather than adding a second payload** if a page ever needs more than status + `updatedAt` + `lastLessonId` (the step within a lesson is deliberately *not* in it — the lesson page gets `data-resume-step` instead, because that is an index into the journey and the payload speaks in lesson ids). |
| What is still client-side in the runner | the run: current question, `submitted`/`outcome` per question, the tally on the results screen, and the `performance.now()` response-time measurement | Nothing urgent. Reading `ExerciseAttempt` back for a per-exercise result or a "carry on" link is a new query/endpoint, not a model change (§5.16). |
| Word lookup is a client-side enhancement | `lessons/static/lessons/js/lesson_reader.js` tokenises any `[data-lookup]` element and fetches `vocabulary:word-lookup` on demand; the popover is one shared `#word-popover` in `lesson_detail.html` | A server-rendered word link/add-to-deck flow. Keep the `data-lookup` attribute as the seam — the script already works on any container that publishes `data-lookup-url`. |
| Hardcoded lesson-level state (no entitlement) | Lesson path UI | Free/Premium/Trial entitlement (explicitly out of scope now). |
| Inline-SVG brand mark | `templates/includes/brand.html` | Final brand assets once the name is locked. `static/img/favicon.svg` is the same monogram as a file, and the product name is written by hand in `templates/500.html` (Django renders it with no context) — rename in **both** places. |
| "Continue learning" | server-backed for a signed-in learner: the views hand the browser `progress_state` and `dashboard.js` classifies it through `GamStatus` exactly as it did with local data (anonymous visitors keep the local path) | Nothing — **the seam held**, which is what the Phase 0 note predicted. `lesson_status.js`, `dashboard.js` and `path.js` were not touched in Phase 8; keep it that way. |

---

## 7. Constraints & conventions

- **Write Python in the `accounts` style.** The user uses this project as a portfolio piece for
  an Ausbildung interview and has to explain every line himself, so the `accounts` app is the
  reference for the whole backend (see §4, Phase 10). Concretely:
  - **No type hints** (`str`, `dict`, `list`, `->`, `from __future__ import annotations`).
  - **No `getattr()` / `setattr()`** where an explicit line works.
  - **No `.get()` with a default for lookups you can write as an `if`**: use
    `if key in LABELS: return LABELS[key]` then `return fallback`, not `LABELS.get(key, fallback)`.
  - **No single-use private helpers** (`_resolve`, `_iso`, …) unless they genuinely remove
    repetition. Wrappers whose whole body is one call are removed.
  - **Plain `if` / `elif` / `else`** instead of `or`-chains, `a if b else c`, `next((…), None)`,
    `any(… for …)`, `sum(1 for …)`, `x = a = b = 0`, `for … else`, and comprehension-plus-index.
  - **No lambdas** except a real sort key (`lessons.sort(key=lambda item: item["order"])` is
    deliberate — see §4, Phase 10).
  - **Import at the top of the file.** A local import inside a function needs a real reason
    (a circular import); otherwise move it up.
  - **A few repeated lines are better than a clever abstraction** — the `if workers > 1: … else: …`
    branches in the audio commands are the pattern to copy.
  - Keep module docstrings: they explain *why* a module exists, which is exactly what an
    interview asks about.
- **No migrations / no new models** was the *redesign's* rule, not a standing one: Phase 8
  added `LessonProgress`, `ExerciseAttempt` and `WordProgress` on purpose, with the user's
  approval. Still out of scope until asked for: SRS/mastery fields, `CourseProgress`,
  `StudySession`, analytics or streaks.
- **`LessonProgress.current_step` stores journey step keys.** They must stay identical to
  `lessons/journey.py::_STEP_SPEC`'s keys and `LessonProgress.Step`'s values — the same ten
  names, in the same order. `lessons.tests.LessonProgressTests` fails the moment they drift.
  If a step key is ever renamed, the stored values need a data migration.
- **Progress is only ever written on POST.** No GET writes a progress row (there is a test):
  the stepper posts each step to `lessons:lesson-progress`, and a lesson page for an
  anonymous visitor renders no endpoint at all. Keep new writes on POST for the same reason
  — a prefetch or a crawler must not create progress.
- **Exercise grading belongs on the server.** `exercises/grading.py` decides, the client
  displays. Never reintroduce a client-side verdict or put the correct answer back into the
  rendered page: `build_runner` is the shape of the page, not its answers.
- Preserve RTL layout and `lang="de"` / `dir="ltr"` handling for German text.
- Tap targets ≥ 44px; `:focus-visible` outlines are part of the design system.
- Honor `prefers-reduced-motion`.
- Database: `makemigrations` is allowed, **`migrate` only with explicit user approval**;
  no destructive DB operations without approval (see `AGENTS.md`).
- **Logout must be a POST form.** `django.contrib.auth.views.LogoutView` sets
  `http_method_names = ["post", "options"]` on Django 5+, so a GET to
  `/accounts/logout/` returns 405 by design — never turn it back into a link.
- Learning content stays public. `@login_required` belongs on `/accounts/profile/`
  only; do not add it to lessons, vocabulary or exercises.
- **"Progress" means completed lessons, everywhere.** Both the dashboard and the learning
  path show `completed / total` and label it کامل‌شده. Do not switch one page to a different
  measure (e.g. started) — two bars measuring different things is worse than either.
- **`lessons/templates/lessons/lesson_list.html` is the learning path**, despite the name.
  The name is kept because the `lesson-list` URL name, the level tabs and `course_detail.html`
  all depend on it. `course_detail.html` extends it and overrides the `title` / `heading` /
  `description` blocks only — keep those block names if you touch it.
- The learning path must stay **unpaginated**; that is a deliberate design decision.
- Do not imply locked or premium lessons anywhere. `upcoming` is a position on the trail.
  See the visual rule under Phase 4 in §4 before changing step states.
- **The lesson page is a journey, not a document.** Step definitions live in
  `lessons/journey.py` and each step's markup in `lessons/templates/lessons/steps/`. Never
  render a step for content the lesson does not have, and never move step copy into a template.
- **Never use a multi-line `{# … #}` in a template** — Django emits it as visible text (and
  any `<tag>` inside it becomes real markup). Use `{% comment %} … {% endcomment %}`.
- The lesson page must stay readable with JavaScript off: all steps server-rendered, the
  stepper only hides. Do not move content behind a script.
- **The exercise runner follows the same rule.** Every question is server-rendered; only
  `.js .runner-q:not(.is-active)` hides, and the controls ship `hidden` so a no-JS page has
  no dead button.
- **Never decide how a question is answered from `Exercise.type`.** `exercises/runner.py`
  derives `choice` / `text` / `none` from the real `Answer` rows — `FILL_BLANK` exists in both
  shapes in the live data, and one question has no author answer at all.
- **One progress indicator per page.** The runner's bar is it; the visible position text
  lives once, in the current question's eyebrow. `Question.order` is lesson-wide — number
  questions by position.
- Exercise results are **not** persisted. Do not add an exercise key to `localStorage`
  without replacing the whole temporary-grading story (§6).
- Exercise type/difficulty copy lives in `Exercise.type_label` / `Exercise.difficulty_label`.
  Do not re-add an if-chain for them in a template.
- The exercise list groups by lesson and shows published exercises of published lessons in
  published courses — the same rule as the dashboard, the path and the journey.
- **One audio system, product-wide.** Never write a page-specific player: include
  `templates/includes/audio_control.html` with a unique `prefix` + `pk` and let
  `static/js/audio.js` (loaded by `base.html`) run it. Player styles live in
  `static/css/components.css`; do not move them back into an app stylesheet.
- **`.chip` is the badge primitive** (`static/css/components.css`); the journey's `.tag`
  extends it. Do not hand-roll another badge in an app stylesheet.
- **Vocabulary copy lives on the model** (`Word.type_label`, `Word.gender_label`), exactly
  like `Exercise.type_label`. Do not re-add if-chains for them in templates.
- **A vocabulary term is a link and its player is a sibling, never nested inside it**, and
  word cards opt **out** of lookup tokenisation on purpose (nesting a lookup button inside a
  link would nest interactive controls). Only `[data-lookup]` elements get tokens.
- The word list stays a **dense row list** — a learner must be able to scan many words. Do
  not turn it into a grid of cards, and do not invent filters the backend cannot serve.
- German is `lang="de" dir="ltr"` and Persian meaning/explanation stays in the page's RTL
  flow. Grammar prose is rendered as paragraphs; **never rewrite stored educational text**
  to make it look nicer.
- Ask before installing dependencies or committing/pushing.

## 8. Tests

### Phase 10 — how the style pass was verified

There is no type checker in this project (no mypy/ruff, and the code base is deliberately
untyped), so the check is: static check + the existing suites + a compile of every touched file.

```bash
# Django's own checks (.venv/bin/python — the system python has no psycopg!)
.venv/bin/python manage.py check                 # System check identified no issues
.venv/bin/python manage.py makemigrations --check --dry-run   # No changes detected

# Byte-compile every touched file
.venv/bin/python -m py_compile <the touched files>            # ALL COMPILE OK

# Every suite that can run (the five non-seeding `lessons` classes are named individually,
# because `manage.py test lessons` as a whole still aborts on the §5.0 data bug)
.venv/bin/python manage.py test accounts exercises vocabulary tests \
    lessons.tests.DashboardTests lessons.tests.LearningPathTests \
    lessons.tests.LessonJourneyTests lessons.tests.LessonProgressTests \
    lessons.tests.LessonProgressEndpointTests
#   Ran 177 — OK (skipped=1)
```

That is **177 tests, all green, 1 skipped.** The `lessons` five cover `lessons/progress.py`,
`lessons/journey.py` and `lessons/views.py`; the other 113 cover accounts (21), exercises,
vocabulary and the project-wide template guards. Also checked by hand: `manage.py seed_a1_course --check` still prints its four
known data errors cleanly (no traceback — proof the validation rewrite works), and the seven
management-command modules were imported one by one: five import, and the two that fail do so
only on the missing `vocabulary.german_text` module (§5.30), which is unrelated to the pass.

> **`.venv/bin/python`, not `python`.** The bare `python` on this machine is the system
> interpreter (`/usr/lib/python3/dist-packages`), which has no `psycopg`, so every management
> command dies with `Error loading psycopg2 or psycopg module`. Always use the venv.

- `lessons/tests.py` — structural A1 content checks (seeds content into the test DB).
  **Blocked by the data bug in §5.0** — it aborts and reports no summary.
- `vocabulary/tests.py` — **26 tests, green.** Published-only list with real level counts,
  the level-scoped view and its tab ordering, pagination (24/page, page state, prev/next
  semantics), the shared `.chip` primitive and no retired classes/scripts, the word detail's
  real fields (article/gender/plural/pronunciation/meaning in both languages), the lessons
  that teach the word and the exercises that test it, no invented fields, and the lookup
  endpoint's contract (empty `q` → 400, unknown word → empty list, Persian type label,
  audio URL, published-only).
- `exercises/tests.py` — **63 tests, green.** Five groups:
  - `ExerciseIntegrityTest` (9) + `LessonExerciseDisplayTest` (1, skips on an empty test DB —
    §5.3) as before. Note the integrity group iterates `Exercise.objects.all()`, so on a
    **fresh test DB it is vacuous** (no exercises exist there — §5.1).
  - `ExerciseListViewTests` (9): anonymous access, its own stylesheet and not `reader_modern.css`,
    drafts hidden, one group per lesson with its own count, real `question_total`/`lesson_count`,
    the `?lesson=` scope (including the instruction and a lesson with no exercises), and a 404
    for an unpublished lesson.
  - `ExerciseRunnerTests` (16) + `ExerciseRunnerBuilderTests` (4): one row per real answer shape
    (4-option, 2-option, distractor `FILL_BLANK`, typed `FILL_BLANK`, `TRANSLATION`, `READING`
    with a `CONTEXT` sentence, a question with no answer, an exercise with no questions),
    position-based numbering, progress semantics, hidden-by-default controls, inline feedback
    and no `alert(`, the unchecked question kept out of the score, the results state, the next
    published exercise, and `build_runner`'s kind/numbering/passage/option rules.
    Three of these were **rewritten in Phase 8** and must stay rewritten: the page must carry
    no `data-correct` and no typed answer's text, `data-submit-url` must be present, and the
    disclosure must tell an anonymous visitor that nothing is saved and a signed-in learner
    that their answers are recorded.
  - `ExerciseSubmissionTests` (11), `WordProgressTests` (6), `GradingTests` (7) — Phase 8.
    Anonymous is graded but stores nothing; a correct/wrong answer stores one attempt with the
    real question, the chosen `Answer` row and the response time; a typed answer is kept
    exactly as typed (while case/spacing/trailing punctuation are forgiven for the verdict);
    the explanation comes back with the verdict; every submission is a new row; response
    times that are missing, non-numeric, negative or over an hour are dropped; an answer from
    another exercise, an option of another question, and a question with no authored answer
    are all refused with a 400; and `WordProgress` counts the `TESTED_ITEM` word only,
    accumulates across attempts, and never touches a `CONTEXT` word.
    All built from a fixture (`ExercisePageTestBase`) because a test DB has no exercises.
- DB-backed tests need permission to create a test database; if that is unavailable,
  use `python manage.py validate_a1_content` as the read-only fallback.
- `accounts/tests.py` — signup, login (valid/invalid/`next`), POST-only logout, profile
  access rules, on-demand profile creation, and anonymous-first access (18 tests, green).
  Its home-page test now asserts the dashboard renders anonymously, not a redirect.
- `lessons/tests.py::DashboardTests` — 9 tests: anonymous access, published-only counts,
  the lesson payload handed to the browser, the browser-only progress disclosure, the
  optional account CTA, the empty state, and the `data-lesson-id` hook.  Runnable alone:
  `python manage.py test lessons.tests.DashboardTests`.
- `lessons/tests.py::LearningPathTests` — 11 tests: every published lesson appears exactly
  once, nothing is paginated, unpublished lessons and lesson-less courses are excluded,
  grouping is in level order, the payload shape/order, the server rendering every step as
  not-started, durations, the course-scoped page, no locked/premium wording, and the empty
  state. Runnable alone: `python manage.py test lessons.tests.LearningPathTests`.
- `lessons/tests.py::LessonJourneyTests` — 18 tests: the step sequence follows the lesson's
  own content and order, every step is rendered server-side, counts come from published rows
  only, a lesson with no grammar/sentences/exercises grows no such step (and one with no
  content grows no fake steps at all), the intro agenda lists only material steps, German is
  LTR with the translation following in RTL, a speaker appears only where the data has one,
  word cards show only fields the word has, audio is never invented, no interactive element
  is nested inside a link, the vocabulary step paginates inside the step, the practice step
  offers the real exercises with their size, the finish step offers the next lesson, no
  locked/premium wording, and unpublished lessons are unreachable. Runnable alone:
  `python manage.py test lessons.tests.LessonJourneyTests`.
- `lessons/tests.py::LessonProgressTests` — 12 tests (Phase 8): the journey step keys and the
  model's `Step` values are the same ten names in the same order, the first visit starts the
  lesson at its first step, coming back does not reset `started_at` (and does not create a
  second row), moving a step moves `last_activity_at` only, completing sets `completed_at`,
  completing twice does not move it, reading a finished lesson does not un-finish it, each
  lesson keeps its own row, and `progress_state` reports `started`/`completed`, leaves an
  untouched lesson out entirely, and picks the most recently touched lesson as `lastLessonId`.
- `lessons/tests.py::LessonProgressEndpointTests` — 14 tests (Phase 8): an anonymous POST is
  403 and writes nothing; a move is recorded and the response carries exactly the five facts
  (`status`, `current_step`, `started_at`, `last_activity_at`, `completed_at`); completing
  reports `completed_at`; an unknown step is a 400 with nothing written; **a GET is a 405 and
  writes nothing**; an unpublished lesson is a 404; the lesson page opens on the stored step
  (and a stored step that is no longer part of the journey is ignored rather than breaking the
  page); `data-progress-url` and `progress-state` appear only for a signed-in learner; and the
  dashboard and the path ship the same payload.
- `tests/tests.py` — 3 tests (Phase 9): no template anywhere contains a multi-line `{# #}`
  comment (the regression guard for §5.4 — it walks the project's `templates/` **and** every
  app's), and both error pages render, the 500 with an empty context exactly as Django
  renders it. The template guard is the only test that reads files rather than the DB.
- Runnable together today (**174 tests, green, 1 skipped**):
  `python manage.py test tests accounts vocabulary exercises lessons.tests.DashboardTests lessons.tests.LearningPathTests lessons.tests.LessonJourneyTests lessons.tests.LessonProgressTests lessons.tests.LessonProgressEndpointTests`.
  Split: tests 3, accounts 18, vocabulary 26, exercises 63, lessons (those five classes) 64.
  `python manage.py test` as a whole still aborts at the seeding class (§5.0).
- `makemigrations --check --dry-run` is **clean** after Phase 8 — the only model change
  (`ExerciseAttempt.response_text`, nullable `answer`, plus two `__str__` methods) is captured
  in `exercises/0003_exerciseattempt_response_text_and_more`, and the exercise/word labels are
  still properties rather than fields.
- **Verifying commands:** `python manage.py check`, plus `test accounts vocabulary exercises`.
- Beware pipelines: `python manage.py test lessons | tail` masks the real exit code.

### Browser verification (Phase 9 frontend audit & polish)

**Every learner-facing route, at four widths (390/768/1024/1440), in Chromium against the
live dev server and the real 24-lesson database**: `/`, `/lessons/`, `/lessons/courses/1/`,
`/lessons/1/`, `/lessons/12/`, `/lessons/24/`, `/vocabulary/`, `/vocabulary/words/level/A1/`,
`/vocabulary/words/1/`, `/exercises/`, `/exercises/?lesson=1`, `/exercises/21/`,
`/exercises/22/`, `/accounts/login/`, `/accounts/signup/`, `/accounts/profile/`, and two
404 routes — 72 route loads. Each one was checked for horizontal overflow, tap targets,
unrendered template syntax, text contrast, clipped text, broken images, `h1` count, console
errors and 4xx/5xx responses. Result: **zero** of those, apart from Django's own debug 404
page while `DEBUG = True` (it overflows by 18px at 390px and probes `/favicon.ico` — that
page belongs to Django, not to us; the real 404 template was audited separately below).

**Interaction pass: 37 anonymous checks + 10 signed-in checks, all green, no console error
and no 5xx.** Anonymous: step forward/back, chip jumps moving focus to the step heading,
`prev` disabled on the first step and `next` on the last, exactly one step on screen, the
progress bar at 100%, no horizontal scroll at 360px, the bottom nav at exactly the 66px
token with every nav destination present, the exercise runner's verdict landing inline and
marked in words as well as colour, an empty typed answer showing a hint instead of failing,
and a JavaScript-off page keeping all eight steps readable with no dead play button.
Signed-in (throwaway account, deleted afterwards): login, the dashboard no longer claiming
progress lives in this browser, the step POSTed on a chip jump, **the reload resuming from
the server's stored step**, the finish button locking once complete, and the DB checked
afterwards — 1 `LessonProgress` (`completed`/`finish`, `started_at` + `completed_at` set),
1 `ExerciseAttempt` (real question, chosen answer, `is_correct`, `response_time` 0.6), and
1 `WordProgress` for the `TESTED_ITEM` word with `attempt_count == correct + wrong`.

**Error pages (throwaway `DEBUG=False` server on :8012, since the dev server replaces them
with its debug pages):** the real 404 and 500 were opened at all four widths — correct
title, one `h1`, no overflow, no console error, the 404 keeping the full app shell and its
three action links resolving to real URLs, the action-links and monogram present on both,
and `/static/img/favicon.svg` answering 200.

**Two audit-script faults are recorded because they will recur:** (1) the tap-target probe
measured the *anchor* box, so the learning path's cards (17px anchor + stretched `::after`)
and the exercise index's group headings looked broken when a tap anywhere on the card lands
on the link — the probe now resolves the effective hit box and separates WCAG 2.2 AA (24×24,
a failure) from the 44px comfort guideline (advice); (2) the lesson's steps are hidden by CSS
(`.js .journey-step:not(.is-active)`), so counting `:not([hidden])` reports all of them —
count rendered boxes instead.

### Browser verification (Phase 8 backend progress)

**82 machine checks pass** (Playwright, Chromium, live dev server + the real 24-lesson
database, 390 px viewport): **49 anonymous, 33 signed in**. The signed-in pass used a throwaway
account (`phase8_check`) which was deleted afterwards with its 1 `LessonProgress`,
6 `ExerciseAttempt` and 6 `WordProgress` rows, so those three tables are empty again.

What was actually verified: the anonymous lesson page still renders the journey, still offers
no `data-progress-url` / `data-resume-step` / `progress-state`, still stores the step in
`localStorage` and still drives the dashboard from it; the runner submits to
`exercises:exercise-submit` with a CSRF header, one POST per question, and the request carries
`question` + `answer` (or `response_text`) + a numeric `response_time` and **no** `is_correct`;
the page source has no `data-correct` and no expected-answer text; a wrong option is flagged
wrong while the right one is flagged correct **in words as well as colour**; a wrong typed
answer reveals the server's expected answer and matches the response; a correct answer does not
repeat it and is accepted with different case/spacing/trailing punctuation; an empty
submission is refused without a request; the results screen appears only after the last
"next", its score comes from the returned verdicts, and retry returns to question 1; a failed
request keeps the question open and says why; with JavaScript off the questions are readable
and no control is offered; and the only console error and only 4xx is the known
`/favicon.ico` (§5.10).

The failures encountered in the anonymous pass were **script faults, not app bugs** (worth
remembering for the next pass): always picking the first radio option happened to be correct
every time, so the "wrong answer" check never fired; the results screen needs the last
question's "next" clicked, not just a submit; and Chromium serialises an empty attribute as
`data-expected-value=""`, so an exact-string assertion against the Django-rendered HTML fails.

**Signed in (33 checks).** Two separate browser contexts were used on purpose, the second with
empty `localStorage`: the first walked to the fourth step of lesson 1, and the second — a
"different device" — logged in, opened the lesson and landed on **the same step**. That is the
only real proof that resume comes from the server rather than the browser. Also verified: the
lesson page is offered `data-progress-url` (and an anonymous visitor is not), the first step is
saved on open, each step is sent exactly once, nothing at all is written to `gam.progress.v1`
for a signed-in learner (neither steps nor exercise results), completion asks the server and
then shows a disabled «کامل‌شده», the dashboard reads `1 از 24 درس کامل‌شده` and says progress
is on the account, the path marks lesson 1 `is-completed`, and all four choice submissions plus
two typed ones came back `recorded: true` with a measured response time.

Database rows written by that pass, checked afterwards: `LessonProgress` — status `completed`,
`current_step` `finish`, all three timestamps set, `completed_at >= started_at`, one row;
`ExerciseAttempt` — 6 rows (4 choice with an `answer`, 2 typed with `response_text`, never
both), 4 correct / 2 wrong, each with a `response_time`; `WordProgress` — 6 rows, every
`attempt_count` equal to `correct_count + wrong_count`, timestamps consistent with the
counters **and, the important one, the counted words were exactly the `TESTED_ITEM` words of
the answered questions — no `CONTEXT` word was ever counted**.

**A real copy bug the signed-in pass caught:** `path.js::progressNote()` told a signed-in
learner «پیشرفت روی همین مرورگر نگه داشته میشود». The template's default line had been made
honest, but the script overwrites it. `path.js` and `dashboard.js` now branch on
`progress.serverBacked` before saying anything about this browser. **Lesson: any page script
that replaces a progress sentence needs the `serverBacked` check — the templates are
conditioned, but the scripts own the text once they run.**

### Browser verification (Phase 4 learning path)
Against the live dev server and the real 24-lesson database: **107 machine checks pass**.
The only console error on any page is the known `/favicon.ico` 404, confirmed by URL
(§5.10). (Three checks first reported as failures were faults in the verification script
itself: the active-nav comparison was glyph-sensitive — ZWNJ — but is an exact match, and
the dashboard preview was asserted to contain completed rows when it correctly shows the
four steps *ahead* of the current lesson.)
Verified across the whole state machine: fresh (lesson 1 current, 23 upcoming, 0% bar,
"هیچ درسی کامل نشده"), one lesson opened (current moves, nothing completed), 3 completed
(13% bar, "3 از 24 کامل", current jumps to the first unfinished lesson), middle (12 done,
exactly 50%), last lesson (23 done, 96%, lesson 24 current, no upcoming left), and all 24
done (100%, no current step, the next-step row stops offering lesson 1). Plus: the dashed
spine starts at the first upcoming step; clicking a step opens that lesson and coming back
moves the current marker; blocked storage still renders a usable trail and says so; the
course-scoped page lists only its own course. Layouts 360/390/768/1024/1440: no horizontal
overflow, no contrast failures, the marker stays exactly on the spine at every width, and
the mobile layout is re-proportioned (28px markers, clamped descriptions, full-width
actions) rather than shrunk. A11y: one `h1`, a real `<ol>`, `aria-hidden` decorative
markers, a text chip on every step, accessible names on every action, progressbar min/max/now.
The dashboard was re-verified after its refactor: same 13% bar as the path, continue card on
the first unfinished lesson, shared `.progress` markup, and no preview row claiming a
completion it does not have.

### Browser verification (Phase 3 dashboard)
Against the live dev server and the real 24-lesson database: **72/73 machine checks pass**,
the single miss being the `/favicon.ico` console line (§5.10). Verified: anonymous empty
state → "شروع درس 1"; opening `/lessons/1/` writes `gam.progress.v1` and the dashboard
returns as "قدم بعدی" + "ادامهٔ درس 1" + `1 از 24 درس شروع‌شده` with `aria-valuenow=4`;
the path window re-anchors on the current lesson, stays contiguous, and **does not
collapse at the end of the course** (`markVisited(24)` still yields lessons 21–24);
`markCompleted` renders "کامل‌شده"; a corrupt `gam.progress.v1` degrades to the empty state
instead of throwing. No contrast failures and no horizontal overflow at 360/390/768/1024/
1440; bottom nav 66px below 900px, sidebar above it; one `h1`, skip link present,
progressbar min/max/now exposed, every nav link labelled. Signed in: greeting, no upsell,
profile link, progress still disclosed as browser-local, and lessons stay public.
**Gotchas found here:** JS-built path rows must carry the same `data-path-state` hook the
server-rendered rows do (they did not at first), and the preview window must slide back
near the end of the course instead of shrinking to a single row.

### Browser verification (Phase 7 vocabulary, grammar, dialogue & listening)

Playwright against the live dev server and the real database (1,008 words), in two passes:
**110 machine checks, all green** (70 on vocabulary + lookup + audio, 40 on regressions
across the rest of the product). The only console error and the only 4xx stay `/favicon.ico`
(§5.10).

| Check | Result |
|---|---|
| Word list | 24 rows/page, one `h1`, German term is a real `lang="de" dir="ltr"` link to the word page, Persian meaning present, type + level chips from the shared primitive, **24 players for 24 rows and none inside the link**, page state stated once (`1008 واژه` · `صفحهٔ 1 از 42`), labelled pagination with `قبلی` disabled on page 1, and **no search box invented** |
| Level tabs / pagination | `همهٔ سطح‌ها 1008` then `A1 1008` with the current tab marked by `aria-current` **and** a text state (no colour-only meaning); page 2 and page 42 hold different/remaining words and offer a way back |
| Word detail | the German word is the only `h1` and is marked German+LTR, `اسم | A1` chips from the model, pronunciation, the **shared** audio control (real `/media/words/audio/*.mp3`, 200), meaning in both languages, grammar facts only from populated fields, the real lessons that teach it and the real exercises that test it, no decorative flag/tagline, a way back to the list |
| Word lookup | still tokenises the lesson prose (>100 tokens, `span[role=button]`, none nested in a link); click opens the popover with real data + audio and sets `aria-expanded`; **Escape** and an outside click close it; a failing response says `دریافت معنی انجام نشد` instead of a silent empty box; an unknown word returns an empty list (200, not an error); keyboard focus opens it; on a phone the popover stays above the 66px bottom nav |
| No-JS | the list is complete (24 rows, 24 terms, 24 download links) with **no dead play buttons and no hidden players**; the word page still reads fully |
| a11y / responsive | 0 contrast failures on the list; 3px focus ring; one `h1`; no horizontal overflow at 360/390/768/1024/1440; dialog/level tabs carry accessible names |
| Audio | the grammar topic's player reveals a real `<audio>` whose `/media/…mp3` request answers 200; one player stops the others |
| Regressions | 40/40 across dashboard, learning path (24 steps + states), lesson journey (8-step sequence, 24 word cards with 25 players, grammar in 5 paragraphs with an `H3` title, 10 dialogue lines with 10 speakers, 5 practice links, one active step, live bar), dialogue script layout (beside the line on desktop, stacked on a phone), exercise list (23 groups/111 cards/222 chips), exercise runner (4 badges, bar max 4, real grading + advance), login form, and `/accounts/profile/` still redirecting anonymously to login |

### Browser verification (Phase 6 exercise experience)

Playwright against the live dev server and the real database (111 exercises / 296 questions):
**three passes, 155 machine checks, all green** — 39 on the list, 67 on the runner flow, 49 on
responsive + a11y + no-JS. The only console error and the only 4xx remain `/favicon.ico`
(§5.10).

| Check | Result |
|---|---|
| Exercise list | 23 lesson groups (lesson 12 has no exercises), 111 cards, per-group counts `5 تمرین`…, `درس 1 — Hallo! Begrüßung und Vorstellung` linking to `/lessons/1/`, lead `111 تمرین در 23 درس · 296 پرسش`, one `h1`, no nested interactive inside a card link |
| Scoped list | `?lesson=1` → 5 cards with the instruction, no grouping, heading names the lesson; `?lesson=12` → real empty state with a way back to the lesson |
| Runner flow (ex 21, 4 questions) | starts on `سؤال 1 از 4` with the bar at 1/4; unanswered submit → inline message, nothing submitted; wrong → `درست نیست` + `پاسخ درست: سلام` revealed + options disabled + `بعدی` revealed + focus moved there; correct → `درست است` and the answer block stays hidden; back → the submitted state is still there; last question → `دیدن نتیجه` |
| Results | `2 از 4 پاسخ درست`, `دقت: 50٪`, both missed questions listed with their number and prompt, questions + bar hidden, results focused, primary `/lessons/1/`, next exercise `/exercises/22/`, `تلاش دوباره` present; a missed entry jumps back to that question and `دیدن نتیجه` returns |
| Retry | back to question 1 with a 1/4 bar, every radio unchecked and re-enabled, feedback cleared |
| Typed answers (ex 22) | no options, German `dir="ltr" lang="de"` field, empty submit → inline message, **Enter** submits, `  GUTE  nacht! ` accepted for `gute Nacht`, a wrong answer marks the field and reveals `auf Wiedersehen` |
| Other real types | `FILL_BLANK` with distractors → 2 options + explanation; `READING` → `Guten Morgen!` as a real German LTR passage above its options; `TRUE_FALSE` → `سؤال 1 از 2` (stored `Question.order` is 12) and the authored explanation |
| One-question exercise (ex 91) | no bar, `سؤال 1 از 1`, only action is `دیدن نتیجه`, authored answer accepted → `1 از 1`, `100٪`, the "all correct" line shown |
| Mobile 360 / 390 / 768 | no horizontal overflow; bottom nav still exactly 66px; the action bar pins 66px above it while the question is taller than that space, stays inside its card (no bleed), and is clear of the nav at the end of the page; every tap target ≥44px; prompt ≥16px |
| Desktop 1024 / 1440 | content column 702 / 836px (≤900), cards not full-bleed, sidebar present, no overflow |
| a11y | one `h1`; one `h2` per question; every radio group a `<fieldset>` with a visually-hidden `<legend>`; every radio inside its `<label>`; every visible control named; `role="progressbar"` with min/max/now + label; 3px focus ring via keyboard; arrow keys move the selection and the `.is-selected` state follows; `✕ درست نیست` + `درست`/`نادرست` flags mean nothing is colour-only; reduced motion → `transition-duration: 0s` |
| No JavaScript | 4/4 questions visible and readable, 16 options readable, **0 controls visible**, bar hidden, answers still hidden, `<noscript>` note visible |
| Journey regression | `/lessons/1/` practice step still lists its 5 exercises, links to `/exercises/21…25/`, labels from the model (`چندگزینه‌ای`…`درست / نادرست`), difficulties `آسان|آسان|متوسط|متوسط|متوسط`, sizes `4 پرسش|2 پرسش|…` |

**Five apparent failures were faults in the verification script, not the app** — worth knowing
before writing the next one:
1. `console` messages do not carry the URL in `m.text()`; a 404 line is only attributable via
   `m.location().url`. Without it the known favicon noise looks like a real error.
2. `بعدی` is **deliberately withheld until a question is submitted**, so a script that clicks it
   on an unanswered question times out (that is the design, not a bug).
3. A `position: sticky` element only pins while its containing block still crosses the sticky
   line — the first version scrolled past the end of the card, where the bar correctly rides
   with it. The check now brings the card into view and asserts both the pinned offset and
   that the card still extends past it.
4. Reviewing a **non-last** missed question and pressing its own `بعدی` advances to the next
   question instead of returning to the results (only the last question offers
   `دیدن نتیجه`). The script now reviews the last missed question.
5. Exercise 91's answer was guessed in the script rather than read from the data, so the app
   graded it wrong (correctly). The fix was to read the authored answer out of the hidden
   reveal block and submit that.

### Browser verification (Phase 5 lesson journey)
Playwright against the live dev server and the real 24-lesson database: five passes, ~120
machine checks, all green once the two real fixes below landed (six apparent failures were
faults in the verification script itself — see the end of this note).

Covered: the step sequence of lessons 1 / 12 / 24, the chip row, the progress bar and its
`aria-valuenow` at every step, the forward and backward walk, `#step-…` history, resuming the
remembered step after a reload, jumping out of order from a chip (with focus moved to the step
heading), the agenda (material steps only, counts from real data: `2 بخش | 40 واژه | 7 موضوع |
4 جمله | 8 جمله`), vocabulary pagination inside the step (167 words → 7 pages, and page 2
returns to `#step-vocabulary`), the practice step linking to real exercises, completion
propagating to the path **and** the dashboard (same `aria-valuenow`, same `1 از 24`), blocked
storage, JavaScript disabled, mobile at 360/390, contrast across all 8 steps at 1440 and 390,
and the a11y basics.

| Check | Result |
|---|---|
| Steps, chips, ordering | lesson 1: `intro>explanation>vocabulary>grammar>examples>dialogue>practice>finish`; lesson 12 (no exercises, no dialogue) drops both; lesson 24 keeps both |
| Progress + history | bar reaches 100 at the finish step, `#step-…` tracks every move, the next button names the step ahead (`بعدی: توضیح`) |
| Resume | the remembered step survives a reload |
| Lookup | 512 tokens on lesson 1, opens real data, Escape closes, works by Enter, stays inside the viewport at 390px, no nested interactives |
| Audio | real files only, 200 responses, the play button reveals the player |
| No JavaScript | 8/8 steps visible, no stepper buttons, no dead completion button, 49 download fallbacks |
| Mobile 360/390 | no overflow; the sticky action bar ends exactly where the 66px bottom nav starts; taps ≥40px; header 331px |
| Direction | page RTL, German `ltr`, every Persian element RTL |
| Contrast | 0 failures across 8 steps × 2 widths |
| A11y | one `h1`, one `h2` per step, accessible names on every visible control, 3px focus outline, reduced motion honoured |
| Console / HTTP | `/favicon.ico` 404 is the only error (§5.10) |

**Two things verification caught that the tests could not:**
1. **The multi-line `{# … #}` comment bug** (§4): 110 leaked comment blocks per lesson page,
   and a stray `<audio>` inside one of them turned every audio control on the page into a
   zero-sized, unclickable element. Fixed across 13 templates.
2. **A dead "mark complete" button when storage is blocked** — it looked live but recorded
   nothing. Now the button is withheld and the learner is told why.

**Four apparent failures were script faults, not app bugs:** the script asserted the `h1` is
RTL (the lesson title is *German*, so `dir="auto"` correctly resolves LTR), counted both
agendas as one, looked for `data-path-state="completed"` (the path marks state with a CSS
class — `is-completed` — and puts its text in `[data-step-state]`; `[data-path-progress]` is a
`<p>`, the bar is `[data-path-bar]`), and required lookup tokens to be `<button>` (they are
`span[role=button]` with real Enter/Space handling — a legitimate custom button).

### Browser verification (Phase 0)
A Playwright + system-Chromium audit is available without installing anything. **Load it as
`NODE_PATH="/home/sina45v/node_modules" node script.js` with `require('playwright-core')`** —
`playwright` is *not* under `$(npm root -g)` (that holds `agent-browser`, `9router`, …), so the
older `NODE_PATH="$(npm root -g)"` form fails with MODULE_NOT_FOUND. Launch with
`chromium.launch({ executablePath: '/usr/bin/chromium-browser', args: ['--no-sandbox'] })`, and
start the server in the same shell call (`nohup … runserver 127.0.0.1:8011 --noreload &`) — a
background server does not survive between tool calls. It checked computed styles,
text/background contrast, horizontal overflow at 360/390/768/1440, the nav toggle, and
audio fetches. Results after Phase 0: **all 14 design tokens resolve** (canonical and
legacy aliases alike), every card renders `--surface` on a `--line` border, **zero
contrast failures across all seven pages**, no horizontal overflow at any tested width,
nav toggle works, audio fetches return 200, and `#theme-toggle` is gone.

**Phase 1 shell checks.** Sidebar is fixed at the inline-start edge (right in RTL):
`R == innerWidth`, `L == innerWidth - 258`, and the content column ends exactly at the
sidebar's left edge, so nothing overlaps. Below 900px the sidebar and app bar swap for
the app bar + bottom nav, which renders the same three links. Active state verified per
section (lessons → درس‌ها, vocabulary → واژه‌ها, exercises → تمرین‌ها) and a real click
through both surfaces navigates and moves the active state. No horizontal overflow at
360/390/768/1024/1440. **Gotcha:** the fixed bottom bar must keep its explicit
`height: var(--bottom-nav-h)` — with `height: auto` the flex container resolved its own
height from children that `align-items: stretch` had already stretched, and the bar grew
to 107px at ≤390px (which pushed the lesson floating actions under it).
