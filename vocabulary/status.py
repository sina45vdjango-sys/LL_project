"""The one label a lesson vocabulary row is allowed to show.

A row already says what the word means, how it is pronounced and how it is inflected. The
label is the only thing on it that is about the *learner* rather than about the word, and
it answers one question — "where do I stand with this word?" — so a row shows at most one.
Showing all of them would turn a quiet list into a traffic light, and a label that is always
there stops meaning anything.

The order is the order of usefulness, and it is decided here and nowhere else:

    اشتباه پرتکرار    the learner keeps getting it wrong — the most worth acting on
    وقت مرور          it is due for review now (``vocabulary/schedule.py`` owns the dates)
    مهم برای آزمون    the exam asks the learner to produce this form (``Word.is_exam_important``)
    جدید             this lesson introduces it
    مرور             this lesson revisits it

The first three need the learner's own rows, so a visitor we cannot identify sees only the
last two. That is the honest answer rather than a missing one: they have no stored answers,
so there is no schedule and no mistake to report.

The template reads the words from here, and the row's CSS class comes from the same key, so
a state is spelled once. Nothing here writes to the database.
"""

from lessons.models import LessonWord

from .models import WordProgress

#: How many wrong answers make a word repeatedly wrong rather than once missed. The same
#: number the finish step of a lesson uses when it names the words to practise again.
MISTAKE_LIMIT = 2

#: The label for each state. The keys are the state names the CSS classes use too.
STATUS_LABELS = {
    "wrong": "اشتباه پرتکرار",
    "due": "وقت مرور",
    "exam": "مهم برای آزمون",
    "new": "جدید",
    "review": "مرور",
}


def status_of(link, progress, now):
    """The one state this ``LessonWord`` earns, as a key of ``STATUS_LABELS``.

    ``progress`` is the learner's own ``WordProgress`` row for the word, or ``None``.
    """
    if progress is not None:
        if progress.wrong_count >= MISTAKE_LIMIT:
            return "wrong"

        if progress.due_at is not None and progress.due_at <= now:
            return "due"

    if link.word.is_exam_important:
        return "exam"

    if link.role == LessonWord.Role.NEW:
        return "new"

    return "review"


def word_rows(page, user, now):
    """One row per word of a vocabulary page, ready for the template.

    Each row is ``{"word", "status", "label"}``. ``page`` is the ``Paginator`` page the
    vocabulary step is showing, so the page is the unit of work: a signed-in learner's
    counters are read in one query for all of the words on it, and a visitor we cannot
    identify is not queried for a lookup that could only come back empty.
    """
    links = list(page)

    progress_by_word = {}
    if user.is_authenticated:
        word_ids = []
        for link in links:
            word_ids.append(link.word_id)

        for progress in WordProgress.objects.filter(user=user, word_id__in=word_ids):
            progress_by_word[progress.word_id] = progress

    rows = []
    for link in links:
        if link.word_id in progress_by_word:
            progress = progress_by_word[link.word_id]
        else:
            progress = None

        status = status_of(link, progress, now)
        rows.append({"word": link.word, "status": status, "label": STATUS_LABELS[status]})

    return rows
