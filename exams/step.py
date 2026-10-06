"""The step test: a short check on the way through the skills (concept 20).

The full mock exam (``exams/paper.py``) is a whole sitting — 45 questions on a 65-minute
clock. The design's «آزمون گام» is the opposite: a small station every few nodes on the
practice path. It has to be short enough that a learner does not plan an evening around
it, and it has to be **skippable**, because a test that blocks the path turns practice
into an obligation (``DESIGN_ALL_SKILLS.md``, «عیب ۴»).

So this is deliberately *not* a second exam:

* It asks the same *kinds* of question as the exam, out of the whole published course
  rather than out of the exam's own curated set. Which skill a practice question can stand
  in for is decided in one place (``paper.py::section_of``), so a step test and a paper
  cannot disagree about what a question is; which questions the *exam* may ask is a
  separate, curated decision (``management/commands/export_a1_exam_items.py``). Keeping
  the two apart matters: if a step test drew from the exam's set it would spoil a third of
  the paper before the learner ever sat it.
* Every answer goes to ``exercises:exercise-submit`` through the ordinary runner, so
  grading, XP, the word-review schedule and «امروز» all see a step test as the practice it
  is. Nothing here writes a row.
* **No exam score.** The full exam's 100 points come from 45 questions and the official
  ×1.66 factor. Applying that arithmetic to twelve questions would produce a number that
  looks like an exam result and is not, so the page counts right answers and says that is
  what it is counting. The score is the runner's own — right answers out of asked.

Nothing is stored as "a step test" either, and that is a decision rather than a gap: a
stored sitting would need a new table (and a migration) only to keep a copy of questions
the learner has already had recorded as attempts.
"""

from exercises.models import Question
from exercises.session import answered_today_ids
from lessons.today import lesson_to_work_on

from .paper import section_of
from .spec import SECTION_ORDER

#: How many questions one step test asks, and how many of them come from each of the three
#: written skills. Twelve is small enough to finish in one sitting and large enough that a
#: single lucky guess does not decide it; four each keeps all three skills in the check.
STEP_SIZE = 12
PER_SECTION = 4


def step_questions(user, today):
    """The questions of today's step test, in order, or ``None`` when there are none.

    The learner's current lesson comes first, so the check is about what they have just
    been studying, and the rest of the course fills the remaining slots so a lesson with
    little material cannot leave a step test short. A question already answered today is
    left out — the same rule a session follows — and a section with nothing left simply
    contributes fewer questions rather than the page inventing one.

    The order is the course's own, section by section, and it is stable on purpose: a step
    test is a check of the same material, not a fresh paper. A learner who wants a paper
    they have never seen is who the full exam is for.

    The pools are built here rather than read from ``paper.section_pools`` because they are
    a different set of questions: every published question of the course, classified by
    ``section_of``, not the curated exam set. That classification is a Python pass over the
    course, and this is the only page left that pays for one — it is behind a login and
    opened on purpose, unlike the public exam index, which is why the exam set became a
    stored fact.
    """
    pools = {}
    for section in SECTION_ORDER:
        pools[section] = []

    questions = (
        Question.objects.filter(
            exercise__is_published=True,
            exercise__lesson__is_published=True,
            exercise__lesson__course__is_published=True,
        )
        .select_related("exercise", "exercise__lesson")
        .prefetch_related("answers", "targets")
        .order_by("exercise__lesson__order", "exercise__order", "order", "pk")
    )

    for question in questions:
        section = section_of(question)
        if section in pools:
            pools[section].append(question)

    lesson = None
    work = lesson_to_work_on(user)
    if work is not None:
        lesson = work["lesson"]

    everything = []
    for section in SECTION_ORDER:
        for question in pools[section]:
            everything.append(question)

    answered = answered_today_ids(user, today, everything)

    chosen = []

    for section in SECTION_ORDER:
        wanted = []
        for question in pools[section]:
            if question.pk not in answered:
                wanted.append(question)

        if lesson is None:
            preferred = []
            rest = wanted
        else:
            preferred = []
            rest = []
            for question in wanted:
                if question.exercise.lesson_id == lesson.pk:
                    preferred.append(question)
                else:
                    rest.append(question)

        take = []
        for question in preferred:
            if len(take) == PER_SECTION:
                break
            take.append(question)
        for question in rest:
            if len(take) == PER_SECTION:
                break
            take.append(question)

        chosen.extend(take)

    if not chosen:
        return None

    return chosen
