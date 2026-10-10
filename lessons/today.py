"""Where this learner is, and what they have already done — the facts today is built from.

This module used to own «امروز» itself: an ordered list of "the lesson to work on, then the
exercise that tests your wrong words". That list and the guided day on «مسیر امروز» were two
answers to the same question, and two answers drift — the learner had to guess which one was
really today. The day now lives in one place (``lessons/skill_path.py::day_steps``) and both
pages render it. What is left here are the rows that day is made of:

1. **The lesson to work on** — the one the learner started and has not finished, or else the
   first published lesson they have not completed. When every published lesson is completed
   there is no lesson rather than an invented next step.
2. **What they have done** — how many questions they answered today (counted from
   ``ExerciseAttempt.created_at``, so nothing extra is stored), the last seven days of it for
   the week chart, and when they last did anything at all.

Everything here is read from rows that already exist. There is no plan table, no scheduled
date and no streak, and nothing in this module writes to the database. ``None`` means "we
cannot identify this visitor", exactly like ``review_plan``: a page has to tell "no account"
apart from "an account with nothing to do", because those need different words.

Deliberately **not** here: streaks, points, "you missed a day", and any invented sense of how
well the learner is doing. The schedule that decides which words are due lives in
``vocabulary/schedule.py``, and the mistakes that feed the review step live in
``vocabulary/review.py``; this module only says where the learner is and what they have done.
"""

from datetime import timedelta

from django.db.models import Count, Max, Q

from exercises.models import ExerciseAttempt

from .models import Lesson, LessonProgress
from .progress import progress_rows

#: One Persian letter per weekday for the week strip, keyed by ``date.weekday()`` (Monday
#: is 0). The Persian week starts on Saturday, so the letters are not in weekday() order.
WEEKDAY_LETTERS = {5: "ش", 6: "ی", 0: "د", 1: "س", 2: "چ", 3: "پ", 4: "ج"}


def started_row(user, rows=None):
    """This learner's row for the lesson they are inside and have not finished, or ``None``.

    Returns the row rather than the lesson because the readers of today's lesson need
    both halves of it: ``lesson_to_work_on`` wants the lesson, and the day's first step
    wants to know whether that same row already says the lesson is finished. Handing the
    row over is what keeps the second question from becoming a second query.

    Newest activity first — the same rule ``lessons/progress.py::progress_state`` uses to
    decide which lesson the learner touched last, so "continue" means the same lesson on both
    pages. ``rows`` is the caller's own ``progress_rows(user)`` when it already has them.
    """
    if rows is None:
        rows = progress_rows(user)

    for row in rows:
        if row.status != LessonProgress.Status.IN_PROGRESS:
            continue
        if not row.lesson.is_published:
            continue
        if not row.lesson.course.is_published:
            continue
        return row

    return None


def started_lesson(user, rows=None):
    """The lesson this learner is inside and has not finished, or ``None``."""
    row = started_row(user, rows)

    if row is None:
        return None
    return row.lesson


def finished_lesson_ids(user, rows=None):
    """The ids of the lessons this learner has completed."""
    if rows is None:
        rows = progress_rows(user)

    ids = set()

    for row in rows:
        if row.status != LessonProgress.Status.COMPLETED:
            continue
        ids.add(row.lesson_id)

    return ids


def next_lesson(user, lessons=None, rows=None):
    """The first published lesson this learner has not completed, or ``None``.

    In course order, not by id, so "next" means the next thing on the path — the order the
    learning path already shows. ``lessons`` is the caller's own course-ordered list of
    published lessons when it already read one (``exercises/eligibility.py::course_lessons``).
    """
    finished = finished_lesson_ids(user, rows)

    if lessons is None:
        lessons = (
            Lesson.objects.filter(is_published=True, course__is_published=True)
            .select_related("course__language_level")
            .order_by("course__language_level__order", "course__pk", "order", "pk")
        )

    for lesson in lessons:
        if lesson.pk in finished:
            continue
        return lesson

    return None


def lesson_to_work_on(user, lessons=None, rows=None):
    """Today's lesson and whether the learner is already inside it.

    ``None`` when every published lesson is completed — the page says that rather than
    promising a lesson that does not exist.
    """
    row = started_row(user, rows)

    if row is not None:
        return {"lesson": row.lesson, "started": True}

    lesson = next_lesson(user, lessons, rows)

    if lesson is None:
        return None
    return {"lesson": lesson, "started": False}


def exercises_done_today(user, today):
    """The ids of the exercises this learner has already answered today.

    ``today`` is a date in the project's own timezone (``timezone.localdate()``), and the
    comparison is a ``created_at`` date lookup, so a late-evening answer in Tehran counts as
    today rather than as tomorrow in UTC.
    """
    ids = set()

    for exercise_id in ExerciseAttempt.objects.filter(
        user=user, created_at__date=today
    ).values_list("exercise_id", flat=True):
        ids.add(exercise_id)

    return ids


def day_summary(user, today):
    """What this learner has already answered today, counted from their stored attempts."""
    answered = ExerciseAttempt.objects.filter(user=user, created_at__date=today).count()
    correct = ExerciseAttempt.objects.filter(
        user=user, created_at__date=today, is_correct=True
    ).count()

    return {"answered": answered, "correct": correct}


def weekly_activity(user, today):
    """The last seven days of this learner's own answers, oldest day first.

    One row per day, counted from ``ExerciseAttempt.created_at`` — the same rows
    ``day_summary`` counts, so the two cannot disagree about today. Days with no answers
    are kept with zeroes rather than dropped, because a gap is information too and a chart
    that closes up around it would lie about how the week went.
    """
    start = today - timedelta(days=6)

    rows = (
        ExerciseAttempt.objects.filter(user=user, created_at__date__gte=start)
        .values("created_at__date")
        .annotate(answered=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    )

    found = {}
    for row in rows:
        found[row["created_at__date"]] = row

    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        row = found.get(day)
        if row is None:
            answered = 0
            correct = 0
        else:
            answered = row["answered"]
            correct = row["correct"]
        days.append(
            {
                "date": day,
                "letter": WEEKDAY_LETTERS[day.weekday()],
                "answered": answered,
                "correct": correct,
                "is_today": day == today,
            }
        )

    # The busiest day of the week is the bar that fills the column, so the chart is scaled
    # to this learner rather than to a number invented here. A week with no answers at all
    # has no peak, and the page draws the empty week instead of dividing by zero.
    peak = 0
    for day in days:
        if day["answered"] > peak:
            peak = day["answered"]

    return {"days": days, "peak": peak}


def last_activity(user, rows=None):
    """When this learner last did anything, from their own rows, or ``None``.

    Two tables can hold the newest moment — the last step they moved through and the last
    answer they submitted — so both are read and the later one wins. ``rows`` is the
    caller's own ``progress_rows(user)`` when it already has them, in which case the newest
    moment is already sitting in the first row (they come newest-first).
    """
    if rows is None:
        latest = LessonProgress.objects.filter(user=user).aggregate(Max("last_activity_at"))
        lesson_activity = latest["last_activity_at__max"]
    else:
        # ``Max`` ignores NULLs in SQL and ``rows`` is allowed to lead with one, so the
        # newest moment is searched for rather than read off the first row.
        lesson_activity = None
        for row in rows:
            if row.last_activity_at is None:
                continue
            if lesson_activity is None:
                lesson_activity = row.last_activity_at
            elif row.last_activity_at > lesson_activity:
                lesson_activity = row.last_activity_at

    latest = ExerciseAttempt.objects.filter(user=user).aggregate(Max("created_at"))
    answer_activity = latest["created_at__max"]

    if lesson_activity is None:
        return answer_activity
    if answer_activity is None:
        return lesson_activity
    if answer_activity > lesson_activity:
        return answer_activity
    return lesson_activity
