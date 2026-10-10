"""Report how much each lesson asks of a learner, and flag the ones that ask too much.

Nothing in the course showed this. A lesson's size was visible only as "this page is long",
and the one lesson that had grown to 148 new words and 576 questions was found by reading the
database by hand. This command prints the numbers per lesson, so the next lesson that grows
past the drill cap is visible **before** a learner meets it.

What it reports per lesson:

* ``new`` — the words the lesson introduces (``LessonWord`` with ``role=NEW``)
* ``review`` — the words it revisits
* ``drilled`` — how many of those the word drills will actually ask about, capped at
  ``MAX_DRILL_WORDS`` (the cap lives in ``seed_a1_word_drills``, and this command reads it
  from there rather than keeping a second copy of the number)
* ``exercises`` / ``questions`` — the practice a learner is handed

A lesson is flagged when its battery is at the cap while it teaches more than the cap: the
words past the cap are still on the lesson page and still reach the learner through the review
queue, which is the point of the cap, but the flag is the reminder that a lesson that teaches
sixty words is a lesson worth splitting rather than capping.

**This command only reads.** It writes nothing, needs no flag, and always exits zero — it is a
report, not a gate. The gate is the test in ``exercises/tests.py``, which fails if a lesson's
drilled words ever exceed the cap.
"""

from django.core.management.base import BaseCommand

from exercises.management.commands.seed_a1_word_drills import MAX_DRILL_WORDS
from exercises.models import Exercise, Question
from lessons.models import Lesson, LessonWord


class Command(BaseCommand):
    help = "Report the per-lesson word and question load. Read-only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Also list the lessons that are within the cap.",
        )

    def handle(self, *args, **options):
        lessons = (
            Lesson.objects.filter(is_published=True, course__is_published=True)
            .select_related("course__language_level")
            .order_by("course__language_level__order", "order", "pk")
        )

        headers = ("lesson", "new", "review", "drilled", "exercises", "questions", "title")
        self.stdout.write(
            f"{headers[0]:>6} {headers[1]:>4} {headers[2]:>6} {headers[3]:>7} "
            f"{headers[4]:>9} {headers[5]:>9}  {headers[6]}"
        )

        flagged = 0

        for lesson in lessons:
            new = LessonWord.objects.filter(lesson=lesson, role=LessonWord.Role.NEW).count()
            review = LessonWord.objects.filter(lesson=lesson, role=LessonWord.Role.REVIEW).count()

            # The same selection ``seed_a1_word_drills.published_words`` makes: the words the
            # lesson introduces, or the ones it revisits when it introduces none, cut at the
            # cap. Kept in two short lines here rather than shared, because the rule is two
            # lines and a second caller is not a reason for a module.
            if new:
                drilled = new
            else:
                drilled = review
            if drilled > MAX_DRILL_WORDS:
                drilled = MAX_DRILL_WORDS

            exercises = Exercise.objects.filter(lesson=lesson, is_published=True)
            questions = Question.objects.filter(exercise__in=exercises).count()

            over = new > MAX_DRILL_WORDS
            if over:
                flagged += 1

            if not over and not options["all"]:
                continue

            mark = "  <-- teaches more than the cap" if over else ""
            self.stdout.write(
                f"{lesson.order:>6} {new:>4} {review:>6} {drilled:>7} "
                f"{exercises.count():>9} {questions:>9}  {lesson.title[:40]}{mark}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"Drill cap: {MAX_DRILL_WORDS} words per lesson. "
            f"{flagged} lesson(s) teach more than the cap."
        )
        self.stdout.write(
            "Words past the cap stay on the lesson page and still reach the learner through "
            "the review queue (vocabulary/schedule.py::new_words)."
        )
