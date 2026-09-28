"""What a learner has already done with one exercise.

``ExerciseAttempt`` rows have been written on every submission since Phase 8 — one per
submission, never overwritten — but nothing had ever read them back. This module is the
reader, and it is what lets a result survive a page reload.

The one thing worth being careful about is *which* attempt counts. The runner writes a
new row every time a question is submitted, including after «تلاش دوباره», because the
rows are history rather than a tally. So a question the learner first got wrong and
then got right has two rows. What the page should show is where they stand now, so only
the most recent attempt at each question is counted. ``ExerciseAttempt.Meta.ordering``
is already ``-created_at``, and the query asks for that order explicitly anyway, so the
newest row for a question is simply the first one seen.

Nothing here returns the correct answer. The exercise page is built so the answers are
not in it (``exercises/runner.py``), and this must not become the back door that puts
them back.
"""

from .models import ExerciseAttempt


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
    # The id is the second sort key so "newest" stays true even when two rows share a
    # timestamp, which happens in a fast test run. `pk` only ever increases.
    attempts = ExerciseAttempt.objects.filter(user=user, exercise=exercise).order_by(
        "-created_at", "-pk"
    )

    latest = {}
    last_at = None

    for attempt in attempts:
        if last_at is None:
            last_at = attempt.created_at

        # Newest first, so the first row seen for a question is the newest one.
        if attempt.question_id in latest:
            continue
        latest[attempt.question_id] = attempt

    if not latest:
        return None

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
