"""When each word comes back — the adaptive schedule behind today's review.

Every exercise submission already moves ``WordProgress``: how often the word was
answered right, how often wrong, and when it was last touched. This module turns those
facts into the one thing a review needs — *when the word should come back*.

The first version of this file used a fixed ladder (``[1, 3, 7, 16, 35]`` days): answer
correctly, climb one rung; answer wrong, fall to the bottom. It worked, but it ignored
everything the attempt rows already knew — how fast the answer came, how often the word
had been failed, whether the learner was recovering. This is the replacement: a small,
explainable spaced-repetition schedule inspired by the ideas behind Anki, not a copy of
its internals.

**State.** A word moves through four states: ``NEW`` (never answered), ``LEARNING``
(being learned; intervals are still short), ``REVIEW`` (graduated — its interval is at
least ``GRADUATION_DAYS``), and ``RELEARNING`` (was in review, then answered wrong). The
states are the queue tiers the dashboard and review page care about.

**The interval.** A correct answer grows the interval by the word's *ease* — the
multiplier that says how easily this word is recalled. ``interval = round(interval ×
ease)``, with a small nudge for a fast or slow answer, then clamped to
``MAX_INTERVAL_DAYS``. A wrong answer always makes the word due **tomorrow** (this is a
daily study product, not an in-session drill), moves it into ``RELEARNING`` if it had
graduated, and lowers its ease.

**The ease.** Starts at ``DEFAULT_EASE`` and drifts within ``[MIN_EASE, MAX_EASE]``:
a fast correct answer raises it, a slow one lowers it a little, a wrong one lowers it
more, and a fast *wrong* answer (a confident mistake) lowers it most. Because it is
bounded and its steps are small, one unusual answer cannot destroy a word's progress and
one lucky fast answer cannot make it vanish for months.

**Response time.** ``FAST_SECONDS`` and ``SLOW_SECONDS`` are read from the response
times this project has actually recorded (median ≈ 4s, upper quarter ≈ 9s), and are set
generously so thinking carefully is never a punishment: a correct answer after twelve
seconds is still correct, it just grows the interval a little less. When no time was
recorded the answer counts as normal.

The old ``review_step`` column is gone: a word's position is now ``interval_days`` plus
its ``state``, and this module is the only thing that writes either of them
(``vocabulary/progress.py`` calls ``next_review`` on the submission that moves the
counters). Nothing here writes to the database.
"""

from datetime import timedelta

from django.utils import timezone

from exercises.eligibility import eligible_lesson_ids

from .models import Word, WordProgress

#: The ease a word starts with, and the bounds it can never leave.
DEFAULT_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 2.8

#: The longest gap the schedule will ever ask for. Beyond this a word is effectively
#: known; asking again is cheap, so there is no reason to schedule it further out.
MAX_INTERVAL_DAYS = 180

#: A word whose interval reaches this many days has graduated from LEARNING to REVIEW.
GRADUATION_DAYS = 21

#: Response-time boundaries, in seconds. Chosen from the project's own recorded times
#: (median ≈ 4s, p75 ≈ 9s) and deliberately generous, so careful thinking is not punished.
FAST_SECONDS = 3.0
SLOW_SECONDS = 12.0

#: How many due words one *sitting* hands over, and how many brand-new words the review
#: page lists. The numbers are deliberately modest: a review that cannot be finished is a
#: wall, and a learner with a thousand learned words must not be handed a thousand of them.
#: So the day's review step is one sitting, and ``due_left_count`` says how much is waiting
#: for tomorrow instead of opening everything that is due.
SITTING_SIZE = 15
NEW_LIMIT = 10


def speed_bucket(response_time):
    """``"fast"``, ``"slow"``, ``"normal"`` or ``None`` for one response time in seconds.

    ``None`` means the page did not report a time (or reported an unusable one), which
    counts as normal rather than as either extreme.
    """
    if response_time is None:
        return None
    if response_time <= FAST_SECONDS:
        return "fast"
    if response_time >= SLOW_SECONDS:
        return "slow"
    return "normal"


def _bounded_ease(ease):
    """Keep an ease value inside ``[MIN_EASE, MAX_EASE]``."""
    if ease < MIN_EASE:
        return MIN_EASE
    if ease > MAX_EASE:
        return MAX_EASE
    return ease


def ease_after_correct(ease, speed):
    """The ease after a correct answer: up a little, more if the recall was fast."""
    if speed == "fast":
        ease = ease + 0.10
    elif speed == "slow":
        ease = ease - 0.05
    else:
        ease = ease + 0.03
    return _bounded_ease(ease)


def ease_after_wrong(ease, speed):
    """The ease after a wrong answer: down, most when the mistake was fast and confident."""
    if speed == "fast":
        ease = ease - 0.25
    elif speed == "slow":
        ease = ease - 0.15
    else:
        ease = ease - 0.20
    return _bounded_ease(ease)


def next_review(state, interval_days, ease, is_correct, response_time, now):
    """The word's state, interval, ease and due time after one answer.

    Pure: the caller passes the current values in and stores the result. Returns a dict of
    ``{"state", "interval_days", "ease", "due_at"}``.
    """
    speed = speed_bucket(response_time)

    if is_correct:
        ease = ease_after_correct(ease, speed)

        if interval_days < 1:
            # A word never scheduled yet (or one whose interval was lost): come back tomorrow.
            interval_days = 1
        else:
            factor = ease
            if speed == "fast":
                factor = factor + 0.10
            elif speed == "slow":
                factor = factor - 0.10

            grown = int(interval_days * factor + 0.5)
            # Never stand still: a correct answer must move the word at least one day out.
            if grown <= interval_days:
                grown = interval_days + 1
            interval_days = grown

        if interval_days > MAX_INTERVAL_DAYS:
            interval_days = MAX_INTERVAL_DAYS

        if interval_days >= GRADUATION_DAYS:
            state = WordProgress.State.REVIEW
        else:
            state = WordProgress.State.LEARNING
    else:
        ease = ease_after_wrong(ease, speed)
        interval_days = 1

        if state == WordProgress.State.REVIEW:
            state = WordProgress.State.RELEARNING
        else:
            state = WordProgress.State.LEARNING

    due_at = now + timedelta(days=interval_days)
    return {
        "state": state,
        "interval_days": interval_days,
        "ease": ease,
        "due_at": due_at,
    }


def due_words(user, now=None, limit=None):
    """The learner's tracked words whose review time has arrived, most overdue first.

    Only a row with a recorded due time can be due. Every answer records one from now on
    (``vocabulary/progress.py``), so this covers the words the learner has really
    practised. ``limit`` caps the list; ``None`` means no cap.
    """
    if now is None:
        now = timezone.now()

    rows = list(
        WordProgress.objects.filter(
            user=user,
            word__is_published=True,
            due_at__lte=now,
        )
        .select_related("word", "word__level")
        .order_by("due_at", "-wrong_count")
    )

    if limit is not None:
        rows = rows[:limit]
    return rows


def new_words(user, limit=None, lesson_ids=None):
    """Eligible published words the learner has reached but never been tested on.

    A word can only be "new" once the learner has actually reached the lesson that teaches
    it (``exercises/eligibility.py``), so the schedule never introduces vocabulary nobody
    has taught. Ordered by lesson, so new words arrive in the order the course teaches them.

    ``lesson_ids`` is the caller's own ``eligible_lesson_ids`` when it already has them —
    the review plan and the review queue ask the same question on one page.
    """
    if not user.is_authenticated:
        return []

    if lesson_ids is None:
        lesson_ids = eligible_lesson_ids(user)
    if not lesson_ids:
        return []

    practised = set(
        WordProgress.objects.filter(user=user).values_list("word_id", flat=True)
    )

    # ``level`` is joined because the review page's new-word block shows each word's level:
    # without it that is one query per row, and the block exists to list up to ``NEW_LIMIT``
    # of them.
    rows = (
        Word.objects.filter(is_published=True, lesson_links__lesson_id__in=lesson_ids)
        .exclude(pk__in=practised)
        .select_related("level")
        .distinct()
        .order_by("lesson_links__lesson__order", "lesson_links__order", "pk")
    )

    if limit is not None:
        rows = rows[:limit]
    return list(rows)


def review_queue(user, now=None, review_limit=None, new_limit=None, lesson_ids=None):
    """The learner's review queue, already ordered, in the tiers a sitting cares about.

    * ``overdue``  — due before today, oldest first
    * ``due``      — one **sitting**: every tracked word that is due now, ordered overdue →
      due today → relearning, capped at ``review_limit``
    * ``relearning`` — the subset of the due words that failed out of review
    * ``new``      — eligible words never practised, capped at ``new_limit``

    The cap is the point of this function, not a safety valve: a learner with two hundred
    words due must be handed a sitting they can actually finish, and told that the rest is
    still waiting. So the counts say all three things a page can honestly say about it —
    ``due_count`` how many words the sitting holds, ``due_left_count`` how many due words it
    does not (they stay in the queue and lead tomorrow's sitting), and ``overdue_count``
    how many of the whole group are already behind. This is the one place "what should be
    reviewed" is decided; the pages read it instead of asking ``WordProgress`` directly.

    ``lesson_ids`` is passed straight on to ``new_words`` — see there.
    """
    if now is None:
        now = timezone.now()
    if review_limit is None:
        review_limit = SITTING_SIZE
    if new_limit is None:
        new_limit = NEW_LIMIT

    today_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)

    overdue = []
    due_today = []
    relearning = []

    for row in due_words(user, now=now):
        if row.state == WordProgress.State.RELEARNING:
            relearning.append(row)
        elif row.due_at < today_start:
            overdue.append(row)
        else:
            due_today.append(row)

    # Everything that is due, in the order it should be met: what is already behind first,
    # then what came due today, then the words that fell out of review. One list, so the
    # sitting is simply its first ``review_limit`` words and the remainder is a count rather
    # than a second query.
    due_in_order = []
    for group in (overdue, due_today, relearning):
        for row in group:
            due_in_order.append(row)

    due = []
    for row in due_in_order:
        if len(due) >= review_limit:
            break
        due.append(row)

    fresh = new_words(user, new_limit, lesson_ids)

    return {
        "overdue": overdue,
        "due": due,
        "relearning": relearning,
        "new": fresh,
        "due_count": len(due),
        "due_left_count": len(due_in_order) - len(due),
        "overdue_count": len(overdue),
        "new_count": len(fresh),
    }
