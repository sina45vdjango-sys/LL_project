"""Today's practice, as a path of skill-typed nodes.

The problem this solves is the one the owner reported: a lesson's exercise list is a
wall — lesson 1 alone carries 31 exercises and roughly 183 questions, and the same word
is asked three or four times. A learner opening that page cannot tell what to do first
or when they are finished.

So the exercises are not shown as a list here. They are **grouped by the skill they
train**, one node per skill, and a node is a single exercise — a handful of questions,
finishable in a few minutes. Nothing new is authored: every node points at an
``Exercise`` row that already exists, so this module invents no content and writes
nothing.

Where a node's skill comes from, and why it is not guessed from the title:

* ``Exercise.type`` says what *shape* the exercise is (``LISTENING``, ``TRANSLATION``,
  …). That is the first signal and it covers most rows.
* Grammar is the exception. Article, plural and Perfekt drills are all
  ``MULTIPLE_CHOICE``, and they are the only thing in the product that teaches a rule,
  so a title prefix would be the only way to spot them — and titles are display copy
  that a translator may change. Instead the stored ``QuestionTarget`` row with role
  ``GRAMMAR`` is read: that is the product's own, already-written answer to "which rule
  does this question exercise?", and ``lessons/readiness.py`` counts grammar the same
  way. One query, no string matching.

The lesson's conversation (concepts 9 and 13) is not a skill node. It is one activity
about the whole lesson rather than a drill for one skill, so it gets one node of its own
at the end of the list, and pressing «واژگان» no longer opens it. Both pages still exist:
the node opens the teacher chat, which links on to the role-play.

Three nodes are not drills and are marked as such rather than pretending otherwise:

* **The conversation** and **speaking** are ``optional``. Neither can be graded here — the
  learner answers in their own words and nothing in this product marks that — so a node
  that could never be "done" must not sit inside a daily goal.
* **The test** is a ``milestone``. It is a full sitting, not a daily drill, so it is
  shown at the end of the path and kept out of the goal's arithmetic.

The daily goal is therefore the number of practice nodes that really exist for today's
lesson — not a fixed six. A lesson whose author never attached listening material simply
has no listening node, which is the same "an honest empty is better than a decorated
zero" rule the rest of the product follows.

Two more things this module owns, because both are about *which* node the learner meets:

* **What a node opens.** A practice node opens the graded exercise itself
  (``exercises:exercise-detail``). A learner who clicked «واژگان» must get the vocabulary
  drill, not a page about something else — so the exercise is the destination, and the
  label on the node and the content behind it are the same thing.
* **The order of the skills** (``order_skills``). That is concept 15, «تشخیصی تطبیقی»,
  which the design asks for as a *selection function* rather than a page: it reads the
  learner's own newest answers and moves the skills they are getting wrong up. Under a
  documented threshold it returns the lesson's own order instead, because there is
  nothing to be adaptive about yet.

And **the day itself** (``day_steps``), which is the third thing this module owns. There
used to be two answers to «امروز» — the dashboard's own lesson-and-practice list and the
guided day on «مسیر امروز» — and two answers to one question drift apart, so the learner
is left guessing which one is really today. ``today_board`` builds the day once and both
pages render it.
"""

from django.db.models import Count
from django.urls import reverse

from exercises.history import latest_attempts
from exercises.models import Exercise, QuestionTarget
from exercises.session import session_progress
from vocabulary.review import missed_words
from vocabulary.schedule import review_queue

from .models import LessonProgress, LessonSentence
from .today import exercises_done_today, lesson_to_work_on

#: Which skill an exercise's *shape* trains. ``MULTIPLE_CHOICE`` says vocabulary because
#: that is what almost all of them are; the grammar ones are lifted out separately by
#: ``grammar_exercise_ids`` below.
TYPE_SKILL = {
    Exercise.ExerciseType.MULTIPLE_CHOICE: "vocabulary",
    Exercise.ExerciseType.TRANSLATION: "writing",
    Exercise.ExerciseType.FILL_BLANK: "grammar",
    Exercise.ExerciseType.LISTENING: "listening",
    Exercise.ExerciseType.READING: "reading",
    Exercise.ExerciseType.TRUE_FALSE: "reading",
    Exercise.ExerciseType.SCRAMBLE: "writing",
    Exercise.ExerciseType.SPEAKING: "speaking",
    Exercise.ExerciseType.WRITING: "writing",
}

#: The shapes a grammar-tagged exercise can be and still be counted as grammar. A
#: listening drill that happens to exercise a rule stays a listening drill, because the
#: learner's ear is what it trains.
GRAMMAR_SHAPES = (
    Exercise.ExerciseType.MULTIPLE_CHOICE,
    Exercise.ExerciseType.FILL_BLANK,
)

#: The skills, in the order the path shows them: what the learner already half-knows
#: first, then the skills that need more attention. The label is what the page writes;
#: the hint says what the node is for.
SKILLS = (
    {
        "key": "vocabulary",
        "label": "واژگان",
        "hint": "معنی، آرتیکل و شکل درست واژه‌ها.",
    },
    {
        "key": "grammar",
        "label": "گرامر",
        "hint": "قاعده‌ای که این درس روی آن بنا شده است.",
    },
    {
        "key": "listening",
        "label": "شنیدن",
        "hint": "اول فقط گوش کن، بعد جواب بده.",
    },
    {
        "key": "reading",
        "label": "خواندن",
        "hint": "متن را بخوان و معنی‌اش را پیدا کن.",
    },
    {
        "key": "writing",
        "label": "نوشتن",
        "hint": "خودت بنویس — تایپ کردن، نه انتخاب گزینه.",
    },
)

#: What finishing a practice node is worth. The test's own number lives in
#: ``accounts/xp.py`` beside the rest of the reward table.
XP_PER_NODE = 20

#: How many answers a learner must have stored on today's lesson before the adaptive order
#: may disagree with the lesson's own order. Below it there is nothing to tell the skills
#: apart, and shuffling the nodes would be decoration rather than diagnosis
#: (DESIGN_ALL_SKILLS.md, «عیب ۶»: «تشخیصی در روزهای اول داده ندارد»).
MIN_ANSWERS = 20


def order_skills(user, exercises, grammar_ids):
    """The practice skills in the order this learner should meet them today (concept 15).

    This is «تشخیصی تطبیقی» as the design specifies it: a **selection function**, not a
    page. It changes nothing about what a node contains — only which skill comes first.

    The signal is the learner's own newest answer to each question
    (``exercises/history.py::latest_attempts``, the rule «آمادگی من» counts with too),
    restricted to today's lesson's exercises and counted per skill. A skill with more
    wrong answers moves up; a tie keeps the lesson's own order, so the result is stable
    and explainable.

    Under ``MIN_ANSWERS`` there is not enough stored to tell the skills apart, so the
    lesson's order comes back unchanged — the honest fallback the design asks for, and
    what every new learner gets.
    """
    baseline = []
    for skill in SKILLS:
        baseline.append(skill["key"])

    if not user.is_authenticated:
        return baseline

    by_exercise = {}
    for exercise in exercises:
        by_exercise[exercise.pk] = exercise

    answers = 0
    wrong_by_skill = {}

    for attempt in latest_attempts(user).values():
        if attempt.exercise_id not in by_exercise:
            continue

        answers += 1
        if attempt.is_correct:
            continue

        skill = skill_of(by_exercise[attempt.exercise_id], grammar_ids)
        if skill not in wrong_by_skill:
            wrong_by_skill[skill] = 0
        wrong_by_skill[skill] += 1

    if answers < MIN_ANSWERS:
        return baseline

    rows = []
    for position, key in enumerate(baseline):
        if key in wrong_by_skill:
            wrong = wrong_by_skill[key]
        else:
            wrong = 0
        rows.append({"key": key, "wrong": wrong, "position": position})

    rows.sort(key=lambda row: (-row["wrong"], row["position"]))

    ordered = []
    for row in rows:
        ordered.append(row["key"])
    return ordered


def grammar_exercise_ids(exercises):
    """The ids of ``exercises`` that exercise a grammar rule, in one query.

    Read from ``QuestionTarget`` rather than from a title, so renaming or translating a
    title cannot quietly move a drill from one skill to another.
    """
    ids = set()

    rows = QuestionTarget.objects.filter(
        role=QuestionTarget.Role.GRAMMAR,
        question__exercise__in=exercises,
    ).values_list("question__exercise_id", flat=True)

    for exercise_id in rows:
        ids.add(exercise_id)

    return ids


def skill_of(exercise, grammar_ids):
    """Which skill one exercise trains.

    Grammar is checked first because an article drill's *shape* is an ordinary
    multiple-choice question; its ``GRAMMAR`` target is the only thing that says
    otherwise.
    """
    if exercise.pk in grammar_ids and exercise.type in GRAMMAR_SHAPES:
        return "grammar"

    if exercise.type in TYPE_SKILL:
        return TYPE_SKILL[exercise.type]

    return "vocabulary"


def exercise_for_skill(rows, done_today):
    """The exercise of this skill to open today, or ``None`` if the skill has none.

    A row the learner has not answered today wins, so pressing the node again moves on
    instead of replaying the same card; ``lessons/today.py::exercises_done_today`` is what
    supplies the "answered today" set. When everything for that skill is already done today
    the first row comes back anyway, so the node still opens something.
    """
    for row in rows:
        if row.pk not in done_today:
            return row

    if rows:
        return rows[0]

    return None


def skill_practised_today(rows, done_today):
    """Whether *any* exercise of this skill was answered today.

    This is not the same question as "was the linked exercise answered", and getting it
    wrong is invisible until it matters: as soon as one exercise of a skill is done,
    ``exercise_for_skill`` moves the node's link on to the next one, so the linked row is
    by definition not the row that was answered. Reading ``done`` off that row alone would
    make a finished skill look untouched again the moment it was finished, and the day's
    goal could never fill up.
    """
    for row in rows:
        if row.pk in done_today:
            return True

    return False


def skill_nodes(lesson, user, today, exercises=None):
    """One lesson's practice as a node per skill, in the order this learner should meet them.

    Split out of ``build_path`` so the lesson journey can show the same map: the page that
    *teaches* a lesson should not hand the learner the exercise wall that this grouping
    exists to replace. ``exercises`` is accepted so a caller that has already read the
    lesson's exercises does not read them twice.
    """
    # The question count is annotated rather than counted per node: the dashboard builds this
    # path on every page load, and ``exercise.questions.count()`` once per node was five more
    # queries for a number a JOIN can hand over with the row.
    if exercises is None:
        exercises = list(
            Exercise.objects.filter(
                lesson=lesson,
                is_published=True,
            )
            .annotate(question_count=Count("questions"))
            .order_by("order", "pk")
        )

    grammar_ids = grammar_exercise_ids(exercises)

    rows_by_skill = {}
    for exercise in exercises:
        skill = skill_of(exercise, grammar_ids)
        if skill not in rows_by_skill:
            rows_by_skill[skill] = []
        rows_by_skill[skill].append(exercise)

    # A visitor has no stored answers, so nothing can have been done today — and asking
    # the database for one would look up an ``ExerciseAttempt`` by an AnonymousUser.
    if user.is_authenticated:
        done_today = exercises_done_today(user, today)
    else:
        done_today = set()

    skill_by_key = {}
    for skill in SKILLS:
        skill_by_key[skill["key"]] = skill

    nodes = []
    for key in order_skills(user, exercises, grammar_ids):
        skill = skill_by_key[key]

        if key in rows_by_skill:
            rows = rows_by_skill[key]
        else:
            rows = []

        exercise = exercise_for_skill(rows, done_today)

        if exercise is None:
            continue

        question_count = exercise.question_count

        nodes.append(
            {
                "key": skill["key"],
                "label": skill["label"],
                "hint": skill["hint"],
                "title": exercise.title,
                # The graded drill itself, so the label and the content agree.
                "url": reverse("exercises:exercise-detail", args=[exercise.pk]),
                "mode": "drill",
                "questions": question_count,
                "xp": XP_PER_NODE,
                # The skill, not the card: see ``skill_practised_today``.
                "done": skill_practised_today(rows, done_today),
                "optional": False,
                "milestone": False,
            }
        )

    return nodes


def assign_states(nodes):
    """Set every node's state: ``done``, ``now``, ``next`` or ``side``.

    ``now`` is the first unfinished node that is inside the day's goal and ``next`` is
    everything after it — never locked, because the path has no gates. ``side`` marks the
    optional and milestone nodes, which are shown but are not "the next thing" the learner
    must do. One definition, used by both the path and the lesson's practice step.
    """
    current_marked = False
    for node in nodes:
        if node["done"]:
            node["state"] = "done"
            continue
        if node["optional"] or node["milestone"]:
            node["state"] = "side"
            continue
        if current_marked:
            node["state"] = "next"
        else:
            node["state"] = "now"
            current_marked = True

    return nodes


def practice_tally(nodes):
    """How many nodes the goal counts, and how many of them are done.

    Optional and milestone nodes are left out on purpose: a conversation and a whole
    sitting cannot be honestly finished, so counting them would make the day unfinishable.
    """
    goal = 0
    done = 0
    for node in nodes:
        if node["optional"] or node["milestone"]:
            continue
        goal = goal + 1
        if node["done"]:
            done = done + 1

    return {"goal": goal, "done": done}


def lesson_practice(lesson, user, today):
    """One lesson's practice as the journey shows it: skill nodes, states and a tally.

    The lesson page and «مسیر امروز» must agree about what a lesson's practice is made of,
    so both read ``skill_nodes``; only the path adds the conversation, the speaking node
    and the milestone test, because those are about the learner's day rather than about
    one lesson's skills.
    """
    nodes = skill_nodes(lesson, user, today)
    assign_states(nodes)
    tally = practice_tally(nodes)

    return {"nodes": nodes, "goal": tally["goal"], "done": tally["done"]}


def finished_a_lesson(user):
    """Whether this learner has completed at least one lesson.

    «آزمون گام» measures the lessons a learner has studied, so it belongs to a day only
    once there is something to measure. On the first day there is not, and a test that
    cannot say anything is worse than no test: it is the one thing on the page that can
    only tell a new learner they know nothing yet. One fact, read by both «امروز» and the
    path's own map, so the two cannot disagree about whether the test is on today.
    """
    return LessonProgress.objects.filter(
        user=user,
        status=LessonProgress.Status.COMPLETED,
    ).exists()


def build_path(user, today, review=None, lessons=None, lesson_ids=None, rows=None):
    """Everything the practice path page shows, or ``None`` for a visitor.

    ``today`` is a date in the project's timezone (``timezone.localdate()``), passed in
    rather than read here so a page and a test agree on which day they are asking about —
    the same rule ``lessons/today.py`` follows.

    Returns a dict with the nodes in display order, today's goal, how much of it is done,
    and the lesson they belong to. The goal counts only the practice nodes that actually
    exist, so a lesson with no listening material does not promise a listening node.

    Two counts come along for the day to build its review step from: how many words the
    schedule says are due (``vocabulary/schedule.py``) and how many the learner has ever
    answered wrong (``vocabulary/review.py``).    ``review`` is a caller's own
    ``review_plan`` when it already built one — the dashboard builds it for its mistake
    panel — so the page does not pay for the same plan twice; every other caller gets the
    mistake count on its own, which is one ``COUNT``.

    ``lessons``, ``lesson_ids`` and ``rows`` are a caller's copies of the three facts this
    builds on — every published lesson, the ones this learner may practise, and their own
    progress rows — for the reason ``build_path`` and ``review_plan`` already take ``review``:
    «امروز» computes them all for its own sake and should not make this read them again.
    """
    if not user.is_authenticated:
        return None

    # The words whose review time has arrived, from the one module that decides it
    # (vocabulary/schedule.py). The day needs the count even when there is no lesson left,
    # because review is then the day's whole work rather than an afterthought.
    queue = review_queue(user, lesson_ids=lesson_ids)
    due_count = queue["due_count"]
    due_left_count = queue["due_left_count"]

    if review is not None:
        wrong_count = review["wrong_word_count"]
    else:
        wrong_count = missed_words(user).count()

    work = lesson_to_work_on(user, lessons, rows)

    # Whether the step test belongs to today at all. Read here rather than inside
    # ``day_steps`` so the day and the path's own map are told the same thing, and so one
    # page load asks the question once.
    test_ready = finished_a_lesson(user)

    if work is None:
        return {
            "lesson": None,
            "nodes": [],
            "goal": 0,
            "done": 0,
            "due_count": due_count,
            "due_left_count": due_left_count,
            "wrong_count": wrong_count,
            "session": None,
            "test_ready": test_ready,
        }

    lesson = work["lesson"]

    # Today's practice as one sitting, read from the module that composes sessions: the
    # day's practice step and «جلسهٔ امروز» must not disagree about when practice is
    # finished, and this is the only place that decides either
    # (exercises/session.py::session_progress).
    session = session_progress(user, today, lesson)

    exercises = list(
        Exercise.objects.filter(
            lesson=lesson,
            is_published=True,
        )
        .annotate(question_count=Count("questions"))
        .order_by("order", "pk")
    )

    nodes = skill_nodes(lesson, user, today, exercises)

    # The lesson's own conversation (concepts 9 and 13), as one node of its own. It is a
    # page about the whole lesson, so it cannot be attached to a single skill — which is
    # what it used to be, making five different labels open the same page. Optional for
    # the same reason speaking is: the learner's own line is graded nowhere and stored
    # nowhere, so the node can never be honestly called finished.
    dialogue_exists = LessonSentence.objects.filter(
        lesson=lesson,
        role=LessonSentence.Role.DIALOGUE,
        sentence__is_published=True,
    ).exists()

    if exercises and dialogue_exists:
        nodes.append(
            {
                "key": "conversation",
                "label": "گفت‌وگو",
                "hint": "دیالوگ همین درس را با معلم تمرین کن؛ جواب را خودت می‌نویسی و بعد خط درس را می‌بینی.",
                "title": "چتِ معلم",
                "url": reverse("exercises:exercise-chat", args=[exercises[0].pk]),
                "mode": "chat",
                "questions": 0,
                "xp": 0,
                "done": False,
                "optional": True,
                "milestone": False,
            }
        )

    # Speaking: the official rehearsal, not a drill. Optional and outside the goal,
    # because nothing here can tell whether the learner actually spoke.
    nodes.append(
        {
            "key": "speaking",
            "label": "گفتن",
            "hint": "صوت الگو را بشنو، خودت را ضبط کن و «گفتم» را بزن. بدون نمره.",
            "title": "بلند بگو",
            "url": reverse("exams:sprechen"),
            "mode": "speaking",
            "questions": 0,
            "xp": 0,
            "done": False,
            "optional": True,
            "milestone": False,
        }
    )

    # The milestone test closes the path — once there is something to be measured on. A test
    # measures the lessons a learner has studied, and on the first day that is none.
    if test_ready:
        nodes.append(
            {
                "key": "test",
                "label": "آزمون گام",
                "hint": "هر چند گره یک بار: یک ایستگاه کوتاه از هر مهارت، و می‌شود ردش کرد.",
                "title": "آزمون گام",
                "url": reverse("exams:step-test"),
                "mode": "test",
                "questions": 0,
                "xp": 0,
                "done": False,
                "optional": False,
                "milestone": True,
            }
        )

    # The first node that is neither optional nor a milestone and not yet done is where the
    # learner actually is; everything after it is "next". See ``assign_states``.
    assign_states(nodes)
    tally = practice_tally(nodes)

    return {
        "lesson": lesson,
        "nodes": nodes,
        "goal": tally["goal"],
        "done": tally["done"],
        "due_count": due_count,
        "due_left_count": due_left_count,
        "wrong_count": wrong_count,
        "session": session,
        "test_ready": test_ready,
    }


def today_board(user, today, test_questions, review=None, lessons=None, lesson_ids=None, rows=None):
    """«امروز», in one place: the skill path and the one guided day built from it.

    The dashboard and «مسیر امروز» answer the same question and used to answer it twice —
    the dashboard with its own lesson-and-practice list (``lessons/today.py``), the page
    with the guided day below. Two answers to one question drift apart, and the learner is
    left guessing which one is really today. So the day is built here, once, and both pages
    render the same steps; ``path`` travels with it because the page also shows the skill
    map.

    ``review``, ``lessons``, ``lesson_ids`` and ``rows`` are the caller's own copies of
    what ``build_path`` reads, passed straight on for the reason given there.
    """
    path = build_path(user, today, review, lessons, lesson_ids, rows)
    return {"path": path, "day": day_steps(path, user, test_questions)}


def day_steps(path, user, test_questions):
    """The guided day: review what is due, then read, practise and be measured.

    The three study steps already existed as separate destinations — the lesson page,
    «جلسهٔ امروز» and «آزمون گام» — and the learner was left to decide which to open. This
    puts them in one order, says which one is next, and gives the page a single button to
    start, which is the loop the owner asked for.

    A review step is added ahead of them whenever there is something to review: words the
    schedule says are due (``vocabulary/schedule.py``) or words the learner has answered
    wrong (``vocabulary/review.py``). Leaving it off the page called «امروز» was the gap —
    the queue existed but only the dashboard read it, and only through a practice card of
    its own. The step is the same «مرور» either way and always opens the review page, where
    both kinds of word live; only its hint and size say which of the two reasons brought the
    learner there. It becomes the *only* step once the course has no lesson left, so a
    finished learner still has a reason to come back instead of an empty day.

    The size is one *sitting* of words, never everything the schedule has due: a learner
    with two hundred words waiting is told how many lead today and how many stay in the
    queue for tomorrow (``due_left_count``), because a step that hands over the whole queue
    is a wall rather than a day (``vocabulary/schedule.py::SITTING_SIZE``).

    ``None`` for a visitor or for a learner with neither a lesson nor a due word — the same
    answer ``build_path`` gives, and for the same reason.

    Sizes are the real ones — the lesson's own estimate, the session's own question count,
    the step test's own size, the review queue's own count — rather than a target number
    invented here. The lesson and today's practice can honestly be known to be finished
    (a stored row and stored answers); the review step is finished by clearing the queue,
    and the step test stores nothing by design, so it is never claimed as done.

    The goal counts only the steps that can honestly be finished. «آزمون گام» stores
    nothing, so it is shown as a step and marked ``counted`` False: a learner can reach the
    end of the day — ``start`` is then ``None``, and the page says the day is done — without
    a test that nothing can ever mark as taken. The test is also left off the day
    altogether until the learner has finished a lesson, because a test measures what has
    been studied and on the first day that is nothing. The practice step reads
    ``path["session"]`` — the session the learner would be handed right now — which is the
    whole reason it is built in ``exercises/session.py`` and not counted here. A lesson with
    no material a session can ask gets no practice step at all, the same rule the skill map
    follows when it leaves a skill out rather than showing it empty.

    Reading the lesson and *saying* so are two different acts, and the first one is the one
    every learner performs. Reaching the journey's last step is the lesson read; the button
    there only writes the row down. So the step is finished either way — otherwise the day
    stayed at «۰ از ۳» for everyone who read a lesson without pressing a button, which is
    what the stored rows showed.
    """
    if path is None:
        return None

    steps = []

    # What is about to be forgotten comes first. A word whose review time has arrived leads,
    # because the schedule is what keeps earlier lessons from being forgotten; when nothing
    # is scheduled yet, the words the learner actually got wrong are what is left to work on.
    # Both live on the review page, so the step keeps one identity («مرور») and one
    # destination — only the hint and the size change.
    due_count = path["due_count"]
    due_left_count = path["due_left_count"]
    wrong_count = path["wrong_count"]

    if due_count > 0:
        review_hint = "وقت مرور این واژه‌ها رسیده؛ اول همین‌ها را تمرین کن تا از یادت نروند."
        if due_left_count:
            # The rest is not lost and the day does not pretend to fit it: it is still due,
            # so it leads tomorrow's sitting.
            review_hint = (
                review_hint
                + " %d واژهٔ دیگر هم نوبتشان رسیده و برای فردا می‌مانند." % due_left_count
            )
        review_size = "%d واژه" % due_count
    elif wrong_count > 0:
        review_hint = "واژه‌هایی که در تمرین‌ها اشتباه زده‌ای؛ اول همین‌ها را تمرین کن."
        review_size = "%d واژه" % wrong_count
    else:
        review_hint = ""
        review_size = ""

    if review_hint:
        steps.append(
            {
                "key": "review",
                "label": "مرور",
                "title": "مرور واژه‌ها",
                "hint": review_hint,
                "url": reverse("vocabulary:word-review"),
                "size": review_size,
                "counted": True,
                "done": False,
            }
        )

    lesson = path["lesson"]

    if lesson is not None:
        # Read here rather than taken from ``path``: the row is the learner's own, and it is
        # read at the moment the day is built rather than at the moment the lesson was
        # chosen, so a lesson finished earlier in the same request is seen as finished.
        row = LessonProgress.objects.filter(user=user, lesson=lesson).first()

        lesson_done = False
        if row is not None:
            if row.status == LessonProgress.Status.COMPLETED:
                lesson_done = True
            elif row.current_step == LessonProgress.Step.FINISH:
                lesson_done = True

        # Today's practice is today's session, so the verdict and the size both come from
        # the module that composes sessions rather than from the skill map's own tally. The
        # old rule ticked this step once every skill had been touched — about five answers —
        # while the session page still had ten questions to give, which is two answers to
        # one question (exercises/session.py::session_progress). Like the review queue's own
        # count, it is read when the day is built: one request answers once, and the next
        # page load is what sees the sitting that was just done.
        session = path["session"]
        practice_done = session["done"]

        if session["size"]:
            practice_size = "%d پرسش" % session["size"]
        else:
            practice_size = ""

        steps.append(
            {
                "key": "lesson",
                "label": "درس",
                "title": lesson.display_title,
                "hint": "درس امروز را بخوان؛ هرچه لازم داری همان‌جا هست.",
                "url": reverse("lessons:lesson-detail", args=[lesson.pk]),
                # The same lesson, read the short way. The journey is eight screens built
                # from the lesson's own material and it is the right way to *learn* the
                # lesson — but it is a long way to the first step of the day, so the
                # revision page (which already exists and shows the same rows as one
                # scannable list) is offered beside it. Both count as reading the lesson;
                # the page a learner prefers is theirs to pick.
                "alt_label": "مرور سریع درس",
                "alt_url": reverse("lessons:lesson-review", args=[lesson.pk]),
                "size": "%d دقیقه" % lesson.estimated_time,
                "counted": True,
                "done": lesson_done,
            }
        )
        # A lesson with nothing a session can ask gets no practice step at all: the same rule
        # the skill map follows, where a skill with no material is absent rather than empty. A
        # learner who has already cleared today's sitting still gets the step, marked
        # finished — that is work they really did.
        if session["size"] or session["practised"]:
            steps.append(
                {
                    "key": "practice",
                    "label": "تمرین",
                    "title": "جلسهٔ امروز",
                    "hint": "یک جلسهٔ کوتاه: هر واژه یک بار و از نوع‌های گوناگون.",
                    "url": reverse("exercises:session"),
                    "size": practice_size,
                    "counted": True,
                    "done": practice_done,
                }
            )
        if path["test_ready"]:
            steps.append(
                {
                    "key": "test",
                    "label": "آزمون گام",
                    "title": "آزمون گام",
                    "hint": "ببین روی درس‌هایی که خوانده‌ای چقدر بلدی؛ کوتاه است و نمرهٔ رسمی ندارد.",
                    "url": reverse("exams:step-test"),
                    "size": "%d پرسش" % test_questions,
                    # Shown, but outside the goal: nothing about the test is stored, so it
                    # can never be honestly finished and must not hold the day open.
                    "counted": False,
                    "done": False,
                }
            )

    # A learner with nothing to read and nothing due has no day to guide.
    if not steps:
        return None

    # The single button starts at the first step that is not finished, so it always resumes
    # rather than restarting — and it is ``None`` once every counted step is done, which is
    # a state the day can now actually reach (see the module docstring above).
    goal = 0
    finished = 0
    start = None

    for step in steps:
        if not step["counted"]:
            continue

        goal = goal + 1

        if step["done"]:
            finished = finished + 1
            continue

        if start is None:
            start = step

    return {"steps": steps, "start": start, "goal": goal, "finished": finished}
