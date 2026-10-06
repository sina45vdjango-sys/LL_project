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

from .models import Lesson, LessonProgress

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


def import_guest_progress(user, reported):
    """Record the lessons a browser says the learner finished before signing up.

    A visitor works without an account, so their progress lives in ``localStorage``
    (``static/js/progress.js``). Signing up used to leave that memory behind the moment the
    dashboard switched to the server's answer — the work was still on the device and the
    product stopped looking at it, which is a silent loss, not a migration. The dashboard
    now asks first and posts what the browser has (``LessonImportView``); this is the write.

    ``reported`` maps a lesson id to the word the browser used, ``"started"`` or
    ``"completed"``. Three rules, and they are the same rules every other write follows:

    * a lesson already ``COMPLETED`` keeps its own ``completed_at`` and is not rewritten —
      importing a browser's memory of lesson 3 must not move the date lesson 9 was finished;
    * a ``"started"`` report creates an in-progress row (``record_step``), never a complete
      one, because the browser said the lesson was opened and not that it was finished;
    * a report the server does not understand is ignored rather than guessed at.

    Returns how many lessons the server wrote or moved forward.
    """
    written = 0

    for lesson_id, status in reported.items():
        lesson = Lesson.objects.filter(
            pk=lesson_id, is_published=True, course__is_published=True
        ).first()
        if lesson is None:
            continue

        row = LessonProgress.objects.filter(user=user, lesson=lesson).first()

        if status == "completed":
            if row is not None and row.status == LessonProgress.Status.COMPLETED:
                continue
            complete_lesson(user, lesson, LessonProgress.Step.FINISH)
            written += 1
        elif status == "started":
            # Already on the server: the browser has nothing to add here, and rewriting
            # last_activity_at would move a date the account knows better than a browser.
            if row is not None:
                continue
            record_step(user, lesson, LessonProgress.Step.INTRO)
            written += 1

    return written


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


def progress_rows(user):
    """Every lesson row this learner has, newest activity first — the table, read once.

    One page asks this table several different questions — where the learner stopped, how
    many lessons are finished, whether today's lesson is done, when they were last here,
    and the whole payload the page scripts read. Each of those used to be its own query,
    which made the dashboard read the same handful of rows five times over. They are read
    here instead and handed to whoever needs them.

    ``select_related`` is not decoration: ``lessons/today.py::started_row`` tests the
    lesson's own ``is_published`` flags, and without the join that would be one query per
    row.
    """
    return list(
        LessonProgress.objects.filter(user=user)
        .select_related("lesson__course")
        .order_by("-last_activity_at", "-pk")
    )


def progress_state(user, rows=None):
    """Every lesson this learner has touched, in the shape the page scripts read.

    ``static/js/progress.js`` exposes ``read()`` and ``summary()`` built from exactly
    this object, so the dashboard, the learning path and the lesson page keep working
    as they are — none of them has to know whether the numbers came from the server or
    from ``localStorage``.

    ``rows`` is the caller's own ``progress_rows(user)`` when it already read them, so a
    page that also asks the other questions above reads the table once.
    """
    if rows is None:
        rows = progress_rows(user)

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
