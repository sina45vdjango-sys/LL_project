"""Apply the mock exam's content set — the file — to the marked questions in the database.

``export_a1_exam_items`` chooses which questions the exam may ask; this command stores that
choice on ``Question.exam_section``, where ``exams/paper.py`` reads it. Two commands rather
than one because the file is the thing under version control: the selection is reviewable in
a diff, and applying it is a separate, repeatable step.

    python manage.py import_a1_exam_items           # apply the file
    python manage.py import_a1_exam_items --check   # compare, write nothing

How a row is matched
--------------------
By the orders, never by primary key, because a key means nothing after a rebuilt database:

* the lesson, by its ``order`` inside the level's course;
* the exercise, by its ``order`` inside that lesson;
* the question, by its ``order`` inside that exercise.

All three are already unique in the schema, which is what makes them a key rather than a
guess. An entry that does not resolve is an error, not a skip: a file that names content
which is not there is stale, and half-applying it would leave a section short without saying
so.

What is written
---------------
The set is the file and nothing else. Every question the file names is marked with its
section, and every other question's mark is cleared — so the exam is exactly the file, and
removing a line from the file really does remove the item. Rows are never deleted and no
learner data is touched.

The whole thing runs in one transaction: a failure half-way cannot leave the exam set half
applied.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.sections import Section
from exercises.models import Question
from lessons.models import Course, LanguageLevel

DEFAULT_DATA = "exams/data/a1_exam_items.json"


class Command(BaseCommand):
    help = "Apply the exam content set in the JSON file to Question.exam_section."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            default=DEFAULT_DATA,
            help=f"JSON file to read (default {DEFAULT_DATA}).",
        )
        parser.add_argument(
            "--level",
            default="A1",
            help="Language level code (default A1).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Compare the file with the database and write nothing.",
        )

    def load_payload(self, path):
        if not path.exists():
            raise CommandError(
                f"No such data file: {path}. "
                f"Run `python manage.py export_a1_exam_items` first."
            )

        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict) or "sections" not in payload:
            raise CommandError(f"{path} is not an exam export: it has no 'sections' key.")

        for section in payload["sections"]:
            if section not in Section.values:
                raise CommandError(
                    f"{path} names an unknown section {section!r}. "
                    f"Known sections: {', '.join(Section.values)}."
                )

        return payload

    def resolve(self, entry, course, label):
        """One written key back to its question, or an error naming what is missing."""
        lesson = course.lessons.filter(order=entry["lesson_order"]).first()
        if lesson is None:
            raise CommandError(
                f"{label}: no lesson with order {entry['lesson_order']} in this course."
            )

        exercise = lesson.exercises.filter(order=entry["exercise_order"]).first()
        if exercise is None:
            raise CommandError(
                f"{label}: no exercise with order {entry['exercise_order']} in lesson "
                f"{entry['lesson_order']}."
            )

        question = exercise.questions.filter(order=entry["question_order"]).first()
        if question is None:
            raise CommandError(
                f"{label}: no question with order {entry['question_order']} in exercise "
                f"{entry['exercise_order']}."
            )

        return question

    def wanted_marks(self, payload, course):
        """``{question pk: section}`` from the file, with every key resolved."""
        wanted = {}

        for section, entries in payload["sections"].items():
            for entry in entries:
                question = self.resolve(
                    entry, course, f"{section} lesson {entry['lesson_order']}"
                )

                if question.pk in wanted:
                    raise CommandError(
                        f"{payload.get('level', '?')}: question "
                        f"{entry['lesson_order']}/{entry['exercise_order']}/"
                        f"{entry['question_order']} is listed in both {wanted[question.pk]} "
                        f"and {section}. A question stands in for one section."
                    )

                wanted[question.pk] = section

        return wanted

    def handle(self, *args, **options):
        path = Path(options["data"])
        payload = self.load_payload(path)

        level = LanguageLevel.objects.filter(level=options["level"]).first()
        if level is None:
            raise CommandError(f"LanguageLevel {options['level']!r} does not exist.")

        course = Course.objects.filter(language_level=level).first()
        if course is None:
            raise CommandError(
                f"No course for {level.level!r}. Run `python manage.py seed_a1_course` first."
            )

        wanted = self.wanted_marks(payload, course)

        self.stdout.write(
            f"{path}: {len(wanted)} item(s) across {len(payload['sections'])} section(s)."
        )

        if options["check"]:
            report = self.compare(wanted, course)
            self.stdout.write(
                f"Check only: {report['marked']} already correct, "
                f"{report['missing']} to mark, {report['stale']} to clear, "
                f"{report['wrong']} marked as the wrong section."
            )
            return

        with transaction.atomic():
            results = self.apply(wanted, course)

        self.stdout.write(
            self.style.SUCCESS(
                f"Marked {results['marked']}, cleared {results['cleared']}, "
                f"re-pointed {results['repointed']}. {results['total']} exam items now."
            )
        )

    def compare(self, wanted, course):
        """What applying the file would change, counted but not written."""
        report = {"marked": 0, "missing": 0, "stale": 0, "wrong": 0}

        marked_now = {}
        for question in self.level_questions(course):
            if question.exam_section:
                marked_now[question.pk] = question.exam_section

        for question_id, section in marked_now.items():
            if question_id not in wanted:
                report["stale"] += 1
            elif wanted[question_id] != section:
                report["wrong"] += 1
            else:
                report["marked"] += 1

        for question_id in wanted:
            if question_id not in marked_now:
                report["missing"] += 1

        return report

    def level_questions(self, course):
        """Every question of this level's course, published or not.

        Not filtered to published rows: a mark left on a draft question is still a mark to
        clear, and clearing it here is what makes "the set is the file" true.
        """
        return Question.objects.filter(exercise__lesson__course=course)

    def apply(self, wanted, course):
        """Write the file's marks, and clear every mark that is not in it."""
        results = {"marked": 0, "cleared": 0, "repointed": 0, "total": len(wanted)}
        to_mark = []

        for question in self.level_questions(course):
            if question.pk not in wanted:
                if question.exam_section:
                    question.exam_section = ""
                    to_mark.append(question)
                    results["cleared"] += 1
                continue

            section = wanted[question.pk]
            if question.exam_section == section:
                continue

            if question.exam_section:
                results["repointed"] += 1
            else:
                results["marked"] += 1

            question.exam_section = section
            to_mark.append(question)

        if to_mark:
            Question.objects.bulk_update(to_mark, ["exam_section"])

        return results
