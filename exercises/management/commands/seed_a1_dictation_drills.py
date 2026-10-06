"""Turn the words the course already has recordings for into dictation questions.

The product asks a learner to write a German word from its Persian meaning — the word drills'
writing drill — but never from its **sound**. For a Persian speaker learning German that is
the missing half: ``ü``, ``ö`` and ``ä`` do not exist in Persian, ``ß`` is a letter they have
never written, ``ie`` and ``ei`` are the same two letters in a different order, and a doubled
consonant or a silent ``h`` changes the vowel without changing how the word looks. None of
that can be learned by reading; it is learned by hearing the word and writing it down.

The question is that whole exercise and nothing more:

    a word is played, and the learner types it.

No microphone and no speech recognition are involved — the learner **writes** what they
heard, so the verdict is the same typed-answer comparison the rest of the product already
uses (``exercises/grading.py``, which ignores case, repeats of whitespace and trailing
punctuation). That is what makes dictation the one ear-training exercise that fits a product
whose speaking slice was dropped: it trains spelling from sound, which needs no new
dependency and no model.

Five decisions are worth naming:

* **Audio plus exactly one answer row is the whole mechanism.** ``exercises/runner.py``
  shows options only when a question has more than one answer row, so a single row is what
  makes the page ask for typing — the same shape the authored «ترجمهٔ … به آلمانی؟» questions
  use. There is no new field, type or renderer.
* **The recording is the word's own file.** Nothing is generated or copied, exactly as
  ``seed_a1_exercises`` does with its sentences; a word with no recording is skipped rather
  than asked in silence (``media/`` is gitignored, so a fresh clone builds nothing until the
  audio commands have run).
* **The question carries a ``TESTED_ITEM`` target on the word it plays** — the opposite of
  the sound-pair drill, and for a reason: there the confusion is between *two* words, while
  here the learner heard exactly one word and spelled it, so a miss is a fact about that word
  and must move ``WordProgress`` to be reviewable. Generated drills therefore had to become
  distinguishable from authored ones (``exercises/generated.py``), or the word drills would
  read a dictation question as "this word was already asked what it means" and quietly drop
  its meaning drill.
* **One question per word per lesson, and the lesson it belongs to is the word's own.** A
  lesson that introduces no word is a review lesson, and it dictates the words it revisits —
  the same fallback the other generators make.
* **The same spelling is asked once per lesson.** ``sie`` and ``Sie`` are two rows that sound
  identical, and grading already ignores case, so dictating both would be one question
  written twice.

This command deletes and rebuilds. It removes only what carries its own title prefix
(``TITLE_PREFIX``), never an authored exercise and never another generator's drills.
Rebuilding is refused while a learner has attempts on those questions — deleting an exercise
cascades to the attempts that point at it — and ``--yes-replace-history`` allows it on purpose.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max, Q

from exercises.generated import DICTATION_DRILL_PREFIX
from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.models import Lesson, LessonWord

#: Questions per exercise. Smaller than the word drills' ten: every question is a recording
#: to listen to (usually twice) and a word to type, so a sitting is shorter.
BATCH = 6

#: Every exercise this command writes starts with this, and no authored exercise does. One
#: list, so the rebuild, the history gate and the report cannot disagree about what is ours.
TITLE_PREFIX = DICTATION_DRILL_PREFIX
TITLE_PREFIXES = [TITLE_PREFIX]

DICTATION_TITLE = "تمرین املا — شنیدن و نوشتن"

DICTATION_INSTRUCTION = "به هر واژه گوش کنید و آن را همان‌طور که شنیدید بنویسید."

DICTATION_PROMPT = "به فایل گوش کن و واژه‌ای را که شنیدی بنویس."

#: The most words one lesson dictates. The same cap, and the same reasoning, as
#: ``seed_a1_word_drills.MAX_DRILL_WORDS``: a lesson may **teach** more than this — lesson
#: 24's closing word bank is deliberately larger — but a lesson cannot ask a dictation for
#: every one of a hundred and fifty words. That was 25 exercises in a single lesson, which
#: the audit measured as the heaviest block in the course and the last thing between a
#: learner and the end of the lesson.
#:
#: The cap costs no content. The words beyond it stay on the lesson page, and every linked
#: word the learner has reached and never practised is offered by
#: ``vocabulary/schedule.py::new_words``, which is what puts them in the review queue. The
#: cap decides how much one lesson asks in a sitting, not which words exist.
MAX_DRILL_WORDS = 30


class Command(BaseCommand):
    help = "Build dictation drills that play a word and ask the learner to write it."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
        parser.add_argument(
            "--batch",
            type=int,
            default=BATCH,
            help="Questions per exercise. Only changes how the questions are split.",
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
            help="Also delete the stored attempts that belong to the drills being replaced.",
        )

    def owned_exercises(self):
        """Every exercise this command owns — everything under its own title prefix."""
        query = Q()

        for prefix in TITLE_PREFIXES:
            query = query | Q(title__startswith=prefix)

        return Exercise.objects.filter(query)

    def published_words(self, lesson):
        """The words this lesson should dictate, in the order the lesson lists them.

        The words it introduces (``role=NEW``). A lesson that introduces no word is a
        **review lesson** — lesson 12, «Wiederholung A1.1» — and it gets nothing here: its
        words were dictated when they were introduced, so a second dictation would be the
        same question twice. It still gets the turned-around word drills
        (``seed_a1_word_drills``), which ask the words a new way.

        Cut at ``MAX_DRILL_WORDS``, in the lesson's own teaching order, so the first words a
        lesson introduces are the ones it dictates.
        """
        # A review lesson introduces no word of its own, and the words it revisits already
        # have their dictation from the lesson that introduced them. Listening to the same
        # word a second time would be the same question twice, so a review lesson gets no
        # dictation at all — its review is the turned-around word drills, which ask
        # something new.
        if not lesson.lesson_words.filter(role=LessonWord.Role.NEW).exists():
            return []

        links = lesson.lesson_words.filter(
            role=LessonWord.Role.NEW, word__is_published=True
        )

        words = []
        for link in links.select_related("word").order_by("order", "pk"):
            words.append(link.word)

        return words[:MAX_DRILL_WORDS]

    def questions_for(self, lesson):
        """One question per word of this lesson that has a recording.

        The word is the answer, so it must have one: a question with no audio has nothing to
        dictate, and the learner could not tell anyone it was broken. Two rows that spell the
        same thing after case folding (``sie`` and ``Sie``) are one question, since grading
        ignores case and the second would be the first one asked twice.
        """
        questions = []
        asked = set()

        for word in self.published_words(lesson):
            if not word.audio:
                continue

            spelling = word.word.lower()
            if spelling in asked:
                continue
            asked.add(spelling)

            questions.append({"word": word})

        return questions

    def batches(self, questions, batch):
        """The questions split into exercises of ``batch`` questions each."""
        parts = []

        for start in range(0, len(questions), batch):
            parts.append(questions[start : start + batch])

        return parts

    def lesson_plan(self, lesson, batch):
        """The exercises this lesson should get, already split into batches.

        A lesson where no word has a recording returns an empty list rather than an empty
        exercise.
        """
        questions = self.questions_for(lesson)

        plan = []

        for number, part in enumerate(self.batches(questions, batch), start=1):
            plan.append({"title": f"{DICTATION_TITLE} ({number})", "questions": part})

        return plan

    def write_exercise(self, lesson, drill):
        """Write one exercise with its questions, their single answer and their audio.

        ``Question.order`` is numbered across the whole lesson in the existing data, so these
        continue from where the lesson's questions stop and each exercise of the lesson
        carries on from the one before it.
        """
        last_order = Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"]
        if last_order is None:
            last_order = 0

        exercise = Exercise.objects.create(
            lesson=lesson,
            title=drill["title"],
            instruction=DICTATION_INSTRUCTION,
            type=Exercise.ExerciseType.LISTENING,
            difficulty=Exercise.Difficulty.EASY,
            order=last_order + 1,
            is_published=True,
        )

        last_question = Question.objects.filter(exercise__lesson=lesson).aggregate(Max("order"))
        order = last_question["order__max"]
        if order is None:
            order = 0

        for row in drill["questions"]:
            order += 1
            question = Question.objects.create(
                exercise=exercise,
                prompt=DICTATION_PROMPT,
                order=order,
                # The recording the word already has, not a new one.
                audio=row["word"].audio.name,
            )

            # One answer row, and that is the point: more than one would make the runner
            # render options, and a dictation question is answered by typing. The bare word
            # is the accepted answer, exactly as the writing drill accepts it.
            Answer.objects.create(
                question=question, text=row["word"].word, is_correct=True, order=1
            )

            # What was played is what was tested: the learner heard this word and spelled it,
            # so a miss belongs to this word and moves its progress. (The sound-pair drill
            # carries no target: there the confusion is between two words.)
            QuestionTarget.objects.create(
                question=question,
                word=row["word"],
                role=QuestionTarget.Role.TESTED_ITEM,
            )

        return exercise

    def handle(self, *args, **options):
        if options["batch"] < 1:
            raise CommandError("batch must be at least 1")

        lessons = Lesson.objects.filter(is_published=True, course__is_published=True)
        if options["lesson"]:
            lessons = lessons.filter(pk=options["lesson"])
        lessons = lessons.select_related("course__language_level").order_by(
            "course__language_level__order", "order", "pk"
        )

        planned = []
        silent_words = 0
        for lesson in lessons:
            for word in self.published_words(lesson):
                if not word.audio:
                    silent_words += 1

            plan = self.lesson_plan(lesson, options["batch"])
            if plan:
                planned.append((lesson, plan))

        for lesson, plan in planned:
            question_total = 0
            for drill in plan:
                question_total += len(drill["questions"])
            self.stdout.write(
                f"lesson {lesson.pk}: {len(plan)} exercise(s) / {question_total} "
                f"questions ({lesson.title})"
            )

        if not planned:
            self.stdout.write(
                "Nothing to build: no published lesson has a word with a recording."
            )
            if silent_words:
                self.stdout.write(
                    f"({silent_words} word(s) have no recording, so they cannot be dictated. "
                    f"Run the audio commands first.)"
                )
            return

        exercise_total = 0
        question_total = 0
        words = set()

        for lesson, plan in planned:
            exercise_total += len(plan)
            for drill in plan:
                question_total += len(drill["questions"])
                for row in drill["questions"]:
                    words.add(row["word"].pk)

        existing = self.owned_exercises().count()

        # An attempt points at both the exercise and the question, and the rebuild deletes
        # both, so these rows disappear with the drills. Count them while they still exist.
        attempt_rows = ExerciseAttempt.objects.filter(exercise__in=self.owned_exercises())
        attempt_total = attempt_rows.count()
        learner_total = attempt_rows.values("user").distinct().count()

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would replace {existing} dictation drill(s) with "
                f"{exercise_total} exercises / {question_total} questions."
            )
            self.stdout.write(
                f"Dry run: {len(words)} word(s) dictated, over {len(planned)} lesson(s)."
            )
            if silent_words:
                self.stdout.write(
                    f"Dry run: {silent_words} word(s) have no recording and were left out."
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
                    f"to the {existing} dictation drill(s) this command would replace."
                )
            )
            self.stderr.write(
                "Deleting those exercises also deletes those attempts, which are the history "
                "the review and progress features read."
            )
            raise CommandError(
                "Refusing to replace dictation drills that have learner attempts. "
                "Re-run with --yes-replace-history to delete that history too."
            )

        if attempt_total:
            self.stderr.write(
                self.style.WARNING(
                    f"--yes-replace-history: deleting {attempt_total} stored attempt(s) from "
                    f"{learner_total} learner(s) together with the dictation drills."
                )
            )

        # One transaction, so a failure half-way cannot leave the content deleted.
        with transaction.atomic():
            self.owned_exercises().delete()

            for lesson, plan in planned:
                for drill in plan:
                    self.write_exercise(lesson, drill)

        self.stdout.write(
            f"Built {exercise_total} dictation drill(s) with {question_total} questions, "
            f"replacing {existing}."
        )
        self.stdout.write(
            f"Words dictated: {len(words)}, over {len(planned)} lesson(s)."
        )
        if silent_words:
            self.stdout.write(f"Words left out for having no recording: {silent_words}.")
