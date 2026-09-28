"""The learner's real lesson progress — the backend source of truth.

Every write goes through this module, so the rules are stated exactly once:

* the row is created the first time the learner reaches a lesson, already
  ``IN_PROGRESS`` and already carrying its first step,
* ``started_at`` is written when the row is created and never moved again, because
  coming back to a lesson must not rewrite when it was started,
* ``completed_at`` is written the first time the lesson is completed and never moved
  again, so ``completed_at - started_at`` stays the lesson's real duration,
* ``last_activity_at`` moves on meaningful learner activity — reaching a step, or
  finishing the lesson — and not on every click.

``current_step`` stores the step keys from ``lessons/journey.py``. The model's
``Step`` choices and that module's steps are the same ten names, and
``lessons.tests.LessonProgressTests`` fails if they ever drift apart.
"""

from django.utils import timezone

from .models import LessonProgress

#: How a stored status is reported to the browser. ``static/js/lesson_status.js``
#: knows exactly two words, and a lesson that has not been opened simply has no entry
#: at all — that is what makes "never started" a fact instead of a third word.
BROWSER_STATUS = {
    LessonProgress.Status.IN_PROGRESS: "started",
    LessonProgress.Status.COMPLETED: "completed",
}


def _iso(value):
    """ISO-8601 for a datetime, or ``None``. The browser does its own formatting."""
    if value is None:
        return None
    return value.isoformat()


def _row(user, lesson, step):
    """The learner's row for this lesson, created on the first visit.

    The row is created already carrying the step it was opened on and its
    ``started_at``; ``get_or_create`` means a second visit finds the row instead of
    starting over.
    """
    now = timezone.now()
    row, _ = LessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
        defaults={
            "status": LessonProgress.Status.IN_PROGRESS,
            "current_step": step,
            "started_at": now,
            "last_activity_at": now,
        },
    )
    return row


def record_step(user, lesson, step):
    """Note that the learner is on ``step`` of ``lesson``."""
    row = _row(user, lesson, step)
    row.current_step = step
    row.last_activity_at = timezone.now()
    # Reading back over a finished lesson does not un-finish it.
    if row.status != LessonProgress.Status.COMPLETED:
        row.status = LessonProgress.Status.IN_PROGRESS
    row.save()
    return row


def complete_lesson(user, lesson, step):
    """Mark the lesson finished, keeping the first ``completed_at`` it ever had."""
    row = _row(user, lesson, step)
    now = timezone.now()
    row.status = LessonProgress.Status.COMPLETED
    if row.completed_at is None:
        row.completed_at = now
    row.last_activity_at = now
    if step:
        row.current_step = step
    row.save()
    return row


def progress_dict(row):
    """One lesson's stored progress, the way the lesson page's endpoint reports it.

    These are the five facts the frontend is allowed to rely on: status, current
    step, and the three timestamps.
    """
    return {
        "status": row.status,
        "current_step": row.current_step,
        "started_at": _iso(row.started_at),
        "last_activity_at": _iso(row.last_activity_at),
        "completed_at": _iso(row.completed_at),
    }


def progress_state(user):
    """Every lesson this learner has touched, in the shape the page scripts read.

    ``static/js/progress.js`` exposes ``read()`` and ``summary()`` built from exactly
    this object, so the dashboard, the learning path and the lesson page keep working
    as they are — none of them has to know whether the numbers came from the server or
    from ``localStorage``.
    """
    rows = LessonProgress.objects.filter(user=user).order_by("-last_activity_at")
    lessons = {}
    last_lesson_id = None

    for row in rows:
        if row.status == LessonProgress.Status.NOT_STARTED:
            continue

        lessons[row.lesson_id] = {
            "status": BROWSER_STATUS[row.status],
            "updatedAt": _iso(row.last_activity_at),
        }

        # The rows come back newest-activity-first, so the first usable one is the
        # lesson the learner touched last.
        if last_lesson_id is None and row.last_activity_at is not None:
            last_lesson_id = row.lesson_id

    return {"source": "server", "lessons": lessons, "lastLessonId": last_lesson_id}
