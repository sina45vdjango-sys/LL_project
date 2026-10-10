"""Turn the sound contrasts the course already contains into listening questions.

The product could ask whether a learner knows a word, its article, its plural, and how to
write it — but never whether they can *hear* it. That is the gap this command fills, and
for German it is the one that matters most: ü and ö do not exist in Persian, short and
long vowels are not written the way they sound, and ``-en`` against ``-er`` decides the
end of a word. A learner who cannot hear a contrast cannot produce it either, which is
exactly why this exists in a product whose speaking slice was dropped: **hearing needs no
microphone and no speech recognition, so it needs no new dependency.**

The question is the smallest one that trains that skill:

    you hear one word, and you pick which of two similar words it was.

Two options, not four. The wrong one is not a random word of the lesson but the word that
differs from the right answer by a single sound (``schon`` against ``schön``), so the
choice is a discrimination rather than a guess, and the prompt names the difference in
Persian so the learner knows what to listen for. The contrast rules live in
``exercises/data/pronunciation_pairs.py``, together with the reason they are rules instead
of a hand-written pair list.

Three decisions are worth naming:

* **The audio is neither generated nor copied.** It is the recording the word already has,
  pointed at by ``Question.audio`` — the same thing ``seed_a1_exercises`` does with its
  sentences. A word with no recording is skipped rather than asked in silence, which is why
  a fresh clone (``media/`` is gitignored) builds nothing until the audio commands have run.
* **The question carries no ``QuestionTarget`` at all.** A learner who confuses ``schön``
  with ``schon`` has told us they cannot hear the difference between *two* words; naming
  either as the word they got wrong would move ``WordProgress`` on a question that never
  asked about its meaning. It would also make ``seed_a1_word_drills`` see the word as
  already asked and skip its meaning drill, so the two commands would silently compete over
  the same words. The mistake stays visible in the attempt history and in exercise accuracy.
* **Nothing here asks what a word means.** A four-option meaning question needs three
  honest distractors; a two-option listening question needs one word that really sounds
  like the answer, and that is the whole content of the question.

Pairs are drawn from **the whole level**, not from the lesson: a contrast partner is often
taught in another lesson, and what makes a minimal pair is the sound rather than the
chapter. The question itself belongs to the lesson that teaches the word being played, so
the drill appears where the learner meets the word — and in a review lesson, where they
meet it again.

The drills being replaced do not count as content of their own: everything under
``TITLE_PREFIXES`` is this command's own output, deleted before the rebuild, exactly like
the other generators. Rebuilding is refused while a learner has attempts on those drills
and ``--yes-replace-history`` allows it on purpose, because deleting an exercise deletes
the attempts that point at it.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max, Q

from exercises.data import pronunciation_pairs
from exercises.models import Answer, Exercise, ExerciseAttempt, Question
from lessons.models import Lesson, LessonWord
from vocabulary.models import Word

#: Two options: the word that was played, and the word one sound away from it.
OPTIONS = 2

#: Questions per exercise. Fewer than the word drills' ten, because every question here is
#: something to listen to (usually twice) rather than something to read.
BATCH = 6

#: Every exercise this command writes starts with this, and no authored exercise does. One
#: list, so the rebuild, the history gate and the report cannot disagree about what is ours.
TITLE_PREFIX = "تمرین تلفظ"
TITLE_PREFIXES = [TITLE_PREFIX]

PRONUNCIATION_TITLE = "تمرین تلفظ — تمایز صدا"

PRONUNCIATION_INSTRUCTION = (
    "به صدا گوش کنید و بگویید کدام واژه را شنیدید. "
    "این دو واژه فقط در یک صدا با هم تفاوت دارند."
)


class Command(BaseCommand):
    help = "Build listening drills that ask the learner to tell similar-sounding words apart."

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

    def level_words(self, level):
        """Every published word of the level, keyed by its lower-case spelling.

        Keyed by spelling because that is how a partner is looked for, and lower-cased
        because a learner reading two options cannot be helped by the capital letter of a
        German noun. Two rows that differ only in case — ``Essen`` the meal and ``essen`` to
        eat — keep whichever comes first by id, so the same content always yields the same
        option.
        """
        words = {}

        for word in Word.objects.filter(level=level, is_published=True).order_by("pk"):
            if word.word.lower() not in words:
                words[word.word.lower()] = word

        return words

    def substituted(self, text, first, second, pool):
        """``text`` with any one occurrence of ``first`` replaced by ``second``.

        Every occurrence is tried, not only the first: ``leben`` becomes ``lieben`` through
        its first ``e``, while the second one spells nothing. Returns the ``Word`` the result
        names, or ``None`` when no occurrence spells another word of the level.
        """
        start = 0

        while True:
            index = text.find(first, start)
            if index < 0:
                return None

            candidate = text[:index] + second + text[index + len(first) :]
            if candidate in pool:
                return pool[candidate]

            start = index + 1

    def partner_for(self, word, pool):
        """The word one sound away from ``word``, and the name of that difference.

        Each contrast is tried in both directions, which is how one entry covers the pair
        from both sides: ``leben`` finds ``lieben`` and ``lieben`` finds ``leben``. A word
        that no contrast reaches returns ``None`` rather than being asked with a partner that
        is not a minimal pair.
        """
        text = word.word.lower()

        for first, second, label in pronunciation_pairs.CONTRASTS:
            partner = self.substituted(text, first, second, pool)
            if partner is None:
                partner = self.substituted(text, second, first, pool)
            if partner is not None:
                return partner, label

        return None, None

    def published_words(self, lesson):
        """The words this lesson should drill, in the order the lesson lists them.

        The words it introduces (``role=NEW``). A lesson that introduces no word is a
        **review lesson** — lesson 12, «Wiederholung A1.1» — and it gets nothing here: its
        sound pairs were taught with the words when they were introduced, so a second
        listening would be the same question twice. It still gets the turned-around word
        drills (``seed_a1_word_drills``), which ask the words a new way.
        """
        # A review lesson introduces no word of its own. Its sound pairs were taught with
        # the lesson that introduced the words, and hearing them again would be the same
        # question twice, so a review lesson gets no sound drill — its review is the
        # turned-around word drills, which ask something new.
        if not lesson.lesson_words.filter(role=LessonWord.Role.NEW).exists():
            return []

        links = lesson.lesson_words.filter(
            role=LessonWord.Role.NEW, word__is_published=True
        )

        words = []
        for link in links.select_related("word").order_by("order", "pk"):
            words.append(link.word)

        return words

    def questions_for(self, lesson, pool):
        """One question per word of this lesson that another word is one sound away from.

        The word that will be played is the answer, so it must have a recording: without one
        there is no question to ask, and a silent question would be a bug the learner could
        not report. The partner needs no recording — it is only ever an option.

        Both words of a pair are asked when the lesson teaches both, because discriminating a
        contrast works in both directions. What is *not* asked twice is the same pair of
        spellings: ``sie`` (she) and ``Sie`` (you, formal) are two words that sound alike, and
        lesson 1 links both, so one sound would otherwise become the same question twice.
        """
        questions = []
        asked = set()

        for word in self.published_words(lesson):
            if not word.audio:
                continue

            partner, label = self.partner_for(word, pool)
            if partner is None:
                continue

            sound = (word.word.lower(), partner.word.lower())
            if sound in asked:
                continue
            asked.add(sound)

            questions.append(
                {
                    "word": word,
                    "partner": partner,
                    "label": label,
                    # Which of the two options is the right one. From the word's own id, so
                    # the answer is not always the first option while still being decided by
                    # the content: two runs on the same data agree.
                    "slot": (word.pk % OPTIONS) + 1,
                }
            )

        return questions

    def batches(self, questions, batch):
        """The questions split into exercises of ``batch`` questions each."""
        parts = []

        for start in range(0, len(questions), batch):
            parts.append(questions[start : start + batch])

        return parts

    def lesson_plan(self, lesson, pool, batch):
        """The exercises this lesson should get, already split into batches.

        A lesson where no word has both a recording and a partner returns an empty list
        rather than an empty exercise.
        """
        questions = self.questions_for(lesson, pool)

        plan = []

        for number, part in enumerate(self.batches(questions, batch), start=1):
            plan.append({"title": f"{PRONUNCIATION_TITLE} ({number})", "questions": part})

        return plan

    def write_exercise(self, lesson, drill):
        """Write one exercise with its questions, their two options and their audio.

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
            instruction=PRONUNCIATION_INSTRUCTION,
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
                prompt=f"کدام واژه را شنیدی؟ تفاوت این دو: {row['label']}",
                order=order,
                # The recording this word already has, not a new one: the same rule
                # `seed_a1_exercises` follows for its sentences.
                audio=row["word"].audio.name,
            )

            for position in range(1, OPTIONS + 1):
                if position == row["slot"]:
                    text = row["word"].word
                    is_correct = True
                else:
                    text = row["partner"].word
                    is_correct = False

                Answer.objects.create(
                    question=question, text=text, is_correct=is_correct, order=position
                )

            # Deliberately no `QuestionTarget`. See the module docstring: the mistake is
            # about two words at once, and tagging one of them would both move that word's
            # progress on a question about sound and make the word drills skip it.

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

        # One pool per level, built once: the partner of a word is looked up by spelling, and
        # a level that is looked up per lesson would be rebuilt 24 times.
        pools = {}

        planned = []
        silent_words = 0
        for lesson in lessons:
            level = lesson.course.language_level
            if level.pk not in pools:
                pools[level.pk] = self.level_words(level)

            for word in self.published_words(lesson):
                if not word.audio:
                    silent_words += 1

            plan = self.lesson_plan(lesson, pools[level.pk], options["batch"])
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
                "Nothing to build: no published lesson has a word that another word is one "
                "sound away from."
            )
            if silent_words:
                self.stdout.write(
                    f"({silent_words} word(s) of those lessons have no recording, so they "
                    f"cannot be asked. Run the audio commands first.)"
                )
            return

        exercise_total = 0
        question_total = 0
        pairs = set()
        labels = set()

        for lesson, plan in planned:
            exercise_total += len(plan)
            for drill in plan:
                question_total += len(drill["questions"])
                for row in drill["questions"]:
                    pairs.add(tuple(sorted([row["word"].pk, row["partner"].pk])))
                    labels.add(row["label"])

        existing = self.owned_exercises().count()

        # An attempt points at both the exercise and the question, and the rebuild deletes
        # both, so these rows disappear with the drills. Count them while they still exist.
        attempt_rows = ExerciseAttempt.objects.filter(exercise__in=self.owned_exercises())
        attempt_total = attempt_rows.count()
        learner_total = attempt_rows.values("user").distinct().count()

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would replace {existing} pronunciation drill(s) with "
                f"{exercise_total} exercises / {question_total} questions."
            )
            self.stdout.write(
                f"Dry run: {len(pairs)} sound pair(s) from {len(labels)} contrast(s), "
                f"over {len(planned)} lesson(s)."
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
                    f"to the {existing} pronunciation drill(s) this command would replace."
                )
            )
            self.stderr.write(
                "Deleting those exercises also deletes those attempts, which are the history "
                "the review and progress features read."
            )
            raise CommandError(
                "Refusing to replace pronunciation drills that have learner attempts. "
                "Re-run with --yes-replace-history to delete that history too."
            )

        if attempt_total:
            self.stderr.write(
                self.style.WARNING(
                    f"--yes-replace-history: deleting {attempt_total} stored attempt(s) from "
                    f"{learner_total} learner(s) together with the pronunciation drills."
                )
            )

        # One transaction, so a failure half-way cannot leave the content deleted.
        with transaction.atomic():
            self.owned_exercises().delete()

            for lesson, plan in planned:
                for drill in plan:
                    self.write_exercise(lesson, drill)

        self.stdout.write(
            f"Built {exercise_total} pronunciation drill(s) with {question_total} questions, "
            f"replacing {existing}."
        )
        self.stdout.write(
            f"Sound pairs drilled: {len(pairs)}, from {len(labels)} of the "
            f"{len(pronunciation_pairs.CONTRASTS)} trained contrasts, "
            f"over {len(planned)} lesson(s)."
        )
        if silent_words:
            self.stdout.write(f"Words left out for having no recording: {silent_words}.")
