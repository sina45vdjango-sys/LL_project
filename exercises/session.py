"""Today's practice as one bounded, non-repeating session.

The problem this solves is the one the owner wrote down: a lesson's exercises are a
wall. Lesson 1 publishes 31 exercises and 183 questions, and the 39 words behind them
are asked three to five times each — once as a meaning, once as a spelling, once as an
article, once as a dictation. The exercise list is honest about that size, which is
exactly the problem: it tells a learner who wanted ten minutes of practice that there
are 183 questions waiting.

So a session is *composed* instead of a list being shown, and four rules are what make
it a session rather than a shorter list:

* **Bounded.** ``SESSION_SIZE`` questions at most, so the learner never meets the whole
  lesson in one sitting.
* **No repetition.** At most one question per thing asked about — a word, or a sentence
  — so ``der Abend`` is asked once even though five drills ask about it.
* **Mixed.** The kind of question varies from one to the next instead of all fifteen
  being meaning questions, by choosing, for each topic, a drill whose kind differs from
  the one just asked.
* **Daily.** A topic already practised today is left out, so the session moves on instead
  of replaying this morning's cards, and once a lesson has nothing left today the session
  is empty and the page says so.

The day reads this module too. «امروز» shows a practice step, and its size and whether it
is finished have to be the fact the session page itself acts on — so ``session_progress``
answers both from the rules above rather than the day counting nodes of its own. That is
also what makes the day *finishable*: a sitting is bounded, so one sitting's worth of
topics behind the learner ends the step, while the page stays open afterwards for anyone
who wants to keep practising.

Nothing here is authored and nothing here is written to the database. Every question is
a row that already exists and is already published, and the page records answers through
the ordinary ``ExerciseSubmitView``, so grading, XP and the word-review schedule keep
working without this module knowing anything about them.
"""

from exercises.models import Exercise, ExerciseAttempt, Question
from lessons.models import Lesson
from lessons.today import lesson_to_work_on

#: How many questions one session holds. The owner's rule is a ceiling of roughly ten to
#: twenty; fifteen is the middle of that and one screen of the runner's progress bar.
SESSION_SIZE = 15

#: A scramble is answered by writing a sentence, and a session has no word bank to show,
#: so a scramble would arrive as a bare typed question. ``exams/paper.py`` leaves them out
#: of a paper for the same reason; a session does too rather than render one wrong.
SKIPPED_TYPES = (Exercise.ExerciseType.SCRAMBLE,)


def session_lesson(user):
    """The lesson today's session is drawn from, or ``None`` when there is none.

    A signed-in learner gets the lesson they are actually inside, so the session, the
    skill path and the dashboard all point at the same lesson. A visitor gets the first
    published lesson: the content is public and a session should not be the one page that
    asks for an account.
    """
    if user.is_authenticated:
        work = lesson_to_work_on(user)
        if work is None:
            return None
        return work["lesson"]

    return (
        Lesson.objects.filter(is_published=True, course__is_published=True)
        .order_by("course__language_level__order", "course__pk", "order", "pk")
        .first()
    )


def lesson_questions(lesson):
    """Every published question of a lesson, with its answers and targets loaded.

    The order is the lesson's own teaching order, so a session begins where the lesson
    begins. ``answers`` and ``targets`` are prefetched because the selection below reads
    both for every question; without it this walks two queries per question.
    """
    return list(
        Question.objects.filter(
            exercise__lesson=lesson,
            exercise__is_published=True,
        )
        .select_related("exercise")
        .prefetch_related("answers", "targets")
        .order_by("exercise__order", "order", "pk")
    )


def markable(question):
    """Whether this question has an authored correct answer at all.

    A question with none cannot be scored, and a session has only fifteen slots — one of
    them should not go to something the server can only answer "unchecked" to.
    """
    for answer in question.answers.all():
        if answer.is_correct:
            return True
    return False


def topic_of(question):
    """The one thing this question asks about, or ``None``.

    A word question is about its word; a reading or sentence question is about its
    sentence. Those are the two kinds of thing a question can be *about*, and two
    questions sharing one of them are the same question asked twice as far as a session
    is concerned.

    A word wins over a sentence: a grammar drill can carry both (the word it asks about
    and the sentence it uses), and it is the word the learner is being tested on. A
    question carrying neither — a grammar question tagged only with a rule — has no topic
    and so never collides with another.
    """
    word = None
    sentence = None

    for target in question.targets.all():
        if target.word_id and word is None:
            word = target.word_id
        if target.sentence_id and sentence is None:
            sentence = target.sentence_id

    if word is not None:
        return ("word", word)
    if sentence is not None:
        return ("sentence", sentence)
    return None


def answered_today_ids(user, today, questions):
    """Which of ``questions`` this learner already answered today, as a set of ids.

    ``today`` is a date in the project's own timezone, compared against ``created_at``'s
    date, so a late-evening answer in Tehran counts as today — the same rule
    ``lessons/today.py::exercises_done_today`` follows.
    """
    ids = set()

    if not user.is_authenticated:
        return ids

    question_ids = []
    for question in questions:
        question_ids.append(question.pk)

    rows = ExerciseAttempt.objects.filter(
        user=user,
        created_at__date=today,
        question_id__in=question_ids,
    ).values_list("question_id", flat=True)

    for question_id in rows:
        ids.add(question_id)

    return ids


def topic_groups(questions):
    """The lesson's questions gathered by what they ask about, in lesson order.

    Each group is ``{"topic": key or None, "questions": [...]}``. Everything about one
    word lands in one group, which is what lets the session ask only one of them. A
    question with no topic (a grammar question tagged only with a rule) gets a group of
    its own, so it can never be deduplicated away.
    """
    groups = []

    for question in questions:
        topic = topic_of(question)

        if topic is None:
            groups.append({"topic": None, "questions": [question]})
            continue

        found = None
        for group in groups:
            if group["topic"] == topic:
                found = group
                break

        if found is None:
            groups.append({"topic": topic, "questions": [question]})
        else:
            found["questions"].append(question)

    return groups


def usable_questions(group):
    """The questions of a topic this session is allowed to ask.

    Scrambles are dropped (see ``SKIPPED_TYPES``) and so is anything with no authored
    answer. What is left is the pool the session chooses one question from.
    """
    available = []

    for question in group["questions"]:
        if question.exercise.type in SKIPPED_TYPES:
            continue
        if not markable(question):
            continue
        available.append(question)

    return available


def topic_done_today(available, answered_ids):
    """Whether this topic was practised today at all, in any of its forms.

    Practised in *any* form, not only in the question that comes back: a word the learner
    already did today should not reappear a minute later as a different drill. This is
    also what makes a day's session finish — once every topic of the lesson has been done
    today, the session is empty and the page says so instead of serving new cards.
    """
    for question in available:
        if question.pk in answered_ids:
            return True
    return False


def choose_one(available, previous_type):
    """One question of a topic, preferring a kind different from the one just asked.

    A topic is usually asked by several exercises of different kinds — a meaning drill, a
    spelling drill, an article drill — and taking the one whose kind the session has not
    just used is what makes a session mixed instead of fifteen meaning questions in a
    row.
    """
    for question in available:
        if question.exercise.type != previous_type:
            return question

    return available[0]


def pick_questions(questions, answered_ids):
    """One question per topic, kinds varied, in the order the lesson teaches them.

    Walking in lesson order is what keeps the pick honest: the learner meets the lesson
    from its beginning rather than a random draw.
    """
    chosen = []
    previous_type = None

    for group in topic_groups(questions):
        available = usable_questions(group)
        if not available:
            continue
        if topic_done_today(available, answered_ids):
            continue
        if len(chosen) >= SESSION_SIZE:
            break

        question = choose_one(available, previous_type)
        chosen.append(question)
        previous_type = question.exercise.type

    return chosen


def session_progress(user, today, lesson):
    """Today's sitting for one lesson: whether it is done, and how big it is right now.

    «امروز» renders this as its practice step and «جلسهٔ امروز» *is* it, so the two must not
disagree about when practice is over. Both the verdict and the size are therefore
computed here, out of the same rules a session is built with, instead of the day counting
something of its own.

Done means one of two things, and both are facts this module already owns rather than a
target invented for a page:

* the lesson has nothing left to ask today, so ``pick_questions`` comes back empty; or
* a whole sitting's worth of topics is already behind the learner — a sitting is at most
  ``SESSION_SIZE`` questions, and each question is about a different topic, so that many
topics answered today is one sitting.

    ``size`` is the session the page would hand over right now, which is what the step
promises; it is never larger than ``SESSION_SIZE``. ``practised`` is how many of the
lesson's topics are already behind the learner today, which is the difference between "the
lesson has nothing to ask yet" and "you have answered everything it had":
``size`` and ``practised`` are both zero only when there is no material at all, and a day
must not show a practice step for that. A learner who wants to practise past the sitting
still can — the step being finished is the day's goal being met, not a lock.
    """
    questions = lesson_questions(lesson)
    answered_ids = answered_today_ids(user, today, questions)

    done_topics = 0
    for group in topic_groups(questions):
        available = usable_questions(group)
        if not available:
            continue
        if topic_done_today(available, answered_ids):
            done_topics = done_topics + 1

    left = pick_questions(questions, answered_ids)

    if not left:
        # Nothing left for today: the sitting is over, and it was exactly as long as it was.
        return {"done": True, "size": done_topics, "practised": done_topics}

    if done_topics >= SESSION_SIZE:
        # A full sitting behind the learner. The lesson has more to give, but the day's step
        # is what a sitting is, so it is finished.
        return {"done": True, "size": SESSION_SIZE, "practised": done_topics}

    return {"done": False, "size": len(left), "practised": done_topics}


def session_skills(questions):
    """The distinct kinds of exercise in a session, in first-appearance order.

    Only used to tell the page what the session is made of; it deliberately carries no
    counts, because the point of the page is the session, not a breakdown of it.
    """
    seen = set()
    labels = []

    for question in questions:
        key = question.exercise.type
        if key in seen:
            continue
        seen.add(key)
        labels.append(question.exercise.type_label)

    return labels


def build_session(user, today, lesson):
    """Everything the session page needs: the lesson, its questions, and the goal.

    ``today`` is a date in the project's timezone (``timezone.localdate()``) and
    ``lesson`` is the lesson today means, both passed in rather than worked out here, so
    a page and a test agree on which day and which lesson they are asking about — the
    same rule ``lessons/today.py`` and ``lessons/skill_path.py`` follow.

    A lesson with nothing left today returns an empty session rather than inventing a
    next step — "an honest empty is better than a decorated zero". The caller already
    holds ``lesson``, so it is not repeated in the result.
    """
    questions = lesson_questions(lesson)
    answered_ids = answered_today_ids(user, today, questions)

    session = pick_questions(questions, answered_ids)

    return {
        "questions": session,
        "goal": len(session),
        "skills": session_skills(session),
    }
