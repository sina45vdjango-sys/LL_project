"""How a learner's ``WordProgress`` counters move.

A word's counters only ever move on the one occasion the learner is actually tested on
that word: an exercise submission. Nothing else in the product claims to know whether a
word is known, so nothing else writes here.

The rule about *which* word that is matters more than it looks. A question points at
its words through ``QuestionTarget``, and only the ``TESTED_ITEM`` target is the word
being tested — the ``CONTEXT`` targets are the words that merely appear in the question.
Answering a question about ``bestellen`` correctly says nothing about the learner's
grasp of ``kaufen`` or ``Geld``, so those are left alone.
"""

from django.utils import timezone

from exercises.models import QuestionTarget

from .models import WordProgress


def tested_word(question):
    """The ``Word`` this question tests, or ``None`` when it does not test one.

    A question can test a word, a grammar topic or a sentence, so a missing word
    target is normal rather than an error.
    """
    target = (
        QuestionTarget.objects.filter(
            question=question,
            role=QuestionTarget.Role.TESTED_ITEM,
            word__isnull=False,
        )
        .select_related("word")
        .first()
    )

    if target is None:
        return None
    return target.word


def record_word_progress(user, question, is_correct):
    """Count one attempt on the word this question tests.

    Separate ``correct`` and ``wrong`` counters are kept (rather than only a total) so
    a later feature can ask "how often was this word missed?" without a migration.
    """
    word = tested_word(question)
    if word is None:
        return None

    now = timezone.now()
    progress, _ = WordProgress.objects.get_or_create(user=user, word=word)

    progress.attempt_count += 1
    progress.last_attempted_at = now
    if is_correct:
        progress.correct_count += 1
        progress.last_correct_at = now
    else:
        progress.wrong_count += 1
        progress.last_wrong_at = now

    progress.save()
    return progress
