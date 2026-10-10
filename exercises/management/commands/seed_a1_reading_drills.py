"""Give every lesson one real reading task, built from the sentences the lesson already has.

A1 LESEN is one of the four official exam sections, and until now the course practised it
with one question per sentence: a single German line with its meaning on offer. That is a
translation question wearing a reading label — the learner never has to hold a text together
and find something *in* it, which is what the exam asks.

This command builds one small reading exercise per lesson out of content that is already
there. The text is the lesson's own dialogue — or its first sentences, for a lesson with no
dialogue — and the questions are the two things an A1 reading task actually asks:

1. **where in the text** — a Persian meaning is given and the learner picks the line of the
   text that carries it. The wrong options are the *other lines of the same text*, so the
   question cannot be answered without reading it. The generated sentence drill asks which
   sentence of the whole course has this meaning; asking it inside a short text is the step
   from recognising a sentence to reading one.
2. **what is not in the text** — three lines of the text and one sentence the same lesson
   teaches elsewhere. Nothing here is invented: the outsider is a real sentence of the
   lesson, and the only way to place it is to have read the text.

The text is carried by ``CONTEXT`` targets — several on one question — which is what
``exercises/runner.py`` joins into the LTR block above the prompt. Without them a reading
question has a one-line "text", which is the thing this command exists to replace.

Neither question moves ``WordProgress``: a learner who misreads a text has not told us which
word they misread, and the sentence drills already make the same point. Nothing is asked
twice either — a sentence used as one line of a passage is still asked about on its own,
because ``seed_a1_sentence_drills`` counts a sentence as "already asked about" only when a
question is about that sentence **alone**, not when it is one line of a passage.

**This command deletes and rebuilds.** What it wrote last time is removed first — only its own
exercises, identified by the title prefix in ``TITLE_PREFIX``, which no authored exercise
uses. Deleting an exercise cascades to its questions, and an ``ExerciseAttempt`` points at
both, so a learner's recorded attempts *on a generated reading drill* go with it; attempts on
authored exercises are untouched. Rebuilding is therefore refused while any such attempt
exists, and ``--yes-replace-history`` allows it on purpose and says how much history it
deletes.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.models import Lesson, LessonSentence

#: Lines in the text. Four is the length of an A1 LESEN task's short text and long enough
#: that a question about it cannot be answered from one line.
PASSAGE_LINES = 4

#: Options per question, the correct one included. Four is what the authored reading
#: questions and the other generated drills use.
OPTIONS = 4

#: A text of one or two lines is not a text, so a lesson that short gets no exercise.
MIN_PASSAGE_LINES = 3

#: Every exercise this command writes starts with this, and no authored exercise does. It is
#: what marks a generated reading drill for the rebuild and for ``exercises/generated.py``.
TITLE_PREFIX = "تمرین خواندن"

READING_TITLE = "تمرین خواندن — متن کوتاه"

INSTRUCTION = "متن را بخوان و به سؤال‌ها جواب بده."

WHERE_PROMPT = "معنیِ «{}» در کدام خطِ متن آمده است؟"

ABSENT_PROMPT = "کدام جمله در این متن نیست؟"


def folded(text):
    """One comparable form of a line: whitespace folded, lower case.

    Two lines of a lesson are the same line to a reader when they differ only in spacing or
    capitalisation, and offering both as options would be offering one option twice.
    """
    return " ".join(str(text).split()).lower()


def owned_exercises():
    """Every exercise this command owns — everything under its own title prefix."""
    return Exercise.objects.filter(title__startswith=TITLE_PREFIX)


class Command(BaseCommand):
    help = "Build one reading exercise per lesson from the sentences that lesson teaches."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
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

    def repeated_line(self, sentence, chosen):
        """Whether a sentence would repeat a sentence the text already has.

        ``Guten Morgen!`` and ``Guten Morgen! Wie geht's?`` are two lines of one dialogue and
        one of them sits inside the other, so "which line carries this meaning?" has two
        defensible answers about them. A sentence whose German runs into a chosen line's
        German, or whose Persian says the same thing, is left out; the text still reads as
        one because the lines around it still follow each other.

        The same test decides the last question's outsider. A sentence the text *almost* has
        is not a fair answer to "which sentence is not in the text?" — the reader who sees
        ``Guten Morgen!`` in the text would be right to say it is there.
        """
        german = folded(sentence.text)
        persian = folded(sentence.translation_fa)

        for other in chosen:
            other_german = folded(other.text)
            other_persian = folded(other.translation_fa)
            if german in other_german or other_german in german:
                return True
            if persian == other_persian:
                return True

        return False

    def first_lines(self, links):
        """The lines of ``links`` that make the text: in order, none of them repeating one."""
        chosen = []
        sentences = []

        for link in links:
            if self.repeated_line(link.sentence, sentences):
                continue
            chosen.append(link)
            sentences.append(link.sentence)
            if len(chosen) == PASSAGE_LINES:
                break

        return chosen

    def passage_links(self, lesson):
        """The lesson's sentences that become its text, in the order it teaches them.

        A dialogue is used when the lesson has one, because a conversation is what a short
        reading text looks like; otherwise the lesson's first sentences are the text. Either
        way the lines follow each other, so they read as one passage instead of a set of
        unrelated sentences. A lesson whose dialogue cannot supply a text falls back to its
        sentences rather than going without an exercise.
        """
        links = list(
            lesson.lesson_sentences.filter(sentence__is_published=True)
            .select_related("sentence")
            .order_by("order", "pk")
        )

        dialogue = []
        for link in links:
            if link.role == LessonSentence.Role.DIALOGUE:
                dialogue.append(link)

        if len(dialogue) >= MIN_PASSAGE_LINES:
            chosen = self.first_lines(dialogue)
            if len(chosen) >= MIN_PASSAGE_LINES:
                return chosen

        return self.first_lines(links)

    def other_lines(self, lesson, passage):
        """The lesson's other sentences, for the wrong options and the last question."""
        passage_ids = set()
        for link in passage:
            passage_ids.add(link.sentence_id)

        sentences = []
        for link in lesson.lesson_sentences.select_related("sentence").order_by("order", "pk"):
            if link.sentence_id in passage_ids:
                continue
            if not link.sentence.is_published:
                continue
            sentences.append(link.sentence)

        return sentences

    def wrong_options(self, correct_text, pool):
        """Up to ``OPTIONS - 1`` lines from ``pool`` that are not the correct one.

        The offered lines are taken in the order the pool lists them, and a line is offered
        once: two options that are the same line to a reader are one option, not two.
        """
        wanted = OPTIONS - 1
        seen = []
        seen.append(folded(correct_text))

        wrong = []

        for text in pool:
            if len(wrong) == wanted:
                break
            value = folded(text)
            if value in seen:
                continue
            seen.append(value)
            wrong.append(text)

        return wrong

    def where_questions(self, passage, others):
        """One question per line of the text: which line carries this meaning?

        The wrong options are the text's other lines first, so the question is answered from
        the text. A text shorter than ``OPTIONS`` needs more, and they come from the lesson's
        own other sentences — a wrong option the lesson never teaches would be answerable
        without reading anything.
        """
        questions = []

        for link in passage:
            pool = []
            for other in passage:
                if other.sentence_id == link.sentence_id:
                    continue
                pool.append(other.sentence.text)
            for sentence in others:
                pool.append(sentence.text)

            wrong = self.wrong_options(link.sentence.text, pool)

            if not wrong:
                continue

            questions.append(
                {
                    "prompt": WHERE_PROMPT.format(link.sentence.translation_fa),
                    "correct": link.sentence.text,
                    "wrong": wrong,
                }
            )

        return questions

    def absent_question(self, passage, others):
        """One question asking which sentence is *not* in the text.

        The outsider is a real sentence of the same lesson, so the question cannot be
        answered by spotting a different topic — only by having read the text. A sentence
        that the text almost carries is skipped, because it is not a fair answer.
        """
        sentences = []
        for link in passage:
            sentences.append(link.sentence)

        outsider = None
        for sentence in others:
            if self.repeated_line(sentence, sentences):
                continue
            outsider = sentence
            break

        if outsider is None:
            return []

        pool = []
        for sentence in sentences:
            pool.append(sentence.text)

        return [
            {
                "prompt": ABSENT_PROMPT,
                "correct": outsider.text,
                "wrong": self.wrong_options(outsider.text, pool),
            }
        ]

    def lesson_plan(self, lesson):
        """The exercise this lesson should get, or nothing when it has no text to read."""
        passage = self.passage_links(lesson)

        if len(passage) < MIN_PASSAGE_LINES:
            return []

        others = self.other_lines(lesson, passage)

        questions = self.where_questions(passage, others)
        questions += self.absent_question(passage, others)

        if not questions:
            return []

        return [
            {
                "title": READING_TITLE,
                "type": Exercise.ExerciseType.READING,
                "instruction": INSTRUCTION,
                "passage": passage,
                "questions": questions,
            }
        ]

    def write_exercise(self, lesson, drill):
        """Write one exercise with its questions, their options and the passage targets.

        ``Question.order`` is numbered across the whole lesson in the existing data, so these
        continue from where the lesson's questions stop.
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

            Answer.objects.create(
                question=question, text=row["correct"], is_correct=True, order=1
            )

            position = 1
            for text in row["wrong"]:
                position += 1
                Answer.objects.create(
                    question=question, text=text, is_correct=False, order=position
                )

            # Every line of the text, on every question, so the learner reads the passage
            # above each one instead of a single line. The runner joins these in order.
            for link in drill["passage"]:
                QuestionTarget.objects.create(
                    question=question,
                    sentence=link.sentence,
                    role=QuestionTarget.Role.CONTEXT,
                )

        return exercise

    def handle(self, *args, **options):
        lessons = Lesson.objects.filter(is_published=True, course__is_published=True)
        if options["lesson"]:
            lessons = lessons.filter(pk=options["lesson"])
        lessons = lessons.order_by("course__language_level__order", "order", "pk")

        planned = []
        for lesson in lessons:
            plan = self.lesson_plan(lesson)
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
            self.stdout.write("Nothing to build: no published lesson has a text of its own.")
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
                f"Dry run: would replace {existing} reading drill(s) with {exercise_total} "
                f"exercise(s) / {question_total} questions."
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
                    f"to the {existing} reading drill(s) this command would replace."
                )
            )
            self.stderr.write(
                "Deleting those exercises also deletes those attempts, which are the history "
                "the review and progress features read."
            )
            raise CommandError(
                "Refusing to replace reading drills that have learner attempts. "
                "Re-run with --yes-replace-history to delete that history too."
            )

        if attempt_total:
            self.stderr.write(
                self.style.WARNING(
                    f"--yes-replace-history: deleting {attempt_total} stored attempt(s) from "
                    f"{learner_total} learner(s) together with the reading drills."
                )
            )

        # One transaction, so a failure half-way cannot leave the content deleted.
        with transaction.atomic():
            owned_exercises().delete()

            for lesson, plan in planned:
                for drill in plan:
                    self.write_exercise(lesson, drill)

        self.stdout.write(
            f"Done: {existing} reading drill(s) replaced by {exercise_total} exercise(s) / "
            f"{question_total} questions."
        )
