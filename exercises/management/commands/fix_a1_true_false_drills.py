"""Rewrite the TRUE/FALSE statements from the Persian glosses the words already carry.

Every lesson has one ``درست / غلط`` exercise with two statements, and the second one was
built from the word's **English** gloss:

    واژهٔ آلمانی «guten Morgen» به فارسی معادل good morning است.  → غلط

The statement is true (``guten Morgen`` really does mean ``good morning``) but the answer
key says it is false, because the key was really comparing the word's **Persian** gloss
with an English string. A learner who knows the word answers «درست» and is marked wrong.
That is the product being wrong rather than the learner, and it repeated in 23 of the 24
lessons — 46 questions.

This command repairs it at the source of the mistake, which is the statement's gloss:

* a **true** statement uses the word's own ``meaning_fa``;
* a **false** statement uses a *different* word's ``meaning_fa`` from the same lesson, so
  it is false by its content and not by a translation slip;
* the two truth values swap every other lesson, so the first statement is not always the
  true one — otherwise the exercise could be answered by position.

The word each question is about does not change, so its ``TESTED_ITEM`` target, its
``WordProgress`` and the review features keep working. The command is idempotent: running
it twice writes the same statements.

It only touches authored exercises of type ``TRUE_FALSE`` (a generated drill is owned by
its own seed command). Rewriting statements does not delete a question or an answer row,
so no learner history is destroyed — only the text and the answer key are corrected.

    python manage.py fix_a1_true_false_drills --dry-run
    python manage.py fix_a1_true_false_drills

Afterwards, run ``export_a1_exercises`` so the JSON file, which is the authored content's
source of truth, carries the corrected statements too.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from exercises.generated import generated_exercises
from exercises.models import Answer, Exercise, QuestionTarget
from lessons.models import LessonWord


#: The two verdicts, always written in this order. The runner shuffles the rendered
#: options from the question's id, so their stored order is not what the learner sees.
TRUE_TEXT = "درست"
FALSE_TEXT = "غلط"


class Command(BaseCommand):
    help = "Rewrite the TRUE/FALSE statements to use Persian glosses only, and fix their answer keys."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
        parser.add_argument(
            "--lesson",
            type=int,
            default=0,
            help="Only this lesson order. Zero means every lesson.",
        )

    def lesson_words(self, lesson):
        """The words this lesson teaches, new first, then the ones it revisits.

        Used only as the pool the *wrong* meaning is drawn from, so it is the lesson's own
        vocabulary rather than the whole course: a plausible confusion, not a random one.
        """
        links = lesson.lesson_words.filter(word__is_published=True)

        new_links = links.filter(role=LessonWord.Role.NEW).order_by("order", "pk")
        review_links = links.filter(role=LessonWord.Role.REVIEW).order_by("order", "pk")

        words = []
        for link in new_links:
            words.append(link.word)
        for link in review_links:
            words.append(link.word)

        return words

    def question_word(self, question):
        """The word a statement is about, from its own ``TESTED_ITEM`` target, or ``None``."""
        for target in question.targets.all():
            if target.role == QuestionTarget.Role.TESTED_ITEM and target.word:
                return target.word
        return None

    def wrong_meaning(self, word, pool):
        """A Persian gloss from ``pool`` that is not this word's, or an empty string.

        The statement has to be false *about the word*, so the gloss must belong to a
        different word. The pool is read from its **end**, so the wrong gloss comes from a
        different part of the lesson than the word being asked about: taking the neighbour
        in the list would often hand the exercise the gloss of the other statement's own
        word, which reads as a trap rather than as a mistake. An empty string is returned
        rather than the word's own gloss, which would make the statement true and the key
        wrong again.
        """
        for other in reversed(pool):
            if other.pk == word.pk:
                continue
            if other.meaning_fa == word.meaning_fa:
                continue
            return other.meaning_fa
        return ""

    def set_verdict(self, question, is_true):
        """Point the two verdict answers at the right one, creating a row only if needed."""
        wanted = {TRUE_TEXT: is_true, FALSE_TEXT: not is_true}
        order = 1

        existing = {}
        for answer in question.answers.all():
            existing[answer.text] = answer

        for text in [TRUE_TEXT, FALSE_TEXT]:
            is_correct = wanted[text]

            if text in existing:
                answer = existing[text]
                if answer.is_correct != is_correct:
                    answer.is_correct = is_correct
                    answer.save(update_fields=["is_correct"])
            else:
                Answer.objects.create(
                    question=question, text=text, is_correct=is_correct, order=order
                )

            order += 1

    def rewrite_exercise(self, exercise):
        """Rewrite both statements of one exercise, and return how many were changed."""
        questions = list(exercise.questions.order_by("order"))

        if len(questions) != 2:
            self.stderr.write(
                f"  ! lesson {exercise.lesson.order}: expected 2 statements, found "
                f"{len(questions)} — left alone."
            )
            return 0

        pool = self.lesson_words(exercise.lesson)

        # Every other lesson puts the false statement first, so the true one is not always
        # in the same place.
        false_first = exercise.lesson.order % 2 == 0

        changed = 0
        for index, question in enumerate(questions):
            word = self.question_word(question)
            if word is None:
                self.stderr.write(
                    f"  ! lesson {exercise.lesson.order} question {question.order}: "
                    f"no word target — left alone."
                )
                continue

            is_true = index == 0
            if false_first:
                is_true = index == 1

            if is_true:
                gloss = word.meaning_fa
            else:
                gloss = self.wrong_meaning(word, pool)
                if not gloss:
                    self.stderr.write(
                        f"  ! lesson {exercise.lesson.order} question {question.order}: "
                        f"no different gloss available for a false statement — left alone."
                    )
                    continue

            question.prompt = f"واژهٔ آلمانی «{word.word}» به فارسی معادل «{gloss}» است."
            question.explanation = f"معنی واژه: {word.meaning_fa}"
            question.save(update_fields=["prompt", "explanation"])

            self.set_verdict(question, is_true)
            changed += 1

        return changed

    def handle(self, *args, **options):
        exercises = (
            Exercise.objects.filter(type=Exercise.ExerciseType.TRUE_FALSE)
            .exclude(pk__in=generated_exercises())
            .select_related("lesson")
            .order_by("lesson__order", "order", "pk")
        )

        if options["lesson"]:
            exercises = exercises.filter(lesson__order=options["lesson"])

        exercises = list(exercises)

        if not exercises:
            self.stdout.write("Nothing to fix: no authored TRUE/FALSE exercise found.")
            return

        if options["dry_run"]:
            for exercise in exercises:
                self.stdout.write(
                    f"lesson {exercise.lesson.order}: would rewrite "
                    f"{exercise.questions.count()} statement(s)"
                )
            self.stdout.write(f"Dry run: {len(exercises)} exercise(s) would be rewritten.")
            return

        total = 0
        # One transaction, so a failure half-way cannot leave an exercise half rewritten.
        with transaction.atomic():
            for exercise in exercises:
                total += self.rewrite_exercise(exercise)

        self.stdout.write(
            self.style.SUCCESS(
                f"Rewrote {total} statement(s) across {len(exercises)} exercise(s)."
            )
        )
