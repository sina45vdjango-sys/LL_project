"""A short sample check: do you already know this lesson?

Some learners arrive already knowing half of A1 — a lesson whose words they use every day.
The journey teaches a lesson in eight screens, so for those learners it is eight screens of
things they already know, with no way to say so. This module builds the *check* behind the
«این درس را می‌دانم» action on the lesson's first step: a handful of the lesson's own real
questions, spread over the kinds of drill the lesson has, so a learner who already knows the
material passes and a learner who does not, fails.

Nothing is authored and nothing is written to the database here. The questions are rows that
already exist and are already published, and they are graded, recorded and scheduled by the
same submission every other answer uses — so a check is practice, not a shortcut around it.
The pass line is a ratio rather than a mark: the point is "you clearly know this", and the
caller is told how many right answers that takes.
"""

import math

from exercises.models import Exercise, Question

#: How many questions one check asks: enough to span several skills, few enough to finish in
#: a minute.
CHECK_SIZE = 5

#: The share of the sample that counts as "you already know this".
PASS_RATIO = 0.8

#: A scramble has no word bank on this page — the words are shown on the exercise page that
#: owns one — so it would arrive as a bare typed question. ``exercises/session.py`` leaves
#: scrambles out for the same reason.
SKIPPED_TYPES = (Exercise.ExerciseType.SCRAMBLE,)


def markable(question):
    """Whether this question has an authored correct answer at all.

    A question with none cannot be graded, and a check has a handful of slots — none of them
    should go to something the server can only answer "unchecked" to.
    """
    for answer in question.answers.all():
        if answer.is_correct:
            return True
    return False


def usable_questions(lesson):
    """The lesson's published questions this check may ask, in the lesson's teaching order."""
    questions = (
        Question.objects.filter(
            exercise__lesson=lesson,
            exercise__is_published=True,
        )
        .exclude(exercise__type__in=SKIPPED_TYPES)
        .select_related("exercise")
        .prefetch_related("answers")
        .order_by("exercise__order", "order", "pk")
    )

    usable = []
    for question in questions:
        if markable(question):
            usable.append(question)

    return usable


def check_questions(lesson, size=None):
    """A short sample of the lesson's own questions, one per kind of drill first.

    Taking the first question of each exercise type before taking a second of any gives a
    check that spans the lesson rather than five meaning questions in a row — the same
    "varied by kind" rule ``exercises/session.py`` follows. When the lesson has fewer kinds
    than ``size``, the rest is filled in teaching order.
    """
    if size is None:
        size = CHECK_SIZE

    usable = usable_questions(lesson)

    first_by_type = {}
    for question in usable:
        key = question.exercise.type
        if key in first_by_type:
            continue
        first_by_type[key] = question

    chosen = []
    chosen_ids = set()

    for key in first_by_type:
        if len(chosen) >= size:
            break
        question = first_by_type[key]
        chosen.append(question)
        chosen_ids.add(question.pk)

    for question in usable:
        if len(chosen) >= size:
            break
        if question.pk in chosen_ids:
            continue
        chosen.append(question)
        chosen_ids.add(question.pk)

    return chosen


def pass_needed(total):
    """How many right answers count as "you already know this" out of ``total`` questions.

    A ratio rounded **up**, and never zero: a three-question sample needs all three, and a
    check with no gradeable question can never be passed on a technicality.
    """
    if total <= 0:
        return 1
    return math.ceil(total * PASS_RATIO)
