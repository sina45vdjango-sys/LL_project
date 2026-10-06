"""Choose the mock exam's content set, and write it down as a file.

The exam used to be *derived*: ``exams/paper.py`` classified every published question in
Python and took whatever fitted each skill. Two problems came out of that, and both are what
this command fixes.

* **The exam moved by itself.** A new generator changed the paper without anyone deciding
  to. The audit found a reading generator supplying a third of LESEN, and 13 of 15 HÖREN
  items being single-word dictation rather than a sentence to understand.
* **It cost ~600 ms of CPU on a public page**, because the exam index asked for the
  classification on every request.

So the exam set is now chosen here, written to ``exams/data/a1_exam_items.json``, committed,
and applied by ``import_a1_exam_items``. The paper can only move when this file changes, and
the change is visible in a diff.

    python manage.py export_a1_exam_items            # write the file
    python manage.py export_a1_exam_items --report   # say what is in it
    python manage.py import_a1_exam_items            # apply it to the database

What may be an exam item, section by section
--------------------------------------------
Each section is drawn from the course's own questions that already have the *shape* the
section needs — not from the whole practice table. The titles come from
``exercises/generated.py``, so a renamed generator family breaks this command loudly
instead of silently emptying a section.

* **HÖREN** — ``شنیدن: جملههای این درس``: a whole sentence is played and the learner picks
  what it means, or which German sentence it was. This is the nearest thing the course has
  to a task where you listen for meaning.
* **LESEN** — ``تمرین خواندن``: four lines of German on screen and a question about which
  line carries a given meaning. A short text to read, not a single word.
* **SCHREIBEN** — the typed questions with no recording: the learner writes German rather
  than picking an option. Answers of more than one word are preferred, because a paper of
  fifteen single words measures spelling and little else; that is a real limitation of the
  current content and it is recorded in the report rather than papered over.

Every candidate must be *markable* (it has an authored correct answer) and must not be a
``SCRAMBLE``: a scramble on the exam page would be a translation with the word bank missing.
Nothing unanswerable is ever marked, because that would be a hole in the score that looks
like a mistake the learner made.

How the fifteen are spread
--------------------------
Round-robin across the lessons, in teaching order: the first item from each lesson, then the
second from each, and so on. A 45-question paper therefore covers most of the course rather
than the first three lessons, and the choice is reproducible — no randomness, so re-running
this command produces the same file byte for byte.

Why more is marked than one paper asks
--------------------------------------
The paper asks 15 questions per section; this marks ``MARKED_PER_SECTION`` — three sittings'
worth. Marking exactly 15 would make every sitting ask the identical 45 questions in a
different order, which is not a mock exam a learner can take twice.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from exams.paper import is_typed, markable, section_of
from exams.sections import Section
from exams.spec import SECTION_ORDER
from exercises.generated import LISTENING_DRILL_PREFIX, READING_DRILL_PREFIX
from exercises.models import Exercise, Question
from lessons.models import Course, LanguageLevel

DEFAULT_OUTPUT = "exams/data/a1_exam_items.json"

#: How many questions to mark per section. The paper asks ``ITEMS_PER_SECTION`` (15), so
#: this is three sittings' worth: a learner who sits the mock twice gets a mostly different
#: paper, which is the point of a mock they can take again.
MARKED_PER_SECTION = 45


class Command(BaseCommand):
    help = "Choose the mock exam's content set and write it to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=DEFAULT_OUTPUT,
            help=f"File to write (default {DEFAULT_OUTPUT}).",
        )
        parser.add_argument(
            "--level",
            default="A1",
            help="Language level code (default A1).",
        )
        parser.add_argument(
            "--items",
            type=int,
            default=MARKED_PER_SECTION,
            help=f"Items to mark per section (default {MARKED_PER_SECTION}).",
        )
        parser.add_argument(
            "--report",
            action="store_true",
            help="Print what each section will contain after writing.",
        )

    def published_questions(self, level):
        """Every question of this level's published course, in teaching order.

        ``answers`` is prefetched because the two shape rules below read them for every
        question; on the live content that is the difference between one query and two
        thousand.
        """
        return (
            Question.objects.filter(
                exercise__is_published=True,
                exercise__lesson__is_published=True,
                exercise__lesson__course__is_published=True,
                exercise__lesson__course__language_level=level,
            )
            .select_related("exercise", "exercise__lesson")
            .prefetch_related("answers", "targets")
            .order_by("exercise__lesson__order", "exercise__order", "order", "pk")
        )

    def candidates(self, section, questions):
        """The published questions this section may be marked from, in teaching order.

        One question per section: the shapes do not overlap in practice (a listening item
        has a recording and a single-word dictation also has one, so the section rules
        below never both claim the same question — HÖREN takes what the listening generator
        wrote by title, SCHREIBEN refuses anything with a recording).
        """
        chosen = []

        for question in questions:
            title = question.exercise.title

            if section == Section.HOEREN:
                if title.startswith(LISTENING_DRILL_PREFIX) and markable(question):
                    chosen.append(question)
                continue

            if section == Section.LESEN:
                if title.startswith(READING_DRILL_PREFIX) and markable(question):
                    chosen.append(question)
                continue

            # SCHREIBEN: written German, and not something another section already owns.
            if question.exercise.type == Exercise.ExerciseType.SCRAMBLE:
                continue
            if question.audio:
                continue
            if title.startswith(LISTENING_DRILL_PREFIX):
                continue
            if title.startswith(READING_DRILL_PREFIX):
                continue
            if not markable(question) or not is_typed(question):
                continue

            chosen.append(question)

        return chosen

    def pick(self, questions, wanted):
        """``wanted`` questions spread across as many lessons as the set allows.

        Round-robin over the lessons in teaching order: one from each lesson, then a second
        from each, until the section is full. Deterministic, so the file this writes is the
        same file every time it is run over the same content.
        """
        by_lesson = {}

        for question in questions:
            lesson_id = question.exercise.lesson_id
            if lesson_id not in by_lesson:
                by_lesson[lesson_id] = []
            by_lesson[lesson_id].append(question)

        chosen = []
        depth = 0

        while len(chosen) < wanted:
            added = 0

            for lesson_id in by_lesson:
                group = by_lesson[lesson_id]
                if depth < len(group):
                    chosen.append(group[depth])
                    added += 1
                    if len(chosen) == wanted:
                        break

            if added == 0:
                break

            depth += 1

        return chosen

    def multi_word_first(self, section, questions):
        """For SCHREIBEN, put the longer answers in front of the single words.

        The preference is applied inside each lesson's own run of candidates, so it changes
        *which* writing item a lesson contributes without changing how the lessons are
        spread. Nothing is filtered out: a lesson with only single words still contributes.
        """
        if section != Section.SCHREIBEN:
            return questions

        longer = []
        single = []

        for question in questions:
            answer = question.answers.all()[0]
            if " " in answer.text.strip():
                longer.append(question)
            else:
                single.append(question)

        return longer + single

    def entry_for(self, question):
        """This question's natural key: the orders, never a primary key.

        The same three orders the database already makes unique — lesson order inside the
        course, exercise order inside the lesson, question order inside the exercise — so
        the file still resolves after a database is rebuilt from scratch.
        """
        return {
            "lesson_order": question.exercise.lesson.order,
            "exercise_order": question.exercise.order,
            "question_order": question.order,
        }

    def handle(self, *args, **options):
        level = LanguageLevel.objects.filter(level=options["level"]).first()
        if level is None:
            raise CommandError(f"LanguageLevel {options['level']!r} does not exist.")

        course = Course.objects.filter(language_level=level).first()
        if course is None:
            raise CommandError(
                f"No course for {level.level!r}. Run `python manage.py seed_a1_course` first."
            )

        questions = list(self.published_questions(level))
        wanted = options["items"]

        sections = {}
        counts = {}

        for section in SECTION_ORDER:
            pool = self.candidates(section, questions)
            pool = self.multi_word_first(section, pool)
            chosen = self.pick(pool, wanted)

            sections[section] = [self.entry_for(question) for question in chosen]
            counts[section] = {"available": len(pool), "chosen": len(chosen)}

            if len(chosen) < wanted:
                self.stderr.write(
                    f"  ! {section}: only {len(chosen)} of {wanted} items could be chosen."
                )

        payload = {
            "level": level.level,
            "items_per_section": wanted,
            "sections": sections,
        }

        path = Path(options["output"])
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        self.stdout.write(self.style.SUCCESS(f"Wrote {path}."))

        for section in SECTION_ORDER:
            facts = counts[section]
            self.stdout.write(
                f"  {section}: {facts['chosen']} of a possible {facts['available']} "
                f"({facts['available'] - facts['chosen']} left unchosen)"
            )

        if options["report"]:
            self.stdout.write("")
            self.stdout.write("What each section will ask:")
            for section in SECTION_ORDER:
                self.stdout.write(f"  {section}")
                for entry in sections[section]:
                    question = self.lookup(entry, course)
                    self.stdout.write(
                        f"    درس {entry['lesson_order']} · {question.exercise.title} "
                        f"· پرسش {entry['question_order']}"
                    )

    def lookup(self, entry, course):
        """Resolve one written key back to its question, for the report."""
        lesson = course.lessons.filter(order=entry["lesson_order"]).first()
        if lesson is None:
            raise CommandError(f"No lesson with order {entry['lesson_order']}.")

        exercise = lesson.exercises.filter(order=entry["exercise_order"]).first()
        if exercise is None:
            raise CommandError(
                f"No exercise with order {entry['exercise_order']} in lesson "
                f"{entry['lesson_order']}."
            )

        question = exercise.questions.filter(order=entry["question_order"]).first()
        if question is None:
            raise CommandError(
                f"No question with order {entry['question_order']} in exercise "
                f"{entry['exercise_order']}."
            )

        # The key is the same one the paper needs, so a key that resolves to a question
        # whose own section disagrees is a mistake in the file, not a lookup to paper over.
        section = section_of(question)
        if section is None:
            self.stderr.write(
                f"  ! درس {entry['lesson_order']} · {exercise.title} · "
                f"پرسش {entry['question_order']} stands in for no section"
            )

        return question
