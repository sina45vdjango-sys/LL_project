"""Which material a learner may be given, based on how far they have come.

The course is a path: lesson 1, lesson 2, and so on. Practice should follow the same path.
A learner who has only reached lesson 3 should not be handed practice built from lesson 20,
even though lesson 20 exists and is published — seeing a word nobody has taught yet is not
practice, it is a wall.

This module is the one place that answers \"how far has this learner come\". Two callers need
it — the exercise picker behind the review plan and today's plan — and the rule has to be
the same for both, so it lives here instead of being written twice.

**What \"reached\" means.** The project already records it: ``LessonProgress`` is written the
first time a learner opens a lesson and keeps its status (``lessons/progress.py``). A lesson
is *reached* when a row exists for it at all, whatever the status — starting a lesson is
enough to practise it. The eligible set is then every published lesson up to the furthest
one reached, in course order, so \"lesson N and everything before it\" has one definition.

A learner with no account has no history to read, so nothing is hidden from them: they get
the whole course, exactly as the site is for a visitor everywhere else. A brand-new account
with no progress yet gets the first published lesson, so there is something to practise on
day one rather than an empty page.
"""

from exercises.models import ExerciseAttempt
from lessons.models import Lesson, LessonProgress


def reached_lesson_ids(user, progress=None):
    """The ids of the lessons this learner has opened or practised.

    Two kinds of row count, because a learner can reach a lesson either way. Opening it
    writes a ``LessonProgress`` row. Answering one of its exercises writes an
    ``ExerciseAttempt`` but not necessarily a progress row, so the lesson an attempt
    belongs to is read too — otherwise a learner who practised a lesson from the exercise
    list would be told they had not reached it, and the practice built from their own
    answers would be hidden from them.

    ``progress`` is the caller's own list of this learner's ``LessonProgress`` rows when it
    already holds them (``lessons/progress.py::progress_rows``). A page can ask this
    question more than once — «امروز» asks it for the review plan and again for the review
    queue — and passing the rows in means the same table is read once rather than twice.
    """
    ids = set()

    if not user.is_authenticated:
        return ids

    if progress is None:
        progress = LessonProgress.objects.filter(user=user)

    for row in progress:
        ids.add(row.lesson_id)

    for lesson_id in ExerciseAttempt.objects.filter(user=user).values_list(
        "exercise__lesson_id", flat=True
    ):
        ids.add(lesson_id)

    return ids


def course_lessons():
    """Every published lesson of a published course, in the order the path shows them."""
    return list(
        Lesson.objects.filter(is_published=True, course__is_published=True).order_by(
            "course__language_level__order",
            "course__pk",
            "order",
            "pk",
        )
    )


def eligible_lessons(user, lessons=None, progress=None):
    """The published lessons this learner may be given practice from, in course order.

    A visitor gets everything; a learner with no progress gets the first lesson; everyone
    else gets every lesson up to the furthest one they have reached.

    ``lessons`` and ``progress`` are the caller's own copies of the two things this reads,
    when it already has them (see ``course_lessons`` and ``reached_lesson_ids``).
    """
    if lessons is None:
        lessons = course_lessons()

    if not user.is_authenticated:
        return lessons

    reached = reached_lesson_ids(user, progress)
    if not reached:
        return lessons[:1]

    furthest = -1
    for index, lesson in enumerate(lessons):
        if lesson.pk in reached:
            furthest = index

    return lessons[: furthest + 1]


def eligible_lesson_ids(user, lessons=None, progress=None):
    """The ids of ``eligible_lessons``, as a plain list for a query."""
    ids = []
    for lesson in eligible_lessons(user, lessons, progress):
        ids.append(lesson.pk)
    return ids
