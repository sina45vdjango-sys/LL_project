"""What a learner has already done with their exercises.

``ExerciseAttempt`` rows have been written on every submission since Phase 8 — one per
submission, never overwritten — but nothing had ever read them back. This module is the
reader: it is what lets a result survive a page reload, and what lets a progress or
readiness page count a learner's answers at all.

The one thing worth being careful about is *which* attempt counts. The runner writes a
new row every time a question is submitted, including after «تلاش دوباره», because the
rows are history rather than a tally. So a question the learner first got wrong and
then got right has two rows. What a page should show is where they stand now, so only
the most recent attempt at each question is counted — ``latest_attempts`` below, which
both the per-exercise history and the readiness page read, so the two can never
disagree about what "answered" means. ``ExerciseAttempt.Meta.ordering`` is already
``-created_at``, and the query asks for that order explicitly anyway, so the newest row
for a question is simply the first one seen.

Nothing here returns the correct answer. The exercise page is built so the answers are
not in it (``exercises/runner.py``), and this must not become the back door that puts
them back.
"""

from .models import ExerciseAttempt


def latest_attempts(user, exercise=None):
    """``{question id: ExerciseAttempt}`` — the learner's newest attempt at each question.

    ``exercise`` narrows it to one exercise's attempts. The rows come back newest first,
    and ``pk`` is the second sort key so two rows written in the same instant still have
    a defined order (``pk`` only ever increases).
    """
    attempts = ExerciseAttempt.objects.filter(user=user)
    if exercise is not None:
        attempts = attempts.filter(exercise=exercise)
    attempts = attempts.order_by("-created_at", "-pk")

    latest = {}
    for attempt in attempts:
        # Newest first, so the first row seen for a question is the newest one.
        if attempt.question_id in latest:
            continue
        latest[attempt.question_id] = attempt

    return latest


def wrong_counts(user, exercise):
    """``{question id: how many times the learner answered it wrong}``, for one exercise.

    Every wrong attempt is counted, not only the newest one — unlike ``latest_attempts``,
    which deliberately keeps just the newest. The two rules answer different questions:
    "where does the learner stand now" wants one row per question, while "how hard has this
    question been for them" wants the misses added up. That total is what a hint's
    strength is read from (``exercises/hints.py``).
    """
    counts = {}

    rows = ExerciseAttempt.objects.filter(
        user=user, exercise=exercise, is_correct=False
    ).values_list("question_id", flat=True)

    for question_id in rows:
        if question_id in counts:
            counts[question_id] += 1
        else:
            counts[question_id] = 1

    return counts


def exercise_history(user, exercise):
    """The learner's latest attempt at each question of this exercise.

    Returns ``None`` when they have never answered anything here, so a page can tell
    "no history" apart from "a history that is somehow empty". Otherwise:

    * ``answered`` — how many of the exercise's questions they have attempted
    * ``correct``  — how many of those their latest attempt got right
    * ``total``    — how many questions the exercise has
    * ``last_at``  — when they last answered anything here
    * ``missed``   — the questions their latest attempt got wrong, each as
      ``{"position": n, "prompt": text}`` and in the exercise's own order

    Questions are numbered by their **position** rather than ``Question.order``, which
    is lesson-wide: a lesson's true/false exercise really does start at question 12.
    """
    latest = latest_attempts(user, exercise)

    if not latest:
        return None

    # When the learner last answered anything here. The newest row overall is
    # necessarily the newest row for its own question, so the newest of the kept rows is
    # the same instant the old query reported.
    last_at = None
    for attempt in latest.values():
        if last_at is None:
            last_at = attempt.created_at
        elif attempt.created_at > last_at:
            last_at = attempt.created_at

    correct = 0
    missed = []
    total = 0

    for question in exercise.questions.order_by("order", "pk"):
        total += 1

        if question.pk not in latest:
            continue

        if latest[question.pk].is_correct:
            correct += 1
        else:
            missed.append({"position": total, "prompt": question.prompt})

    return {
        "answered": len(latest),
        "correct": correct,
        "total": total,
        "last_at": last_at,
        "missed": missed,
    }
