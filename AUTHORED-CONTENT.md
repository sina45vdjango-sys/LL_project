# AUTHORED-CONTENT.md — what this run wrote into the product, and where it lives

The owner's rule: **authored content lives in version-controlled data files with an
idempotent import command — never hand-edited only in the database.** Everything this run
wrote is listed here, with where it lives and how it gets into the database.

The most important fact about this run's authoring: **no new German text was written
anywhere.** Every German word, sentence and question a learner can meet was already in the
database and already validated by the earlier content phases; what this run authored is
*selection* (which existing questions form the exam) and *Persian prose* (course
description, page copy). That is why the content-accuracy checklist (article, plural,
irregular verbs, word order, accepted spellings, grading.py normalisation) had no new German
rows to be applied to — and why the one place selection could have gone wrong (the exam
drawing single-word dictation as "listening") is exactly what was fixed and locked by tests.

---

## 1. `exams/data/a1_exam_items.json` — the exam's content set

- **What it is:** the list of 135 existing questions that form the mock exam — 45 per
  section (`HOEREN`, `LESEN`, `SCHREIBEN`), i.e. three full papers, so two sittings never
  see the same 45 questions.
- **What it contains:** no German at all. Each entry is a natural key
  (`lesson_order`, `exercise_order`, `question_order`) pointing at a question row that
  already exists. Renumbering the database would break nothing (import re-resolves the keys
  and errors on an unknown one); importing is idempotent.
- **Commands:** `exams/management/commands/import_a1_exam_items.py` (file → DB) and
  `export_a1_exam_items.py` (DB → file). The field on the row is `Question.exam_section`
  (`exercises/migrations/0006_question_exam_section`), and `exams/paper.py` builds sections
  from marked rows only.
- **Selection rules, enforced by tests** (`ExamCurationTests`): a question without a
  verifiable answer is never marked; a scramble question is never marked; a dictation row is
  never marked SCHREIBEN; a marked row that is not in the file is cleared; the composition
  `section_of(p) == p.exam_section` holds for every marked row.
- **Why these 135:** hearing items are full sentences (the meaning question, not one-word
  dictation), reading items attach to multi-line passages, writing items prefer multi-word
  typed answers, and each section is spread round-robin over 23–24 lessons. The honest
  limits of the writing section are recorded in `REPORT.md`.

## 2. The A1 course's Persian description

- **Where:** `lessons/management/commands/seed_a1_course.py`, the `COURSES["A1"]` entry
  (`description_fa`, alongside the pre-existing English `description`).
- **What it says:** where the course starts, how far it goes (A1.1 = lessons 1–12,
  A1.2 = lessons 13–24), and that the material is original and CEFR A1-aligned. No promise
  of a result, no guarantee, no date.
- **How it gets in:** `seed_a1_course --update` (idempotent, writes only this field's
  content; `--check`/`--dry-run` verify without writing). The learner pages show it through
  `Course.display_description`.
- **Persian rules:** written with ی/ک (never ي/ك) and standard spacing; reviewed against the
  project's own Persian copy conventions.

## 3. Persian interface copy in templates (version-controlled, no database)

These are product copy, not course content, listed for completeness:

| Copy | File |
|---|---|
| The front door: what this is, who it is for, what is inside it, one CTA | `templates/includes/front_door.html` |
| The 403 and 405 pages | `templates/403.html`, `templates/405.html` |
| The finish panel: «A1 کامل شد», the three real next steps, the honest no-A2 line | `lessons/templates/lessons/steps/_finish.html` |
| The guest-progress offer and its accept/decline wording | `templates/dashboard.html` |
| The exam page's one corrected explanatory sentence | `exams/templates/exams/exam_index.html` |

Every number these pages show (1,018 واژه / 745 تمرین / 24 درس / «۲۴ درس از ۲۴») is
counted from the database in the view — none is written in the copy.

## 4. What this run did **not** author

- No German exercise, question, sentence, word or lesson was written or edited — existing
  rows were only referenced.
- No grammar-drill content was generated (that half of P-19 is deferred precisely because it
  would require authoring checked German; see `DEFERRED.md`).
- Pre-existing authored content (the A1 lessons, words, sentences, authored exercises,
  pronunciation pairs) lives where earlier phases put it and is not relisted here.
