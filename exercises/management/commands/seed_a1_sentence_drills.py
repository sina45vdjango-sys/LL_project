"""Turn each lesson's own sentences into questions, so the course asks about whole sentences too.

The course teaches 1,008 words and now asks about every one of them, but a word list is not
a language. 339 sentences are published, each with a Persian translation and an audio file,
and only three sentences per lesson are ever asked about — by the generated listening
exercise, which plays the file and asks what it means. The rest were shown in the lesson and
never asked about again.

This command closes that gap from content that is already there. Per lesson it takes the
lesson's own sentences (``LessonSentence``) and writes three questions for each one, all from
the two facts a ``Sentence`` row already stores — its German text and its Persian meaning:

1. **معنی** — the German sentence is the passage and the learner picks its Persian meaning out
   of four. This is a ``READING`` question carrying the sentence as its ``CONTEXT`` target,
   which is what ``exercises/runner.py`` renders as the LTR passage above the prompt; the
   authored «خواندن و درک مطلب» questions already work this way.
2. **کدام جمله** — the other direction: the Persian meaning is in the prompt and the four
   options are German sentences. Recognition only goes one way otherwise: a learner can pick
   the meaning of a sentence without being able to pick the sentence out.
3. **مرتب کردن جمله** — a ``SCRAMBLE``: the sentence's words are shown shuffled and the learner
   writes them back in the right order. The first two ask the learner to recognise a sentence;
   this is the one that makes them build it, because picking the right sentence out of four
   says nothing about being able to put German word order together. The meaning is the cue and
   the single correct ``Answer`` row is the sentence — the words are derived from it and shown
   by ``exercises/runner.py``, so this command stores no scrambled order of its own.

Two things about honesty:

* A sentence that some other exercise already asks about is left alone. An authored reading
  question points at its sentence with a ``CONTEXT`` target, and the listening questions —
  written before question targets existed — are recognised by their own ``audio``, which is
  the sentence's own file. Either way the sentence already has a question, and asking it
  again in another exercise is duplicate content rather than more practice.
* A sentence of fewer than two words is skipped by the scramble only, because there is no
  order to put one word into. The other two directions still ask about it.
* The wrong Persian meanings and the wrong German sentences are drawn from the whole level,
  not from the lesson: a lesson's sentences are usually one short text, and four options
  taken from a single text are recognisable as a set instead of being read. The scan starts
  at the sentence's own id, so the wrong options vary inside one exercise — always reading
  the pool from the front would hand every question the same three wrong answers.

A question is dropped rather than written without honest wrong options, and a lesson whose
sentences are all asked about elsewhere gets no exercise at all.

Nothing here moves ``WordProgress``. A sentence question carries no word target, because a
learner who misreads a sentence has not told us which word they misread, and writing a
guessed word there would put an invented number on the learner's own page.

**This command deletes and rebuilds.** What it wrote last time is removed first — only its
own exercises, identified by the title prefix in ``TITLE_PREFIX``, which no authored exercise
uses. Running it twice does not double the content. Deleting an exercise cascades to its
questions (and an ``ExerciseAttempt`` points at both), so a learner's recorded attempts *on a
generated sentence drill* go with it; attempts on authored exercises are untouched. Rebuilding
is therefore refused while any such attempt exists, and ``--yes-replace-history`` allows it on
purpose and says how much history it deletes.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.models import Lesson
from vocabulary.models import Sentence

#: Options per question, the correct one included. Four is what the authored reading
#: questions and the generated word drills use.
OPTIONS = 4

#: Questions per exercise. The same size as the word drills: a sitting, not a chore.
BATCH = 10

#: Every exercise this command writes starts with this, and no authored exercise does. It is
#: what marks a generated sentence drill for the rebuild and for the "already asked" checks.
TITLE_PREFIX = "تمرین جمله"

MEANING_TITLE = "تمرین جمله — معنی"
GERMAN_TITLE = "تمرین جمله — کدام جمله"
ORDER_TITLE = "تمرین جمله — مرتب کردن"

MEANING_INSTRUCTION = "جملهٔ آلمانی را بخوان و معنی درست آن را انتخاب کن."
GERMAN_INSTRUCTION = "معنی فارسی را بخوان و جملهٔ آلمانی درست را انتخاب کن."
ORDER_INSTRUCTION = "واژه‌های درهم را به ترتیب درست بچین و جمله را بنویس."

MEANING_PROMPT = "معنیِ این جمله کدام است؟"


def owned_exercises():
    """Every exercise this command owns — everything under its own title prefix."""
    return Exercise.objects.filter(title__startswith=TITLE_PREFIX)


def owned_questions():
    """Every question of this command's own drills.

    Used to exclude what the command wrote last time from "what is already asked about",
    which is what makes a second run reproduce the same plan instead of deciding its own
    output is existing content.
    """
    return Question.objects.filter(exercise__in=owned_exercises())


class Command(BaseCommand):
    help = "Build sentence reading drills from the sentences each lesson already has."

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

    def asked_sentences(self):
        """The ids of the sentences some other exercise already asks about.

        Two kinds of question point at a sentence, and both are read from rows rather than
        assumed: an authored reading question carries its sentence as a ``CONTEXT`` target,
        and the listening questions — written before question targets existed — are
        recognised by their ``audio``, which is the sentence's own file.

        This command's own questions are left out of both checks, or a second run would read
        its own output as existing content and build almost nothing.

        A sentence counts as asked about only when a question is about **that sentence
        alone**. A reading drill puts several sentences on one question — that is a passage,
        not a question about each of its lines — so its lines stay available here and the
        two generators do not take content away from each other.
        """
        asked = set()

        rows = list(
            QuestionTarget.objects.filter(sentence__isnull=False).exclude(
                question__in=owned_questions()
            )
        )

        lines_per_question = {}
        for row in rows:
            if row.question_id in lines_per_question:
                lines_per_question[row.question_id] += 1
            else:
                lines_per_question[row.question_id] = 1

        for row in rows:
            if lines_per_question[row.question_id] == 1:
                asked.add(row.sentence_id)

        audio_names = set()
        for name in (
            Question.objects.exclude(audio="")
            .exclude(audio__isnull=True)
            .values_list("audio", flat=True)
        ):
            audio_names.add(name)

        for sentence in Sentence.objects.filter(is_published=True):
            if not sentence.audio:
                continue
            if sentence.audio.name in audio_names:
                asked.add(sentence.pk)

        return asked

    def lesson_sentences(self, lesson, asked):
        """The lesson's own sentences that nothing asks about yet, in the order it teaches them.

        Picked sentences are added to ``asked``, which the whole run shares. A sentence
        taught in several lessons — every later lesson reuses the ones before it — would
        otherwise get the same three questions in each of them; the first lesson that teaches
        it asks about it, and the rest leave it alone.
        """
        links = (
            lesson.lesson_sentences.filter(sentence__is_published=True)
            .select_related("sentence")
            .order_by("order", "pk")
        )

        sentences = []
        for link in links:
            if link.sentence.pk in asked:
                continue
            sentences.append(link.sentence)
            asked.add(link.sentence.pk)

        return sentences

    def option_pools(self, level):
        """The level's sentences as the two option pools: Persian meanings and German text.

        Both directions draw their wrong options from the whole level, because a lesson's
        sentences are usually one short text and four options taken from one text are
        recognisable as a set rather than read. Duplicates are dropped: two options with the
        same text would make one of them a second correct answer.
        """
        meanings = []
        texts = []

        for sentence in Sentence.objects.filter(level=level, is_published=True).order_by("pk"):
            if sentence.translation_fa not in meanings:
                meanings.append(sentence.translation_fa)
            if sentence.text not in texts:
                texts.append(sentence.text)

        return meanings, texts

    def wrong_options(self, correct, candidates, start):
        """Three wrong options for ``correct``, or ``None`` when the pool is too small.

        The scan starts at ``start`` and wraps around. Always reading the pool from the front
        would hand every question of a lesson the same three wrong answers, which a learner
        can learn to pattern-match instead of reading the sentences; the offset is the
        sentence's own id, so the variation is real but still reproducible.
        """
        if not candidates:
            return None

        wrong = []
        index = start % len(candidates)
        tries = 0

        while len(wrong) < OPTIONS - 1 and tries < len(candidates):
            text = candidates[index]
            if text != correct and text not in wrong:
                wrong.append(text)

            index += 1
            if index == len(candidates):
                index = 0
            tries += 1

        if len(wrong) < OPTIONS - 1:
            return None
        return wrong

    def option_rows(self, correct, wrong, slot):
        """The options in display order, the correct one in slot ``slot`` (1-based).

        The slot comes from the sentence's id, so the right answer is not always in the same
        place — while still being decided by the data, so two runs on the same content agree.
        """
        options = []
        wrong_index = 0

        for position in range(1, len(wrong) + 2):
            if position == slot:
                options.append((correct, True))
            else:
                options.append((wrong[wrong_index], False))
                wrong_index += 1

        return options

    def meaning_questions(self, sentences, pool):
        """One question per sentence: read the German sentence, pick its Persian meaning."""
        questions = []

        for sentence in sentences:
            wrong = self.wrong_options(sentence.translation_fa, pool, sentence.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "sentence": sentence,
                    "prompt": MEANING_PROMPT,
                    "correct": sentence.translation_fa,
                    "wrong": wrong,
                    "slot": (sentence.pk % OPTIONS) + 1,
                }
            )

        return questions

    def german_questions(self, sentences, pool):
        """One question per sentence in the other direction: read the Persian, pick the German."""
        questions = []

        for sentence in sentences:
            wrong = self.wrong_options(sentence.text, pool, sentence.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "sentence": sentence,
                    "prompt": f"کدام جملهٔ آلمانی این معنی را می‌رساند؟\n«{sentence.translation_fa}»",
                    "correct": sentence.text,
                    "wrong": wrong,
                    "slot": (sentence.pk % OPTIONS) + 1,
                }
            )

        return questions

    def order_questions(self, sentences):
        """One question per sentence: build the sentence from its words in the right order.

        There are no wrong options here — the answer is one sentence, typed — so this is the
        one direction with a single ``Answer`` row. The shuffled words are not stored: the
        runner reads them back out of that answer, seeded by the question, so this command
        does not write a scramble it would have to keep in step with the sentence.

        A sentence of one word is left out: there is no order to get right, and the page would
        show a single token whose only possible arrangement is the answer.
        """
        questions = []

        for sentence in sentences:
            if len(sentence.text.split()) < 2:
                continue

            questions.append(
                {
                    "sentence": sentence,
                    "prompt": (
                        "این جمله را با ترتیب درست واژه‌ها بنویس.\n"
                        f"«{sentence.translation_fa}»"
                    ),
                    "correct": sentence.text,
                }
            )

        return questions

    def batches(self, questions, batch):
        """The questions split into exercises of ``batch`` questions each."""
        parts = []

        for start in range(0, len(questions), batch):
            parts.append(questions[start : start + batch])

        return parts

    def lesson_plan(self, lesson, batch, asked):
        """The exercises this lesson should get, already split into batches.

        A lesson whose sentences are all asked about elsewhere returns an empty list rather
        than an empty exercise.
        """
        sentences = self.lesson_sentences(lesson, asked)

        if not sentences:
            return []

        meanings, texts = self.option_pools(lesson.course.language_level)

        drills = [
            (
                MEANING_TITLE,
                Exercise.ExerciseType.READING,
                MEANING_INSTRUCTION,
                self.meaning_questions(sentences, meanings),
            ),
            (
                GERMAN_TITLE,
                Exercise.ExerciseType.MULTIPLE_CHOICE,
                GERMAN_INSTRUCTION,
                self.german_questions(sentences, texts),
            ),
            (
                ORDER_TITLE,
                Exercise.ExerciseType.SCRAMBLE,
                ORDER_INSTRUCTION,
                self.order_questions(sentences),
            ),
        ]

        plan = []

        for title, exercise_type, instruction, questions in drills:
            for number, part in enumerate(self.batches(questions, batch), start=1):
                plan.append(
                    {
                        "title": f"{title} ({number})",
                        "type": exercise_type,
                        "instruction": instruction,
                        "questions": part,
                    }
                )

        return plan

    def write_exercise(self, lesson, drill):
        """Write one exercise with its questions, their options and the sentence target.

        ``Question.order`` is numbered across the whole lesson in the existing data, so these
        continue from where the lesson's questions stop, and each exercise of the lesson
        carries on from the one before it.
        """
        last_order = Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"]
        if last_order is None:
            last_order = 0

        exercise = Exercise.objects.create(
            lesson=lesson,
            title=drill["title"],
            instruction=drill["instruction"],
            type=drill["type"],
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
                exercise=exercise, prompt=row["prompt"], order=order
            )

            # A scramble has one answer — the sentence itself. Everything else is a choice
            # between authored options, the correct one placed in its own display slot.
            if "wrong" in row:
                options = self.option_rows(row["correct"], row["wrong"], row["slot"])
                for position, option in enumerate(options, start=1):
                    text = option[0]
                    is_correct = option[1]
                    Answer.objects.create(
                        question=question, text=text, is_correct=is_correct, order=position
                    )
            else:
                Answer.objects.create(
                    question=question, text=row["correct"], is_correct=True, order=1
                )

            # The sentence this question is about, which is what makes the German side of a
            # reading question render as an LTR passage above the prompt. The other direction
            # carries no target: its passage would be the correct option itself.
            if drill["type"] == Exercise.ExerciseType.READING:
                QuestionTarget.objects.create(
                    question=question,
                    sentence=row["sentence"],
                    role=QuestionTarget.Role.CONTEXT,
                )

        return exercise

    def handle(self, *args, **options):
        if options["batch"] < 1:
            raise CommandError("batch must be at least 1")

        asked = self.asked_sentences()

        lessons = Lesson.objects.filter(is_published=True, course__is_published=True)
        if options["lesson"]:
            lessons = lessons.filter(pk=options["lesson"])
        lessons = lessons.select_related("course__language_level").order_by(
            "course__language_level__order", "order", "pk"
        )

        planned = []
        for lesson in lessons:
            plan = self.lesson_plan(lesson, options["batch"], asked)
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
                "Nothing to build: every published sentence is already asked about."
            )
            return

        exercise_total = 0
        question_total = 0
        for lesson, plan in planned:
            exercise_total += len(plan)
            for drill in plan:
                question_total += len(drill["questions"])

        existing = owned_exercises().count()

        # An attempt points at both the exercise and the question, and the rebuild deletes
        # both, so these rows disappear with the drills. Count them while they still exist.
        attempt_rows = ExerciseAttempt.objects.filter(exercise__in=owned_exercises())
        attempt_total = attempt_rows.count()
        learner_total = attempt_rows.values("user").distinct().count()

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would replace {existing} sentence drill(s) with {exercise_total} "
                f"exercises / {question_total} questions."
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
                    f"to the {existing} sentence drill(s) this command would replace."
                )
            )
            self.stderr.write(
                "Deleting those exercises also deletes those attempts, which are the history "
                "the review and progress features read."
            )
            raise CommandError(
                "Refusing to replace sentence drills that have learner attempts. "
                "Re-run with --yes-replace-history to delete that history too."
            )

        if attempt_total:
            self.stderr.write(
                self.style.WARNING(
                    f"--yes-replace-history: deleting {attempt_total} stored attempt(s) from "
                    f"{learner_total} learner(s) together with the sentence drills."
                )
            )

        # One transaction, so a failure half-way cannot leave the content deleted.
        with transaction.atomic():
            owned_exercises().delete()

            for lesson, plan in planned:
                for drill in plan:
                    self.write_exercise(lesson, drill)

        self.stdout.write(
            f"Built {exercise_total} sentence drill(s) with {question_total} questions, "
            f"replacing {existing}."
        )
        self.stdout.write(
            f"Sentences already asked about elsewhere: {len(asked)}."
        )
