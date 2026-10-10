"""A nudge for a question the learner keeps missing.

Nothing here is shown to a learner who has never answered the question wrong: a hint
arrives only after the mistake has really happened, which is the whole point. The
``ExerciseAttempt`` rows already say how many times a question was missed, so this module
only has to turn that count into words — and it never turns it into the answer.

That last part is the rule the project lives by (``exercises/runner.py`` and
``exercises/grading.py``): the correct answer is deliberately not in the page. A hint that
spelled the answer out would be that same leak through a different door, so every hint
hides something on purpose:

* a **typed** answer is shown as a pattern — the first and last letter, the rest as blanks
  (``H _ _ _ o``) — and a stronger hint shows every second letter (``H _ l _ o``);
* a **choice** question names one option that is wrong, and, when that is not enough,
  shows the same pattern for the correct option, so the learner still has to find it;
* a **scramble** tells the learner which word the sentence starts with.

The strength is chosen from the number of times the question has already been missed, so
the help grows with the difficulty rather than appearing all at once. The caller passes
that count in — the hint does not read the database itself, which keeps this module a pure
function and lets a test hand it a number directly.
"""

from exercises.runner import CHOICE, ORDER

#: How many wrong attempts earn each strength. One miss is a slip and is worth a gentle
#: nudge; a second miss means the question is genuinely hard, so it gets more help.
WEAK_FROM = 1
STRONG_FROM = 2


def hint_strength(wrong_count):
    """How strong a hint a question has earned, from the times it was missed.

    ``0`` means no hint at all — the learner has not missed it yet.
    """
    if wrong_count < WEAK_FROM:
        return 0
    if wrong_count < STRONG_FROM:
        return 1
    return 2


def correct_answer_text(question):
    """The first correct ``Answer`` text of a question, or an empty string."""
    for answer in question.answers.all():
        if answer.is_correct:
            return answer.text
    return ""


def wrong_answer_text(question):
    """The first incorrect ``Answer`` text of a question, or an empty string."""
    for answer in question.answers.all():
        if not answer.is_correct:
            return answer.text
    return ""


def masked_word(word, level):
    """One word as a pattern: some letters shown, the rest as blanks.

    Level 1 keeps the first and last letter (``H _ _ _ o``); level 2 keeps every second
    letter as well (``H _ l _ o``). Punctuation and digits are always shown, because they
    are not what the learner is being asked to remember.
    """
    letters = list(word)
    last = len(letters) - 1

    shown = []
    for index, letter in enumerate(letters):
        if not letter.isalpha():
            shown.append(letter)
        elif level == 1:
            if index == 0 or index == last:
                shown.append(letter)
            else:
                shown.append("_")
        elif index % 2 == 0:
            shown.append(letter)
        else:
            shown.append("_")

    # Join one by one so the blanks read as separate characters rather than as one run.
    return " ".join(shown)


def masked_text(text, level):
    """Every word of ``text`` as a pattern, words kept apart."""
    parts = []
    for word in text.split():
        parts.append(masked_word(word, level))
    return " ".join(parts)


def hint_for(question, kind, strength):
    """The hint a question has earned at this ``strength``, or an empty string.

    ``kind`` is the runner's own name for how the question is answered, so a choice
    question gets a choice hint and a typed one gets a pattern. That is the one place the
    kinds differ; the masking underneath is shared.
    """
    if strength < WEAK_FROM:
        return ""

    correct = correct_answer_text(question)

    if not correct:
        return ""

    if kind == CHOICE:
        if strength == 1:
            wrong = wrong_answer_text(question)
            if not wrong:
                return ""
            return f"یکی از گزینه‌ها نادرست است: «{wrong}»"
        return f"گزینهٔ درست این شکل است: {masked_text(correct, 2)}"

    if kind == ORDER:
        words = correct.split()
        if not words:
            return ""
        if strength == 1:
            return f"جمله با واژهٔ «{words[0]}» شروع می‌شود."
        return f"جمله با «{' '.join(words[:2])}» شروع می‌شود."

    # A typed answer: a pattern, never the whole word.
    if strength == 1:
        return f"پاسخ {len(correct)} حرف دارد: {masked_text(correct, 1)}"
    return f"پاسخ این شکل است: {masked_text(correct, 2)}"
