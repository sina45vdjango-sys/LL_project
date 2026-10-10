"""Build the LISTENING exercises from sentences that already have audio.

Every sentence in the course already has a German MP3 (see ``generate_sentence_audio``).
The listening exercise type has been in the model from the start but had no content,
because no question carried an audio file — so a whole exercise type, and the runner's
audio block, were never exercised by real data.

This command fills that in without authoring anything new. It takes a few of a lesson's own
sentences and asks two questions about each one:

1. *what does it mean* — the options are Persian translations of whole sentences;
2. *which German sentence did you hear* — the options are German sentences, so the wrong
   ones are readable practice in their own right.

The audio is neither generated nor copied: the question points at the sentence's existing
file, so one MP3 serves the sentence link, the lesson block and the listening question.

**This command deletes and rebuilds.** What it created last time is removed first, so
running it twice does not double the content. The deletion is scoped to this command's own
exercise **title**, so it can never reach an authored exercise — and it is deliberately not
scoped by exercise *type* any more, because the pronunciation and dictation drills are
``LISTENING`` exercises too, and rebuilding by type silently deleted them.

Deleting an exercise cascades to its questions and answers, and an ``ExerciseAttempt``
points at both, so a learner's recorded attempts *on a generated listening exercise* go with
it. Attempts on authored exercises are untouched. Rebuilding is therefore refused while any
such attempt exists; ``--yes-replace-history`` allows it on purpose and says how much
history it is about to delete.

A lesson is skipped when it has fewer than three usable sentences, because the wrong options
would then be repeated correct answers rather than plausible ones.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from exercises.generated import LISTENING_DRILL_PREFIX
from exercises.models import Answer, Exercise, ExerciseAttempt, Question
from lessons.models import Lesson
from vocabulary.models import Sentence

#: Options per question, the correct one included. Four is what the live multiple-choice
#: and reading questions use.
OPTIONS = 4

#: How many of a lesson's sentences become questions. Each sentence produces two questions,
#: so the default gives six per lesson.
SENTENCES_PER_LESSON = 3

#: How many candidates to look through when picking the wrong options. Only the first few
#: are ever used; this just keeps the query small.
CANDIDATES = 60

MEANING_PROMPT = "به فایل گوش کن و معنی درست را انتخاب کن."
HEARD_PROMPT = "به فایل گوش کن. کدام جملهٔ آلمانی را شنیدی؟"
# The title every exercise it writes carries, and the marker of what it owns. Read from
# ``exercises/generated.py`` so the string cannot drift from the one the word drills use to
# tell generated questions from authored ones.
EXERCISE_TITLE = LISTENING_DRILL_PREFIX
EXERCISE_INSTRUCTION = "به هر فایل گوش کن و گزینهٔ درست را انتخاب کن."


class Command(BaseCommand):
    help = "Build LISTENING exercises from the sentences that already have audio."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
        parser.add_argument(
            "--sentences",
            type=int,
            default=SENTENCES_PER_LESSON,
            help="Sentences per lesson; each one becomes two questions.",
        )
        parser.add_argument(
            "--lesson",
            type=int,
            default=0,
            help="Only this lesson id. Zero means every published lesson.",
        )
        parser.add_argument(
            "--yes-replace-history",
            action="store_true",
            help="Also delete the stored attempts that belong to the listening exercises being replaced.",
        )

    def wrong_options(self, correct, candidates):
        """Three different wrong options for ``correct``, or ``None`` when there are not
        enough to make honest ones.

        A wrong option that repeats the correct answer, or another wrong option, would be
        nonsense; the caller drops the question instead of writing that.
        """
        wrong = []

        for text in candidates:
            if text == correct:
                continue
            if text in wrong:
                continue
            wrong.append(text)
            if len(wrong) == OPTIONS - 1:
                break

        if len(wrong) < OPTIONS - 1:
            return None
        return wrong

    def answer_rows(self, question, correct, wrong, correct_slot):
        """Write the options, with the right one in the slot the caller picked.

        The slot varies per sentence so the correct answer is not always in the same place;
        it still comes out of the data, so two runs on the same content agree.
        """
        wrong_index = 0

        for slot in range(1, OPTIONS + 1):
            if slot == correct_slot:
                Answer.objects.create(question=question, text=correct, is_correct=True, order=slot)
                continue

            Answer.objects.create(
                question=question, text=wrong[wrong_index], is_correct=False, order=slot
            )
            wrong_index += 1

    def lesson_plan(self, lesson, want_sentences, asked):
        """The questions this lesson should get, or an empty list when it cannot supply them.

        ``asked`` holds the sentences an earlier lesson already turned into a listening
        question in this run, and the picked sentence is added to it. A sentence taught in
        several lessons — every later lesson reuses the ones before it — would otherwise be
        asked again, word for word, in each of them; hearing it once is the practice, and the
        second listening is the same question twice.
        """
        links = (
            lesson.lesson_sentences.filter(sentence__is_published=True)
            .exclude(sentence__audio="")
            .exclude(sentence__audio__isnull=True)
            .select_related("sentence")
            .order_by("order", "pk")
        )

        picked = []
        for link in links:
            if link.sentence.pk in asked:
                continue
            picked.append(link.sentence)
            if len(picked) == want_sentences:
                break

        if len(picked) < SENTENCES_PER_LESSON:
            return []

        for sentence in picked:
            asked.add(sentence.pk)

        # Wrong options are drawn from the same level, ordered by id, so the same content
        # always produces the same exercise.
        level = lesson.course.language_level
        pool = list(
            Sentence.objects.filter(level=level, is_published=True)
            .exclude(pk__in=[sentence.pk for sentence in picked])
            .order_by("pk")[:CANDIDATES]
        )

        plan = []

        for sentence in picked:
            translations = []
            texts = []
            for other in pool:
                translations.append(other.translation_fa)
                texts.append(other.text)

            for kind in ["meaning", "heard"]:
                if kind == "meaning":
                    correct = sentence.translation_fa
                    candidates = translations
                    prompt = MEANING_PROMPT
                else:
                    correct = sentence.text
                    candidates = texts
                    prompt = HEARD_PROMPT

                wrong = self.wrong_options(correct, candidates)
                if wrong is None:
                    continue

                plan.append(
                    {
                        "prompt": prompt,
                        "audio": sentence.audio.name,
                        "correct": correct,
                        "wrong": wrong,
                        # Cycles 1-4, so the answer is not always in the first slot.
                        "slot": (sentence.pk % OPTIONS) + 1,
                    }
                )

        return plan

    def handle(self, *args, **options):
        if options["sentences"] < SENTENCES_PER_LESSON:
            raise CommandError(f"sentences must be at least {SENTENCES_PER_LESSON}")

        lessons = Lesson.objects.filter(is_published=True, course__is_published=True)
        if options["lesson"]:
            lessons = lessons.filter(pk=options["lesson"])
        lessons = lessons.select_related("course__language_level").order_by(
            "course__language_level__order", "order", "pk"
        )

        # Which sentences already have a listening question in this run, so a sentence
        # taught in more than one lesson is asked about only in the first of them.
        asked = set()

        planned = []
        for lesson in lessons:
            plan = self.lesson_plan(lesson, options["sentences"], asked)
            if plan:
                planned.append((lesson, plan))

        for lesson, plan in planned:
            self.stdout.write(f"lesson {lesson.pk}: {len(plan)} questions ({lesson.title})")

        if not planned:
            self.stdout.write("Nothing to build: no published lesson has enough sentences with audio.")
            return

        question_total = 0
        for lesson, plan in planned:
            question_total += len(plan)

        existing = Exercise.objects.filter(title=EXERCISE_TITLE).count()

        # An attempt points at both the exercise and the question, and the rebuild deletes
        # both, so these rows disappear with the exercises. Count them while they still exist.
        attempt_rows = ExerciseAttempt.objects.filter(exercise__title=EXERCISE_TITLE)
        attempt_total = attempt_rows.count()
        learner_total = attempt_rows.values("user").distinct().count()

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would replace {existing} listening exercise(s) with "
                f"{len(planned)} exercises / {question_total} questions."
            )
            if attempt_total:
                self.stdout.write(
                    f"Dry run: {attempt_total} stored attempt(s) from {learner_total} "
                    f"learner(s) belong to those exercises and would be deleted as well."
                )
            return

        # Rebuilding is safe while nobody has answered these questions. Once somebody has,
        # replacing them would quietly destroy learning history, so it needs the flag.
        if attempt_total and not options["yes_replace_history"]:
            self.stderr.write(
                self.style.WARNING(
                    f"{attempt_total} stored attempt(s) from {learner_total} learner(s) belong "
                    f"to the {existing} listening exercise(s) this command would replace."
                )
            )
            self.stderr.write(
                "Deleting those exercises also deletes those attempts, which are the history "
                "the review and progress features read."
            )
            raise CommandError(
                "Refusing to replace listening exercises that have learner attempts. "
                "Re-run with --yes-replace-history to delete that history too."
            )

        if attempt_total:
            self.stderr.write(
                self.style.WARNING(
                    f"--yes-replace-history: deleting {attempt_total} stored attempt(s) from "
                    f"{learner_total} learner(s) together with the listening exercises."
                )
            )

        # One transaction, so a failure half-way cannot leave the content deleted.
        with transaction.atomic():
            Exercise.objects.filter(title=EXERCISE_TITLE).delete()

            for lesson, plan in planned:
                last_order = Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"]
                if last_order is None:
                    last_order = 0

                exercise = Exercise.objects.create(
                    lesson=lesson,
                    title=EXERCISE_TITLE,
                    instruction=EXERCISE_INSTRUCTION,
                    type=Exercise.ExerciseType.LISTENING,
                    difficulty=Exercise.Difficulty.MEDIUM,
                    order=last_order + 1,
                    is_published=True,
                )

                # Question.order is numbered across the whole lesson in the existing data, so
                # this exercise continues from where the authored questions stop.
                last_question = Question.objects.filter(exercise__lesson=lesson).aggregate(Max("order"))
                order = last_question["order__max"]
                if order is None:
                    order = 0

                for row in plan:
                    order += 1
                    question = Question.objects.create(
                        exercise=exercise,
                        prompt=row["prompt"],
                        audio=row["audio"],
                        order=order,
                    )
                    self.answer_rows(question, row["correct"], row["wrong"], row["slot"])

        self.stdout.write(
            f"Built {len(planned)} listening exercise(s) with {question_total} questions, "
            f"replacing {existing}."
        )
