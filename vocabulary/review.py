"""What this learner should review — built from their own mistakes.

Every exercise submission already writes two facts: an ``ExerciseAttempt`` for the
answer, and a move on the ``WordProgress`` counters of the word the question tested
(``vocabulary/progress.py``). Those counters were readable — the word review page
reads them — but a list of words the learner got wrong is not yet a plan. It says
*what* was missed and never *where to practise it again*.

This module closes that gap, and it does it without a single new field: the words
come from ``WordProgress``, and the practice comes from the ``QuestionTarget`` rows
that already say which word each question tests. So "review" means doing the real
exercises that test your own weak words, not reading a list about them.

The one rule worth keeping in mind is the same one ``vocabulary/progress.py`` states:
only the ``TESTED_ITEM`` target counts. A word that merely appears in a question is
not a word the learner was tested on, so it cannot be a word they failed.

Three pages need this and they must not disagree about it: the word review page and
the dashboard's personal panel both call ``review_plan`` here, and a lesson's finish
step calls ``lesson_mistakes`` for the same answer narrowed to one lesson.
"""

from exercises.eligibility import eligible_lesson_ids
from exercises.models import ExerciseAttempt, QuestionTarget

from .models import WordProgress


def missed_words(user):
    """The words this learner has answered wrong, worst first.

    A word is listed because they really did answer it wrong at least once; a word
    they have always answered correctly is not a word to review. ``correct_count`` is
    the second sort key on purpose: between two words missed the same number of times,
    the one they have answered right least often is the harder one.
    """
    return (
        WordProgress.objects.filter(
            user=user,
            wrong_count__gt=0,
            word__is_published=True,
        )
        .select_related("word", "word__level")
        .order_by("-wrong_count", "correct_count", "-last_wrong_at")
    )


def lesson_mistakes(user, lesson):
    """The words of one lesson this learner has answered wrong, worst first.

    ``missed_words`` answers a level-wide question, which is the right answer for the
    review page and the dashboard but the wrong one at the end of a lesson: there the
    learner wants to hear about the lesson they just finished. The lesson's own
    ``LessonWord`` links are what narrows it — a word counts when this lesson teaches
    it or revisits it — so what a missed word *is* still has exactly one definition.

    Empty in the two cases the finish step shows no block for: a visitor we cannot
    identify, who has no stored answers at all, and a learner who got every word of
    this lesson right.
    """
    if not user.is_authenticated:
        return []

    return list(missed_words(user).filter(word__lesson_links__lesson=lesson))


def exercises_for_words(words, user=None, avoid_type=None, lesson_ids=None):
    """The published exercises that test any of ``words``, best first.

    Each row is ``{"exercise", "words", "question_count"}`` where ``words`` are the
    given words this exercise tests and ``question_count`` is how many of its
    questions do that. "Best" means the exercise covering the most of the learner's
    own mistakes, then the usual lesson order, so the first recommendation is the one
    that practises the most of what they got wrong.

    Visibility follows the product's one rule: a draft exercise, a draft lesson or a
draft course contributes nothing.

    When ``user`` is given, the exercises are also limited to the lessons that learner
    has reached (``exercises/eligibility.py``), so practice never builds itself out of a
    lesson nobody has taught them yet. ``None`` means no such limit — the caller is not
    asking for one learner's pool.

    ``avoid_type`` is an ``Exercise.type`` to push to the end. The scheduler decides
    *what* to review; this lets the caller stop the *format* repeating — after a meaning
    drill, a second meaning drill is the least useful way to ask the same word again, so
    a different type moves ahead of it when one is available.

    ``lesson_ids`` is the caller's own ``eligible_lesson_ids`` when it already has them, so
    a page that built the review plan and the review queue both does not ask
    ``exercises/eligibility.py`` the same question twice.
    """
    word_ids = []
    for word in words:
        word_ids.append(word.pk)

    if not word_ids:
        return []

    targets = QuestionTarget.objects.filter(
        role=QuestionTarget.Role.TESTED_ITEM,
        word_id__in=word_ids,
        question__exercise__is_published=True,
        question__exercise__lesson__is_published=True,
        question__exercise__lesson__course__is_published=True,
    )

    if user is not None:
        if lesson_ids is None:
            lesson_ids = eligible_lesson_ids(user)

        targets = targets.filter(
            question__exercise__lesson_id__in=lesson_ids
        )

    targets = targets.select_related("word", "question__exercise__lesson").order_by(
        "question__exercise__lesson__order",
        "question__exercise__order",
        "question__order",
    )

    rows = []
    by_exercise = {}

    for target in targets:
        exercise = target.question.exercise

        if exercise.pk not in by_exercise:
            row = {
                "exercise": exercise,
                "words": [],
                "question_count": 0,
            }
            by_exercise[exercise.pk] = row
            rows.append(row)

        row = by_exercise[exercise.pk]

        # One exercise can ask several questions about the same word, and the word
        # should be named once in its list.
        if target.word not in row["words"]:
            row["words"].append(target.word)

        row["question_count"] += 1

    rows.sort(
        key=lambda row: (
            row["exercise"].type == avoid_type,
            -len(row["words"]),
            row["exercise"].lesson.order,
            row["exercise"].order,
        )
    )
    return rows


def last_used_type(user):
    """The ``Exercise.type`` of this learner's most recent answer, or ``None``.

    Nothing new is stored for this: the newest ``ExerciseAttempt`` already says which
    format the learner just practised, and passing it to ``exercises_for_words`` as
    ``avoid_type`` is what keeps a review session from asking the same way twice in a row.
    """
    attempt = (
        ExerciseAttempt.objects.filter(user=user)
        .select_related("exercise")
        .order_by("-created_at", "-pk")
        .first()
    )

    if attempt is None:
        return None
    return attempt.exercise.type


def review_plan(user, word_limit=None, exercise_limit=3, lesson_ids=None):
    """The learner's mistakes and the exercises that practise them.

    Returns ``None`` for a visitor we cannot identify, so a page can tell "no account"
    apart from "an account with nothing to review yet" — they need different words.

    Otherwise:

    * ``words``             — ``WordProgress`` rows worst-first, at most ``word_limit``
      of them when a caller only wants a summary
    * ``wrong_word_count``  — how many there really are, whatever the limit
    * ``exercises``         — the exercises that practise them, best first, at most
      ``exercise_limit``
    * ``exercise_count``    — how many there really are, whatever the limit
    * ``exercises_by_word`` — ``{word id: [Exercise, ...]}``, so a word's own row can
      link to where it can be practised

    ``exercises_by_word`` is built from **every** missed word rather than from the
    limited ``words`` list, because a word shown in a summary deserves its own link
    even when the exercise it belongs to is not one of the top recommendations.

    ``lesson_ids`` is passed straight on to ``exercises_for_words`` for the reason given
    there: the page that builds this plan usually knows the learner's eligible lessons
    already.
    """
    if not user.is_authenticated:
        return None

    rows = list(missed_words(user))

    if not rows:
        return None

    all_words = []
    for row in rows:
        all_words.append(row.word)

    exercises = exercises_for_words(all_words, user, lesson_ids=lesson_ids)

    exercises_by_word = {}
    for row in exercises:
        for word in row["words"]:
            if word.pk not in exercises_by_word:
                exercises_by_word[word.pk] = []
            exercises_by_word[word.pk].append(row["exercise"])

    if word_limit is None:
        shown_words = rows
    else:
        shown_words = rows[:word_limit]

    return {
        "words": shown_words,
        "wrong_word_count": len(rows),
        "exercises": exercises[:exercise_limit],
        "exercise_count": len(exercises),
        "exercises_by_word": exercises_by_word,
    }
