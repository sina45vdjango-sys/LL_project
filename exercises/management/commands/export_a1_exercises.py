"""Export the A1 exercises -- with their questions, answers and targets -- to JSON.

The 111 authored exercises are the only part of this project's content that lives
**only** in the database. The words can be rebuilt from ``vocabulary/data/*.json`` and
the lessons from ``lessons/data/*.py``, but nothing can rebuild an exercise. This
command writes them out, so there is something to restore from and something to review
and diff like the rest of the content.

It changes nothing in the database: it runs SELECT queries and writes one JSON file.

The **generated** exercises are left out. The listening, dictation, pronunciation,
reading and word drills are rebuilt from their own seed command every time, so they are
not authored content and do not belong in a file whose job is to restore what no command
can rebuild. Writing them here was how the listening exercise ended up in the file *and*
in the generator at once — two owners of one exercise, and two identical rows in every
lesson. ``generated_exercises()`` is the list of what to leave out, read from the same
place the seed commands read it, so a new generator is excluded automatically.

Why references are stored as text
---------------------------------
Every reference is written as text instead of a database id, because a primary key
means nothing once the row is gone:

* a **word** is written as ``Wort::TYPE`` (for example ``Bank::NOUN``). That is the
  ``::`` form ``seed_a1_course`` already understands. The type is always included, so
  a word that exists as both a noun and a verb can never be restored as the wrong one.
* a **grammar** topic is written as its title, which is unique.
* a **sentence** is written as its German text.

Answer text and the audio/image paths are copied exactly as they are.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from exercises.generated import generated_exercises
from exercises.models import Exercise
from lessons.models import LanguageLevel

DEFAULT_OUTPUT = "exercises/data/a1_exercises.json"


class Command(BaseCommand):
    help = "Write the A1 exercises, questions, answers and targets to a JSON file. Read-only."

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

    def handle(self, *args, **options):
        code = options["level"]
        level = LanguageLevel.objects.filter(level=code).first()
        if level is None:
            raise CommandError(f"LanguageLevel {code!r} does not exist.")

        exercises = (
            Exercise.objects.filter(lesson__course__language_level=level)
            .exclude(pk__in=generated_exercises())
            .select_related("lesson")
            .order_by("lesson__order", "order", "pk")
        )

        entries = []
        question_total = 0
        answer_total = 0
        target_total = 0
        questions_without_target = 0
        questions_without_answer = 0
        type_counts = {}

        for exercise in exercises:
            if exercise.type in type_counts:
                type_counts[exercise.type] += 1
            else:
                type_counts[exercise.type] = 1

            questions = []

            for question in exercise.questions.order_by("order", "pk"):
                question_total += 1

                answers = []
                for answer in question.answers.order_by("order", "pk"):
                    answers.append(
                        {
                            "order": answer.order,
                            "text": answer.text,
                            "is_correct": answer.is_correct,
                            "match_type": answer.match_type,
                        }
                    )
                    answer_total += 1

                targets = []
                for target in question.targets.select_related(
                    "word", "grammar", "sentence"
                ).order_by("role", "pk"):
                    if target.word:
                        kind = "word"
                        ref = target.word.word + "::" + target.word.word_type
                    elif target.grammar:
                        kind = "grammar"
                        ref = target.grammar.title
                    else:
                        kind = "sentence"
                        ref = target.sentence.text

                    targets.append({"role": target.role, "kind": kind, "ref": ref})
                    target_total += 1

                if not targets:
                    questions_without_target += 1
                if not answers:
                    questions_without_answer += 1

                audio = ""
                if question.audio:
                    audio = question.audio.name

                image = ""
                if question.image:
                    image = question.image.name

                questions.append(
                    {
                        "order": question.order,
                        "prompt": question.prompt,
                        "explanation": question.explanation,
                        "audio": audio,
                        "image": image,
                        "targets": targets,
                        "answers": answers,
                    }
                )

            entries.append(
                {
                    "lesson_order": exercise.lesson.order,
                    "lesson_title": exercise.lesson.title,
                    "title": exercise.title,
                    "instruction": exercise.instruction,
                    "type": exercise.type,
                    "difficulty": exercise.difficulty,
                    "order": exercise.order,
                    "is_published": exercise.is_published,
                    "questions": questions,
                }
            )

        if not entries:
            raise CommandError(f"No exercises found for level {code!r}.")

        payload = {
            "level": code,
            "topic": f"{code} exercises exported from the database",
            "exercises": entries,
        }

        path = Path(options["output"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        self.stdout.write(self.style.SUCCESS(f"Wrote {path}"))
        self.stdout.write(f"  exercises            {len(entries)}")
        self.stdout.write(f"  questions            {question_total}")
        self.stdout.write(f"  answers              {answer_total}")
        self.stdout.write(f"  targets              {target_total}")
        self.stdout.write(f"  questions w/o target {questions_without_target}")
        self.stdout.write(f"  questions w/o answer {questions_without_answer}")

        self.stdout.write("  by type:")
        for type_name in sorted(type_counts):
            self.stdout.write(f"    {type_name:16} {type_counts[type_name]}")
