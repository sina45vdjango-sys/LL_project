# REPORT.md — what this run changed, and how each change was checked

Status of every item this run touched, with the commit, the files, the evidence and the
numbers measured on the **mirror** database (`language_learning_mirror`). The audit IDs
belong to `CONTENT-AND-PRODUCT-AUDIT.md`; the plan and acceptance criteria per item are in
`FIX-PLAN.md`; the honest re-score is in `RESCORE.md`; what was deliberately not done is in
`DEFERRED.md`; the decisions that are the owner's are in `OWNER-DECISIONS.md`.

Statuses: `DONE` (implemented + tested + seen in a browser), `PARTIAL` (the safe part was
done and the rest is written down), `ALREADY` (already true in the code, verified, no change
needed), `DEFERRED`.

---

## The commits

| Commit | Items | Subject |
|---|---|---|
| `c1a3ecb` | P-12, P-15, P-26, P-27, P-28 | close the audit's dead ends, tap targets and type floor |
| `74088dd` | P-06, P-07, P-14 | give `/` a Persian front door and the course's own numbers |
| `99c0529` | P-02, P-01, P-20 | draw the exam from a curated set, not from every drill |
| `d87eb79` | P-19 (half), P-21 | drill a lesson on the rules it teaches, and cap the dictation drills |
| `6dc1d0a` | P-18, P-30 | bring this browser's progress onto the account, and close the course |
| `f8439e3` | P-17 (half) | one copy of the audio icons instead of 110, and record the browser run |
| `cd83daa` | G (explanation, keyboard) | answer with 1–9 and Enter, and say why a right answer is right |

Nothing was pushed. The branch `audit-quality` also still carries the earlier phase's
uncommitted working tree (the Phase A fixes and the audit documents themselves, ~170 paths
that were already modified when this run started); they are untouched by these commits and
still uncommitted, because they are not this run's work and committing them under one of
these messages would misattribute them.

---

## DONE

### P-01 + P-20 — the exam is a curated set, and the composition is locked
- **Commit:** `99c0529`. **Files:** `exams/sections.py` (new), `exams/data/a1_exam_items.json`
  (new), `exams/management/commands/export_a1_exam_items.py` and `import_a1_exam_items.py`
  (new), `exams/paper.py`, `exams/models.py`, `exams/spec.py`, `exams/step.py`,
  `exercises/models.py` (`Question.exam_section`), `exams/templates/exams/exam_index.html`,
  `exams/tests.py`.
- **Why:** the exam used to be built from *every* published question, so any new drill
  changed the exam — and it drew 13 of 15 listening items from one-word dictation.
- **What changed:** an exam section is now a property of the row (`Question.exam_section`),
  read from a version-controlled list of 135 items (45 per section, three papers). Sections
  are drawn round-robin across 23–24 lessons; hearing and reading items are full sentences
  and short passages, not single words.
- **Migration:** `exercises/0006_question_exam_section` — one `AddField`, applied to the
  mirror only.
- **Evidence:** `ExamCurationTests` (unanswered and scramble questions are never marked, a
  marked row outside the file is cleared, an unknown reference is an error, two sittings are
  not the same paper, `section_of(p) == p.exam_section` for every marked row).

### P-02 — `/exam/` stopped classifying the whole question table
- **Commit:** `99c0529`. **File:** `exams/paper.py` (`section_pools` → the marked rows only).
- **Evidence, measured this run (curl, local runserver, mirror):**

  | | audit | now |
  |---|---|---|
  | `/exam/` TTFB | 585 ms | **81 ms** |
  | `/exam/` HTML | 18.4 KB | 19.5 KB |

  `paper_problems()` is 39 ms of that; the rest is the page. The audit's cause was
  `prefetch_related` over ~10,000 questions; the curated set removes the need to read them.

### P-06 + P-07 — the front door
- **Commit:** `74088dd`. **Files:** `templates/includes/front_door.html` (new),
  `templates/dashboard.html`, `lessons/views.py`, `lessons/models.py`,
  `lessons/management/commands/seed_a1_course.py`, `lessons/templates/lessons/lesson_list.html`,
  `course_detail.html`.
- **What changed:** an anonymous visitor now reads, above everything else, what this is, who
  it is for, what is inside it (numbers counted from the database) and one call to action —
  and the course has a Persian description instead of an English one.
- **Evidence:** the browser run below checks `/` at three widths; `DashboardTests` covers the
  numbers.

### P-12 — the dead ends became pages
- **Commit:** `c1a3ecb`. **Files:** `templates/403.html`, `templates/405.html` (new),
  `config/middleware.py` (new), `config/settings.py`, `accounts/views.py`, `exams/views.py`.
- **What changed:** `GET /accounts/logout/` and `GET /exam/start/` no longer answer a blank
  405; a browser method-mismatch renders the product shell while keeping the 405 status.
- **Evidence:** verified in Chromium: a 405 navigation shows the shell and the sidebar
  (`/accounts/theme/`), and the same URL with `Accept: application/json` still gets the plain
  empty 405 — the rule the middleware exists for. `MethodNotAllowedPageTests` in `tests/tests.py`.

### P-14 — the dashboard's numbers are the course's own
- **Commit:** `74088dd`. **File:** `lessons/views.py`.
- **What changed:** `2,208` word rows belonged to no lesson but were counted on the front
  page. Word, exercise and question totals are now scoped to the published lessons of the
  published course, and drafts are excluded.
- **Evidence, mirror:** the front door says **1,018 واژه / 745 تمرین / 24 درس**, matching
  `LessonWord.objects.filter(lesson__in=lessons, word__is_published=True).values("word_id").distinct().count()`.

### P-15 — the lesson list rows are 44px targets
- **Commit:** `c1a3ecb`. **File:** `lessons/static/lessons/css/lesson_path.css`.
- **Evidence:** measured in the browser at 390×844, 820×1180 and 1440×900: the `.path-step__link`
  box is **44px** (it was 17px), and the whole card still falls through to that link.
  `LearningPathTests.test_the_title_link_is_itself_a_forty_four_pixel_target`.

### P-16 — the exercise verdict's live region
- **Commit:** `c1a3ecb` (no code change). **ALREADY.**
- The audit reported no `aria-live` in the served exercise HTML. It is there:
  `[data-runner-feedback]` and `[data-runner-help]` are `role="status" aria-live="polite"`,
  `[data-runner-hint]` is `role="alert"`. Nothing was changed, because nothing was wrong.

### P-18 — a visitor's progress follows them onto their account
- **Commit:** `6dc1d0a`. **Files:** `lessons/views.py` (`LessonImportView`),
  `lessons/urls.py`, `lessons/progress.py` (`import_guest_progress`),
  `static/js/progress.js` (`guestRead`), `static/js/progress_import.js` (new),
  `templates/dashboard.html`, `static/css/dashboard.css`, `lessons/tests.py`.
- **Why:** a visitor learns without an account, so their lessons live in `localStorage`;
  signing up switched the dashboard to the server's answer, which knew nothing about them.
- **What changed:** the dashboard compares the two, asks, and posts what the browser claims
  to `lessons:lesson-import`. A claim can only create a lesson the account never opened or
  move a started lesson to finished: it can never un-finish one, it never touches another
  learner's rows, and a report the server does not understand is refused rather than guessed
  at. Declining deletes the browser's copy.
- **Evidence:** `GuestProgressImportTests` (11 tests: anonymous 403, GET 405, broken input
  400, unpublished ids ignored, no un-finishing, second import writes nothing, per-user
  isolation, panel markup only for a signed-in learner). In Chromium: planting a completed
  lesson in `localStorage`, signing in, seeing the offer count it as **1**, pressing accept,
  then the browser's copy gone, the offer gone and the lesson on the dashboard.

### P-21 — the dictation drills have a cap
- **Commit:** `d87eb79`. **File:** `exercises/management/commands/seed_a1_dictation_drills.py`.
- **Why:** lesson 24's closing word bank produced **154 dictation questions in one exercise**
  — a wall, not practice.
- **What changed:** the same 30-word cap `seed_a1_word_drills` uses, applied in the lesson's
  own teaching order. The words past the cap stay linked, so `vocabulary/schedule.py::new_words`
  still offers them in the review queue — the cap decides one sitting, not which words exist.
- **Evidence, mirror, after regenerating:** lesson 24 went from 154 to **30**; the worst
  lesson is now 30; `Built 115 dictation drill(s) with 688 questions, replacing 176`.
  `SeedA1DictationCapTests` (3 tests: the cap holds, no word is orphaned, a small lesson is
  untouched).

### P-25 — speaking: hear the model, record yourself, compare
- **ALREADY** in the code (`exams/static/exams/js/sprechen_recorder.js`,
  `exams/templates/exams/sprechen.html`), verified this run.
- The page plays the model recording, records the learner locally (nothing is uploaded,
  nothing is stored), plays it back, and lets them mark a phrase as said. Without
  `MediaRecorder` or without permission the record buttons are removed and the page keeps
  working; one recorder runs at a time. The audit's other half of P-25 — a standalone
  free-writing task — is deferred by the owner's own instruction (see `DEFERRED.md`).
- **Limitation:** the microphone cannot be exercised here — this Chromium runs headless and
  the site is served over plain HTTP on a LAN address, where browsers refuse the microphone.
  What was verified is that the page renders, the buttons are present, and the self-report
  works without a microphone. The note in `DEFERRED.md` says HTTPS is required outside localhost.

### P-26 — where signing in lands
- **Commit:** `c1a3ecb`. **Files:** `config/settings.py` (`LOGIN_REDIRECT_URL = 'home'`),
  `accounts/views.py`.
- **Evidence:** a signed-in login lands on `/` (checked in the browser at three widths); a
  valid `?next=` is still honoured and still passes `url_has_allowed_host_and_scheme`, and
  the open-redirect case is still tested.

### P-27 — the type floor
- **Commit:** `c1a3ecb`. **Files:** `static/css/shell.css` and three other stylesheets
  (`.brand__latin` was 9px; the rest were 10–11px declarations).
- **Evidence:** a project-wide scan of every served stylesheet finds no `font`/`font-size`
  below 12px, and the browser run reads `.brand__latin` as **12px** at three widths.

### P-28 — the favicon, and motion
- **Commit:** `c1a3ecb`. **Files:** `config/settings.py` (`FAVICON_PATH`), `config/urls.py`.
- **Evidence:** `GET /favicon.ico` answers **200** `image/svg+xml` in the browser (it was a
  404); `prefers-reduced-motion` was already honoured in `dashboard.css`, `base.css`,
  `shell.css` and `components.css` (transitions are inside
  `@media (prefers-reduced-motion: no-preference)`) — verified, not duplicated.

### P-30 — the course closes instead of stopping
- **Commit:** `6dc1d0a`. **Files:** `lessons/views.py`, `lessons/templates/lessons/steps/_finish.html`,
  `lessons/tests.py`.
- **Why:** the course ended at lesson 24 with one sentence and a link back, at exactly the
  point a learner decides whether to stay.
- **What changed:** the last lesson names the finish, counts the course *from the course*
  (`24 درس از 24`), and offers the three things that are really next: the mock exam, the
  words they got wrong, and the daily review. Whether an A2 course exists is read from the
  content — with none published, the page says so and promises no date.
- **Evidence:** `CourseFinishTests` (8 tests: a middle lesson says nothing about finishing,
  the last one names it and counts it, the three next steps, a finished learner is told so,
  a later course is offered when one exists, a draft later course is not). In the browser:
  the panel, its three links, the «هنوز اینجا نیست» line and 44px targets at three widths.

### G — the "why" after an answer, and the keyboard
- **Commit:** `cd83daa`. **Files:** `exercises/static/exercises/js/exercise_runner.js`,
  `AGENTS.md`.
- **Explanation.** The verdict already revealed the question's explanation — for right
  answers as well as wrong ones — but the content barely existed: **157 of 3,504** questions
  carried one. Regenerating the word drills had deleted the explanations they used to have,
  because an explanation lives on the `Question` row that the rebuild deletes. Running the
  project's own `explain_a1_drills` afterwards took it to **3,173 of 3,504** (124 left blank:
  120 drills whose title the command does not recognise, 4 article questions). `AGENTS.md`
  now says the command has to be re-run after any `seed_a1_*_drills`.
- **Keyboard.** 1–9 pick the option with that number and Enter sends it. The listener is on
  `document`, not on the widget: the exercise sits in the middle of a lesson page, so the
  shortcuts have to work before the learner has clicked anything. A learner typing an answer
  keeps their digits, and another control holding the focus keeps its keys.
- **Evidence, in Chromium:** the page starts with the body focused; the served HTML never
  says which option is right; pressing 2 selects the second option and draws it selected;
  Enter makes the submit request (HTTP 200); the option whose text is correct is graded
  correct; its explanation is on the page; no wrong-answer correction appears for it. 10/10
  checks, appended to `VERIFY-LOG.txt`.

---

## PARTIAL

### P-19 — practice matches teaching (the first half done, the second deferred)
- **Commit:** `d87eb79`. **File:** `exercises/management/commands/seed_a1_word_drills.py`.
- **What was wrong:** every lesson asked about articles, the plural and the Perfekt. Lesson 1
  opened with a Perfekt question for a rule the course introduces in lesson 17 — and the
  914 grammar questions sat in 22 lessons, which is also what hid the fact that most lessons
  had *no* drill for the grammar they actually teach.
- **What changed:** a grammar drill is built only in a lesson that links the rule
  (`LessonGrammar`, the same link the lesson page renders its grammar block from). A revision
  lesson — one that introduces no new word (lesson 12) or whose own topics are called
  «Wiederholung: …» (lesson 24) — may also be drilled on anything the course taught before it,
  which is exactly what those lessons are for. The running set of taught rules is cleared
  when the course changes, so one course's teaching is never another's.
- **Numbers, mirror, after regenerating:**

  | | before | after |
  |---|---|---|
  | grammar exercises / questions | 111 / 914 | 13 / 116 |
  | lessons with a grammar-tagged question | 22 | **3** (lessons 4, 12, 19 — the ones that teach a drilled rule) |
  | meaning + writing drills (the words themselves) | 1,231 | 1,231 (unchanged) |
  | all generated word drills | 252 exercises / 2,145 questions | 154 / 1,347 |

- **Evidence:** `SeedA1WordDrillsTests` gained four tests (a lesson is drilled on the rules it
  teaches; a lesson that teaches no rule is asked about none while its words are still drilled
  both ways; a review lesson reviews what its own course already taught; a review lesson is not
  asked about a rule it has not reached, and another course's rules do not count). All 339
  `exercises` tests pass. In the browser, lesson 12's page offers
  «تمرین گرامر — آرتیکل وارون» and «تمرین گرامر — جمع وارون».
- **What is not done:** the audit's first half — *generate* drills for each lesson's own
  grammar topics (imperative, `nicht/kein`, separable verbs, the modal bracket, dative
  prepositions, the comparative, `seit + Dativ`). This is a content project, not a query: every
  German item has to be checked word by word against the course's own vocabulary and the
  official A1 list, and the owner's rule is that nothing uncertain is published. The design,
  the files it would touch and the accuracy constraint are written down in `DEFERRED.md`.
  **This is the biggest remaining learning gap and it is the reason Learning Experience stays
  below 9 in `RESCORE.md`.**

### P-17 — the lesson page's HTML weight
- **Commit:** `f8439e3`. **Files:** `templates/base.html`, `templates/includes/audio_control.html`,
  `static/css/components.css`.
- **What changed:** a lesson page carried one audio control per word, per sentence and per
  rule — **110** in-line copies of the same two 145-byte icon paths, ~16 KB. The shapes are now
  two `<symbol>`s in `base.html` and every control references them with `<use>`: no request, no
  JavaScript, and the CSS `stroke`/`fill` are inherited properties, so the icons paint exactly
  as before (verified in Chromium: the icon box is non-zero and the reference resolves).
- **Numbers, mirror:**

  | page | before | after | audit |
  |---|---|---|---|
  | `/lessons/1/` | 141,028 B | **138,220 B** | 144 KB |
  | `/lessons/12/` | 132,813 B | **130,191 B** | — |
  | `/lessons/24/` | 166,623 B | **163,381 B** | — |

- **Why it is only 2%:** the page ships the marked-up body of all eight steps at once, by
  design — the journey hides the inactive ones with a `.js` rule so that with JavaScript off
  every step is still readable. Measured breakdown of lesson 12 (123,908 characters): head and
  shell 9.8k, vocabulary step 37.8k, grammar step 27.3k, practice step 15.5k, reading 10.6k,
  examples 7.5k, finish 7.3k, explanation 5.7k, intro 2.1k.
- **The real fix, not done:** server-side step pagination (`?step=`), which is the audit's
  "paginate or lazy-render" and which changes the design the no-JavaScript path depends on. It
  would need `lessons/views.py`, `lessons/journey.py`, `lesson_detail.html`,
  `lesson_steps.js` and the journey tests rewritten together. Written up in `DEFERRED.md`.
- **Also worth recording:** the audit measured `/lessons/` at ~14 KB; measured now it is
  49,351 B, and this run did not touch that page beyond the Persian course description. I
  record the discrepancy rather than claim a regression I cannot attribute.

---

## The verification gates

### The test suite
- Baseline when this run started: **986 tests, OK (skipped=1)**, exit 0, 121.2 s.
- The final full run and its count are in `FIX-PLAN.md`'s closing note (see also
  `VERIFY-LOG.txt`); targeted runs during the work: `exercises` 335 → 339 OK, `lessons` 310 OK,
  `accounts` 94 OK, plus the 64-test audio/template/journey slice.

### The browser run (`VERIFY-LOG.txt`)
147 checks in Chromium (Playwright, `/usr/bin/chromium-browser`) against the project's own
`runserver` on the mirror with `DJANGO_DEBUG=False --insecure`, at **390×844, 820×1180 and
1440×900**:

- 11 real pages plus the 404 page: correct status, **no horizontal overflow**, **no console
  errors**, **nothing failing to load**;
- the last lesson's finish panel, its three links, its tap targets and its «no A2» line;
- lesson 12 offering its own grammar drills;
- the audio icon resolving through the sprite, and the audio button being 44px;
- `.brand__latin` at 12px; the lesson-list row at 44px; `/favicon.ico` at 200;
- `GET /exam/start/` not a blank page (and landing on `/exam/` when signed in);
  `GET /accounts/logout/` landing on the dashboard; a 405 navigation rendering the shell while
  a JSON client still gets the plain 405;
- the guest-progress offer: absent for a visitor, present for a signed-in learner, counting
  the lessons really there, a 44px accept button, fitting its column, importing on click,
  clearing the browser's copy, stopping asking, and the lesson appearing on the dashboard.

Second run, `10/10`: the 1–9/Enter shortcuts and the explanation after a correct answer.

### What could not be verified here
- **Images.** I cannot see images; every visual judgement above is a computed style, a
  bounding box or a status code.
- **Only Chromium.** No Safari or Firefox.
- **No screen reader, no axe, no Lighthouse.**
- **No microphone** (headless Chromium over plain HTTP), so the speaking page's recording
  itself is unexercised — see P-25.
- **No network**, so no CDN, TLS, real latency or production measurement; every timing above
  is a local `runserver` and is only meaningful relative to the other rows.
- **Audio correctness cannot be listened to**, so no claim is made about how any clip sounds.

---

## Dependencies

**None added.** No library, package or service was introduced by this run.

## Database

Every `manage.py` command ran against `language_learning_mirror`, checked before each write.
Content commands run on the mirror: `seed_a1_course --update`, `seed_a1_word_drills
--yes-replace-history`, `seed_a1_dictation_drills --yes-replace-history`, `explain_a1_drills`.
The two regenerations deleted the stored attempts that belonged to the drills they replaced —
**10 attempt rows from 1 learner** (the word drills) and the dictation drills' own history —
which the owner's instructions explicitly allow for generated content. Nothing authored was
touched: `ExerciseAttempt` rows on authored exercises are still there, and no lesson, word,
sentence or authored question was edited or deleted.
