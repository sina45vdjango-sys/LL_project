"""Turning a submitted answer into a verdict.

The exercise page used to decide this in the browser: the correct option carried a
``data-correct`` attribute and a hidden block held the expected answer. Anyone who
opened the page source could read the answers, and the verdict was only as trustworthy
as the page. Now the verdict is decided here, from the real ``Answer`` rows, and the
browser is told the result.

``exercises/runner.py`` says what to show; this module says what counts as correct.

Comparing a typed answer follows the rule the browser used before, so the answers that
passed then still pass:

* surrounding whitespace is ignored, and a run of whitespace counts as one space,
* trailing punctuation is ignored, so ``gute Nacht!`` matches ``gute Nacht``,
* case is ignored.

An expected answer has to match as a whole answer, not as a fragment of one. That is
deliberately forgiving rather than clever: every live ``Answer`` row uses the EXACT
match type, so nothing here stretches to CONTAINS or ANY_OF.
"""

import re

#: Punctuation a learner may reasonably add at the end of an otherwise correct answer.
TRAILING_PUNCTUATION = re.compile(r"[.!?,;:،؛«»\"']+$")

#: ``ExerciseAttempt.response_text`` is a CharField of this length; a typed answer is
#: cut to fit rather than rejected.
MAX_RESPONSE_LENGTH = 500


def normalize(text):
    """One canonical form, for comparing a typed answer with an expected one."""
    # A run of whitespace (spaces, tabs, newlines) counts as a single space.
    collapsed = " ".join(str(text).split())

    # Drop punctuation the learner may have added at the end, then compare lower case.
    without_punctuation = TRAILING_PUNCTUATION.sub("", collapsed)

    return without_punctuation.lower()


def grade(question, answer_id, response_text):
    """The verdict for one submission of one question.

    Returns a dict with the verdict, the row the attempt is stored with, the option
    the page should flag as correct, and the answers it should show. Returns ``None``
    when the submission cannot be judged at all — either nothing was ever authored as
    correct, or ``answer_id`` is not an option of this question. A verdict is never
    invented for those.
    """
    answers = list(question.answers.all())

    # The answers the learner should have given. There is normally one, but the field
    # allows several, so collect them all.
    correct_answers = []
    for answer in answers:
        if answer.is_correct:
            correct_answers.append(answer)

    if not correct_answers:
        return None

    chosen = None

    if answer_id is not None:
        # The learner picked an option, so the verdict is that row's own is_correct.
        for answer in answers:
            if answer.pk == answer_id:
                chosen = answer
                break

        if chosen is None:
            return None

        is_correct = chosen.is_correct
        typed = ""
    else:
        # What the learner actually typed is what gets stored; `normalize` is only
        # used for the comparison.
        typed = str(response_text or "").strip()[:MAX_RESPONSE_LENGTH]

        is_correct = False
        for answer in correct_answers:
            if normalize(answer.text) == normalize(typed):
                is_correct = True
                break

    return {
        "is_correct": is_correct,
        "answer": chosen,
        "response_text": typed,
        "correct_answer_id": correct_answers[0].pk,
        "expected": [answer.text for answer in correct_answers],
    }
