"""How this learner is doing — from stored rows only, with every rule written down.

Milestone 1 answered "what should I do about my mistakes?" (``vocabulary/review.py``).
This module answers the other half of the product's promise: **"how am I doing, and how
far is my goal?"**

There is deliberately no single readiness percentage here, and nothing in this module
claims a CEFR level. Three separate, checkable facts are computed instead, each with a
definition a learner could redo on paper:

* **course progress** — completed published lessons out of all of them. This is the same
  measure the dashboard and the learning path already show ("progress" means completed
  lessons everywhere), not a second definition of progress.
* **exercise performance** — of the questions the learner has answered, how many their
  newest attempt got right (the rule ``exercises/history.py`` states), plus how many of
  the course's questions they have answered at all. Both are counts of real rows.
* **vocabulary performance** — how many of the course's words they have been tested on,
  and of those how many they have answered right more often than wrong. Deliberately
  threshold-free: the stored counters have no "mastered" line, so none is invented.
* **grammar performance** — the same shape, one level up: of the course's grammar topics,
  how many the learner has answered a tagged question about, and how those answers went.
  Only questions that carry a ``GRAMMAR`` target count, and a question is tagged with the
  rule it really asks about. That distinction is the whole reason the count is worth
  showing: the authored questions carry no grammar target, because nothing in them records
  which rule they exercise, and a lesson teaches three or four topics — so tagging them by
  lesson would have produced a number that was vocabulary accuracy under another name.

What the data **cannot** support is stated by ``readiness()`` in ``gaps``, and it is
computed rather than hand-written: how much of the vocabulary no question tests at all,
how many questions are still unanswered, and — when the learner's target level is above
the content that exists — the fact that the extra content has not been built. A learner
reading the page can see exactly why it does not say "you are B1 ready".

The grammar bullets above describe a learner's *numbers*. The rules behind them — which
ones went wrong, and where to practise them again — live here too, in ``missed_grammar``
and ``grammar_review``, because the ``GRAMMAR`` target rows that say which question asks
about which rule are read here and a second copy of that mapping elsewhere would be a
second definition of the same fact. The review page is where they are shown.

Nothing here writes to the database, and nothing here is an estimate: every number is
either a count, a ratio of two counts, or arithmetic on a target date.
"""

import math

from django.utils import timezone

from accounts.models import UserProfile
from exercises.history import latest_attempts
from exercises.models import Exercise, Question, QuestionTarget
from vocabulary.models import Grammar, WordProgress
from vocabulary.review import missed_words

from .models import Lesson, LessonGrammar, LessonProgress, LessonWord


def percent(part, whole):
    """A whole-number percentage, or 0 when there is nothing to divide by.

    Stated once because several numbers on the readiness page are a percentage of two
    real counts, and "0 of 0" must not be a division error or a NaN.
    """
    if whole == 0:
        return 0
    return round(part / whole * 100)


def course_word_ids():
    """The ids of the words the published lessons teach — this course's vocabulary.

    Used as the denominator for "how much of the course's vocabulary have I been tested
    on", so a word that no lesson teaches cannot make a learner look behind.
    """
    word_ids = set()
    for word_id in (
        LessonWord.objects.filter(
            lesson__is_published=True,
            lesson__course__is_published=True,
            word__is_published=True,
        )
        .values_list("word_id", flat=True)
        .distinct()
    ):
        word_ids.add(word_id)
    return word_ids


def course_progress(user, lessons=None, rows=None):
    """Completed published lessons out of all of them, and what is left to do.

    Only published lessons of published courses count, so unpublishing a lesson cannot
    leave a learner looking further along than the product really is — the same rule the
    dashboard, the learning path and the journey already follow. It also means a
    ``LessonProgress`` row for a lesson that is no longer published is simply not
    counted, rather than counted and then hidden.

    ``lessons`` and ``rows`` are the caller's own copies of the two things this reads —
    the published lessons (``exercises/eligibility.py::course_lessons``) and the learner's
    progress rows (``lessons/progress.py::progress_rows``) — so «امروز» does not read the
    same tables twice.
    """
    completed_ids = []
    if rows is not None:
        for row in rows:
            if row.status != LessonProgress.Status.COMPLETED:
                continue
            completed_ids.append(row.lesson_id)
    else:
        for row in LessonProgress.objects.filter(user=user, status=LessonProgress.Status.COMPLETED):
            completed_ids.append(row.lesson_id)

    if lessons is None:
        lessons = Lesson.objects.filter(is_published=True, course__is_published=True)

    completed = 0
    total = 0
    minutes_remaining = 0

    for lesson in lessons:
        total += 1
        if lesson.pk in completed_ids:
            completed += 1
        else:
            minutes_remaining += lesson.estimated_time

    remaining = total - completed

    return {
        "completed": completed,
        "total": total,
        "remaining": remaining,
        "minutes_remaining": minutes_remaining,
        "percent": percent(completed, total),
    }


def exercise_progress(user):
    """What the learner has answered, and how much of it was right.

    Two different facts live here on purpose, and the page must not blur them:
    ``percent`` is accuracy **on the questions answered**, while ``questions_total``
    says how small that set may be. Answering five questions correctly is 100% of five,
    not 100% of the course.

    ``answered`` counts questions, not submissions — only the newest attempt at a
    question counts — and attempts are ignored for exercises that are no longer
    published, so the numbers always describe the product as it is now.
    """
    published = Exercise.objects.filter(
        is_published=True,
        lesson__is_published=True,
        lesson__course__is_published=True,
    )

    exercise_ids = []
    for exercise_id in published.values_list("pk", flat=True):
        exercise_ids.append(exercise_id)

    exercise_total = len(exercise_ids)
    question_total = Question.objects.filter(exercise_id__in=exercise_ids).count()

    answered = 0
    correct = 0
    attempted_ids = []

    for attempt in latest_attempts(user).values():
        if attempt.exercise_id not in exercise_ids:
            continue
        answered += 1
        if attempt.is_correct:
            correct += 1
        if attempt.exercise_id not in attempted_ids:
            attempted_ids.append(attempt.exercise_id)

    questions_remaining = question_total - answered
    if questions_remaining < 0:
        questions_remaining = 0

    return {
        "answered": answered,
        "correct": correct,
        "percent": percent(correct, answered),
        "questions_total": question_total,
        "questions_remaining": questions_remaining,
        "exercises_attempted": len(attempted_ids),
        "exercises_total": exercise_total,
    }


def vocabulary_progress(user):
    """How many of the course's words the learner has been tested on, and how it went.

    Every ``WordProgress`` row is a word the learner was really tested on —
    ``vocabulary/progress.py`` writes nothing else — so ``tested`` is a count of real
    attempts, and ``remembered`` compares the two stored counters:

        answered right more often than wrong  →  correct_count > wrong_count

    That comparison is used instead of a "mastery" threshold because the data has no
    mastery line to point at. Saying "75% of the words you were tested on you answer
    right more often than wrong" is something the learner can check against their own
    history; a mastery score would not be.
    """
    course_ids = course_word_ids()

    tested = 0
    remembered = 0

    for row in WordProgress.objects.filter(user=user, word__is_published=True):
        if row.word_id not in course_ids:
            continue
        tested += 1
        if row.correct_count > row.wrong_count:
            remembered += 1

    return {
        "tested": tested,
        "remembered": remembered,
        "percent": percent(remembered, tested),
        "words_total": len(course_ids),
        "words_untested": len(course_ids) - tested,
    }


def word_coverage():
    """How much of the course's vocabulary any authored question tests at all.

    This is a fact about the **content**, not about a learner, and it is the most
    important limitation on the readiness page: nobody can be measured on words that no
    question asks about. The denominator is the course's own vocabulary, so the number
    is about this course rather than about the whole database.
    """
    course_ids = course_word_ids()

    tested_ids = set()
    for word_id in (
        QuestionTarget.objects.filter(
            role=QuestionTarget.Role.TESTED_ITEM,
            word__isnull=False,
            question__exercise__is_published=True,
            question__exercise__lesson__is_published=True,
            question__exercise__lesson__course__is_published=True,
        )
        .values_list("word_id", flat=True)
        .distinct()
    ):
        tested_ids.add(word_id)

    covered = 0
    for word_id in course_ids:
        if word_id in tested_ids:
            covered += 1

    return {
        "covered": covered,
        "total": len(course_ids),
        "uncovered": len(course_ids) - covered,
    }


def course_grammar_ids():
    """The ids of the grammar topics the published lessons teach — this course's grammar.

    Used as the denominator for "how much of the grammar have I practised", so a topic
    that no lesson teaches cannot make a learner look behind.
    """
    grammar_ids = set()
    for grammar_id in (
        LessonGrammar.objects.filter(
            lesson__is_published=True,
            lesson__course__is_published=True,
            grammar__is_published=True,
        )
        .values_list("grammar_id", flat=True)
        .distinct()
    ):
        grammar_ids.add(grammar_id)
    return grammar_ids


def grammar_questions():
    """``{question id: grammar topic id}`` for every published question that asks about a
    rule, so a submission can be counted against the topic it was really about.
    """
    topic_by_question = {}

    targets = QuestionTarget.objects.filter(
        role=QuestionTarget.Role.GRAMMAR,
        grammar__isnull=False,
        question__exercise__is_published=True,
        question__exercise__lesson__is_published=True,
        question__exercise__lesson__course__is_published=True,
    )

    for target in targets:
        topic_by_question[target.question_id] = target.grammar_id

    return topic_by_question


def grammar_progress(user):
    """How many of the course's grammar topics the learner has practised, and how it went.

    Like ``vocabulary_progress``, this is a count of real rows and a plain comparison of
    two counters, with no "mastered" line invented: a topic counts as practised when the
    learner has answered a question tagged with it at all, and ``percent`` is accuracy on
    the grammar-tagged questions they answered — not on the course.

    "Answered" follows the same newest-attempt rule as ``exercise_progress``
    (``exercises/history.py``), so the two sections cannot disagree about one submission.
    """
    course_ids = course_grammar_ids()
    topic_by_question = grammar_questions()

    answered = 0
    correct = 0
    practised_ids = []

    for attempt in latest_attempts(user).values():
        if attempt.question_id not in topic_by_question:
            continue

        answered += 1
        if attempt.is_correct:
            correct += 1

        topic_id = topic_by_question[attempt.question_id]
        if topic_id not in practised_ids:
            practised_ids.append(topic_id)

    practised = 0
    for topic_id in practised_ids:
        if topic_id in course_ids:
            practised += 1

    return {
        "answered": answered,
        "correct": correct,
        "percent": percent(correct, answered),
        "questions_total": len(topic_by_question),
        "topics_total": len(course_ids),
        "topics_practised": practised,
    }


def grammar_coverage():
    """How many of the course's grammar topics any published question asks about at all.

    The same fact as ``word_coverage``, one level up, and the honest limit on the section
    above: a rule no question is tagged with cannot be measured for anybody. Today the
    generated drills cover the article, plural and perfect-auxiliary topics, and the rest
    of the course's grammar has no question — this number says so instead of showing a
    zero that looks like the learner's fault.
    """
    course_ids = course_grammar_ids()

    asked_ids = set()
    for grammar_id in grammar_questions().values():
        asked_ids.add(grammar_id)

    covered = 0
    for grammar_id in course_ids:
        if grammar_id in asked_ids:
            covered += 1

    return {
        "covered": covered,
        "total": len(course_ids),
        "uncovered": len(course_ids) - covered,
    }


def missed_grammar(user):
    """The grammar topics this learner has answered wrong, worst first.

    The grammar half of ``vocabulary/review.py::missed_words``: a rule is listed because
    the learner really did answer a question about it wrong, and the sort keys are the
    same two — most wrong answers first, then fewest right ones.

    It is built from the same two facts ``grammar_progress`` uses, so the aggregate
    number on «آمادگی من» and this list can never contradict each other: which question
    belongs to which topic (``grammar_questions``) and the learner's **newest** answer to
    it (``latest_attempts``). Only the course's own topics count, so a drill about a rule
    no lesson teaches cannot turn up in a learner's review list.

    The newest-attempt rule means a rule the learner has since answered right is not a
    rule they still need to review — "wrong" here means "their latest answer was wrong",
    exactly what ``grammar_progress`` counts.
    """
    topic_by_question = grammar_questions()
    course_ids = course_grammar_ids()

    counts = {}

    for attempt in latest_attempts(user).values():
        if attempt.question_id not in topic_by_question:
            continue

        topic_id = topic_by_question[attempt.question_id]
        if topic_id not in course_ids:
            continue

        if topic_id not in counts:
            counts[topic_id] = {"answered": 0, "correct": 0, "wrong": 0}

        counts[topic_id]["answered"] += 1
        if attempt.is_correct:
            counts[topic_id]["correct"] += 1
        else:
            counts[topic_id]["wrong"] += 1

    topic_ids = []
    for topic_id in counts:
        topic_ids.append(topic_id)

    rows = []
    for grammar in Grammar.objects.filter(pk__in=topic_ids, is_published=True):
        entry = counts[grammar.pk]

        if entry["wrong"] == 0:
            continue

        rows.append({
            "grammar": grammar,
            "answered": entry["answered"],
            "correct": entry["correct"],
            "wrong": entry["wrong"],
        })

    rows.sort(key=lambda row: (-row["wrong"], row["correct"], row["grammar"].title))
    return rows


def grammar_practice(topics):
    """The published exercises that ask about any of ``topics``, best first.

    ``topics`` is what ``missed_grammar`` returns, so the rules the review page lists and
    the exercises it offers are decided from one place.

    The shape and the rule are ``vocabulary/review.py::exercises_for_words`` one level
    up: each row is ``{"exercise", "topics", "question_count"}``, an exercise is offered
    because its questions really carry a ``GRAMMAR`` target for one of these topics, and
    "best" means covering the most of the learner's own wrong rules first, then the usual
    lesson order. A draft exercise, a draft lesson or a draft course contributes nothing.
    """
    topic_ids = []
    for row in topics:
        topic_ids.append(row["grammar"].pk)

    if not topic_ids:
        return []

    targets = (
        QuestionTarget.objects.filter(
            role=QuestionTarget.Role.GRAMMAR,
            grammar_id__in=topic_ids,
            grammar__is_published=True,
            question__exercise__is_published=True,
            question__exercise__lesson__is_published=True,
            question__exercise__lesson__course__is_published=True,
        )
        .select_related("grammar", "question__exercise__lesson")
        .order_by(
            "question__exercise__lesson__order",
            "question__exercise__order",
            "question__order",
        )
    )

    rows = []
    by_exercise = {}

    for target in targets:
        exercise = target.question.exercise

        if exercise.pk not in by_exercise:
            row = {
                "exercise": exercise,
                "topics": [],
                "question_count": 0,
            }
            by_exercise[exercise.pk] = row
            rows.append(row)

        row = by_exercise[exercise.pk]

        # One exercise can ask several questions about the same rule, and the rule should
        # be named once in its list.
        if target.grammar not in row["topics"]:
            row["topics"].append(target.grammar)

        row["question_count"] += 1

    rows.sort(
        key=lambda row: (
            -len(row["topics"]),
            row["exercise"].lesson.order,
            row["exercise"].order,
        )
    )
    return rows


def grammar_review(user, exercise_limit=3):
    """The learner's wrong grammar topics and the exercises that practise them.

    The grammar half of ``vocabulary/review.py::review_plan``, and it returns ``None`` in
    the same two situations a page has to tell apart: a visitor we cannot identify has no
    stored answers at all, and a learner who has got every tagged question right has
    nothing to review. Otherwise:

    * ``topics``            — ``missed_grammar`` rows, worst first
    * ``wrong_topic_count`` — how many rules they really got wrong
    * ``exercises``         — the exercises that practise them, best first, at most
      ``exercise_limit``
    * ``exercise_count``    — how many there really are, whatever the limit
    """
    if not user.is_authenticated:
        return None

    topics = missed_grammar(user)

    if not topics:
        return None

    for topic in topics:
        practice_rows = grammar_practice([topic])
        if practice_rows:
            topic["practice_exercise"] = practice_rows[0]["exercise"]
        else:
            topic["practice_exercise"] = None

    exercises = grammar_practice(topics)

    return {
        "topics": topics,
        "wrong_topic_count": len(topics),
        "exercises": exercises[:exercise_limit],
        "exercise_count": len(exercises),
    }


def highest_content_level():
    """The highest level the product has a published course for, or ``None``.

    Used to say honestly whether a learner's target level is something this product can
    actually take them to.
    """
    course = (
        Lesson.objects.filter(is_published=True, course__is_published=True)
        .select_related("course__language_level")
        .order_by("-course__language_level__order")
        .first()
    )

    if course is None:
        return None
    return course.course.language_level


def goal_of(profile):
    """The learner's stated goal, or ``None`` when they have not set one.

    ``None`` rather than a filled-in default, because "no goal" and "a goal with no date"
    are different situations and the pages say different things about them.
    """
    if profile is None:
        return None

    if (
        profile.current_level is None
        and profile.target_level is None
        and profile.target_date is None
        and not profile.reason
    ):
        return None

    content_level = highest_content_level()

    covers_target = False
    if profile.target_level is not None and content_level is not None:
        if profile.target_level.order <= content_level.order:
            covers_target = True

    return {
        "reason": profile.reason,
        "reason_label": profile.reason_label,
        "current_level": profile.current_level,
        "target_level": profile.target_level,
        "target_date": profile.target_date,
        "content_level": content_level,
        "covers_target": covers_target,
    }


def learning_pace(course_stats, goal, today):
    """How much has to be done each week to finish the course by the target date.

    The arithmetic is deliberately the kind you can redo on paper::

        weeks left       = ceil((target_date - today) / 7)
        lessons per week = ceil(remaining lessons / weeks left)
        minutes per week = ceil(remaining minutes / weeks left)

    Rounding **up** in both places, so the suggestion is enough rather than optimistic.

    Returns ``None`` when there is no target date, because inventing one would mean
    inventing the plan. A date that has already passed is reported as ``"passed"`` rather
    than divided by zero, and a learner who has finished the course gets ``"done"``.

    What this cannot say: the pace is about finishing **this course**. If the target level
    is above the content that exists, the extra lessons are not in the number — the
    readiness page says so separately (``goal_of`` reports ``covers_target``).
    """
    if goal is None:
        return None

    if goal["target_date"] is None:
        return None

    days_left = (goal["target_date"] - today).days

    if days_left <= 0:
        return {
            "state": "passed",
            "days_left": days_left,
            "weeks_left": 0,
            "remaining_lessons": course_stats["remaining"],
            "lessons_per_week": 0,
            "minutes_per_week": 0,
        }

    weeks_left = math.ceil(days_left / 7)

    if course_stats["remaining"] == 0:
        return {
            "state": "done",
            "days_left": days_left,
            "weeks_left": weeks_left,
            "remaining_lessons": 0,
            "lessons_per_week": 0,
            "minutes_per_week": 0,
        }

    return {
        "state": "planned",
        "days_left": days_left,
        "weeks_left": weeks_left,
        "remaining_lessons": course_stats["remaining"],
        "lessons_per_week": math.ceil(course_stats["remaining"] / weeks_left),
        "minutes_per_week": math.ceil(course_stats["minutes_remaining"] / weeks_left),
    }


def readiness(user, today=None):
    """Everything the «آمادگی من» page shows, in one call.

    ``user`` must be signed in: a visitor we cannot identify has no rows to read, and the
    view is responsible for not calling this for one.

    ``today`` is injectable so the deadline arithmetic can be tested without waiting for
    a calendar; it defaults to today in the project's timezone.

    ``weak_word_count`` comes from ``vocabulary/review.py`` rather than being counted
    again here, so "a word to review" has exactly one definition in the product.
    """
    if today is None:
        today = timezone.localdate()

    course_stats = course_progress(user)
    exercise_stats = exercise_progress(user)
    vocabulary_stats = vocabulary_progress(user)
    grammar_stats = grammar_progress(user)

    profile = UserProfile.objects.filter(user=user).first()
    goal = goal_of(profile)

    pace = learning_pace(course_stats, goal, today)

    weak_grammar = missed_grammar(user)
    for topic in weak_grammar:
        practice_rows = grammar_practice([topic])
        if practice_rows:
            topic["practice_exercise"] = practice_rows[0]["exercise"]
        else:
            topic["practice_exercise"] = None

    return {
        "course": course_stats,
        "exercises": exercise_stats,
        "vocabulary": vocabulary_stats,
        "grammar": grammar_stats,
        "coverage": word_coverage(),
        "grammar_coverage": grammar_coverage(),
        "goal": goal,
        "pace": pace,
        "weak_word_count": missed_words(user).count(),
        "weak_grammar_topics": weak_grammar[:3],
        "weak_grammar_count": len(weak_grammar),
    }
