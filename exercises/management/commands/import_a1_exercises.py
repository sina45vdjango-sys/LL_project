"""Import the A1 exercises from the file written by ``export_a1_exercises``.

The 111 authored exercises used to live in one database and nowhere else, so there was
nothing to restore them from. ``export_a1_exercises`` writes them out; this command reads
them back and rebuilds the rows.

    python manage.py export_a1_exercises      # write the file
    python manage.py import_a1_exercises      # read it back
    python manage.py import_a1_exercises --data somewhere/else.json

How a row is matched
--------------------
Nothing here goes by primary key, because a key means nothing after a restore. Each row
is matched on the same natural key the database itself enforces:

* ``Exercise``  on ``(lesson, order)`` — the file carries ``lesson_order`` and ``order``
* ``Question``  on ``(exercise, order)``
* ``Answer``    on ``(question, order)``

Every other field is written from the file, so running the import twice corrects the
rows instead of doubling them. That is the same rule ``import_a1_words`` follows.

What is never deleted
---------------------
Answers are matched and updated, never deleted and rebuilt: an ``ExerciseAttempt`` points
at an ``Answer``, so removing one would destroy a learner's stored history. For the same
reason this command never deletes an exercise or a question.

``QuestionTarget`` rows are different. Nothing points at them, they carry no learner
data, so they are rebuilt from the file on every run. That is also the only tidy way to
store several ``CONTEXT`` targets on one question, since only ``TESTED_ITEM`` is unique
per question.

Audio is not generated here. The file stores the path a row already had. The files
themselves live in ``/media/``, which is not in version control, so regenerate them with
``generate_sentence_audio`` and the other audio commands.

What this command refuses
-------------------------
A file that contains a **generated** exercise is rejected outright. Listening, dictation,
pronunciation, reading and word drills are rebuilt by their own seed command, and a file
that also carried them is what created a second, identical copy of the listening exercise
in every lesson. The check is a refusal rather than a silent skip so a stale file is fixed
instead of quietly half-imported.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exercises.generated import TITLE_PREFIXES
from exercises.models import Answer, Exercise, Question, QuestionTarget
from lessons.models import Course, LanguageLevel
from vocabulary.models import Grammar, Sentence, Word

DEFAULT_DATA = "exercises/data/a1_exercises.json"


class Command(BaseCommand):
    help = "Import the A1 exercises from the JSON file written by export_a1_exercises."

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

    # ------------------------------------------------------------------ helpers

    def get_level(self, code):
        level = LanguageLevel.objects.filter(level=code).first()
        if level is None:
            raise CommandError(f"LanguageLevel {code!r} does not exist.")
        return level

    def load_payload(self, path):
        if not path.exists():
            raise CommandError(
                f"No such data file: {path}. "
                f"Run `python manage.py export_a1_exercises` first."
            )

        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict) or "exercises" not in payload:
            raise CommandError(f"{path} is not an exercise export: it has no 'exercises' key.")

        return payload

    def lesson_lookup(self, level):
        """``lesson order -> Lesson`` for this level's course.

        The file names a lesson by its order number, which is unique inside a course
        (``unique_lesson_order_per_course``). The id is never used, so the file survives
        a rebuilt database.
        """
        course = Course.objects.filter(language_level=level).first()
        if course is None:
            raise CommandError(
                f"No course for {level.level!r}. Run `python manage.py seed_a1_course` first."
            )

        lessons = {}
        for lesson in course.lessons.order_by("order"):
            lessons[lesson.order] = lesson
        return lessons

    def write_targets(self, question, targets, level, label):
        """Replace this question's targets from the file, and return how many were written."""
        question.targets.all().delete()

        written = 0

        for target in targets:
            kind = target["kind"]
            ref = target["ref"]
            role = target["role"]

            if kind == "word":
                text, _, type_name = ref.partition("::")
                row = Word.objects.filter(level=level, word=text, word_type=type_name).first()
                if row is None:
                    self.stderr.write(f"  ! {label}: no word matches {ref!r}")
                    continue
                QuestionTarget.objects.create(question=question, word=row, role=role)

            elif kind == "grammar":
                row = Grammar.objects.filter(level=level, title=ref).first()
                if row is None:
                    self.stderr.write(f"  ! {label}: no grammar topic matches {ref!r}")
                    continue
                QuestionTarget.objects.create(question=question, grammar=row, role=role)

            else:
                row = Sentence.objects.filter(level=level, text=ref).first()
                if row is None:
                    self.stderr.write(f"  ! {label}: no sentence matches {ref!r}")
                    continue
                QuestionTarget.objects.create(question=question, sentence=row, role=role)

            written += 1

        return written

    # ------------------------------------------------------------------- import

    def import_exercises(self, entries, level, lessons):
        created = 0
        updated = 0
        question_total = 0
        answer_total = 0
        target_total = 0

        for entry in entries:
            lesson = lessons.get(entry["lesson_order"])
            if lesson is None:
                raise CommandError(
                    f"No lesson with order {entry['lesson_order']} in level {level.level} "
                    f"(file lists exercise {entry['order']}, {entry['title']!r})."
                )

            exercise, was_created = Exercise.objects.update_or_create(
                lesson=lesson,
                order=entry["order"],
                defaults={
                    "title": entry["title"],
                    "instruction": entry["instruction"],
                    "type": entry["type"],
                    "difficulty": entry["difficulty"],
                    "is_published": entry["is_published"],
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            for row in entry["questions"]:
                question, _ = Question.objects.update_or_create(
                    exercise=exercise,
                    order=row["order"],
                    defaults={
                        "prompt": row["prompt"],
                        "explanation": row["explanation"],
                        "audio": row["audio"] or "",
                        "image": row["image"] or "",
                    },
                )
                question_total += 1

                for answer in row["answers"]:
                    Answer.objects.update_or_create(
                        question=question,
                        order=answer["order"],
                        defaults={
                            "text": answer["text"],
                            "is_correct": answer["is_correct"],
                            "match_type": answer["match_type"],
                        },
                    )
                    answer_total += 1

                label = (
                    f"lesson {entry['lesson_order']} exercise {entry['order']} "
                    f"question {row['order']}"
                )
                target_total += self.write_targets(question, row["targets"], level, label)

        return created, updated, question_total, answer_total, target_total

    # ------------------------------------------------------------------- handle

    def handle(self, *args, **options):
        path = Path(options["data"])
        payload = self.load_payload(path)

        entries = payload["exercises"]
        if not entries:
            raise CommandError(f"{path} contains no exercises.")

        for entry in entries:
            for prefix in TITLE_PREFIXES:
                if entry["title"].startswith(prefix):
                    raise CommandError(
                        f"{path} contains a generated exercise ({entry['title']!r}). "
                        f"Generated exercises are rebuilt by their own seed command, not "
                        f"restored from this file. Run export_a1_exercises to write a "
                        f"clean file."
                    )

        level = self.get_level(options["level"])
        lessons = self.lesson_lookup(level)

        self.stdout.write(f"Loading {len(entries)} exercise(s) from {path} for level {level.level}.")

        # One transaction, so a failure half-way cannot leave the content half imported.
        with transaction.atomic():
            created, updated, questions, answers, targets = self.import_exercises(
                entries, level, lessons
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exercises: {created} created, {updated} updated. "
                f"{questions} questions, {answers} answers, {targets} targets."
            )
        )
