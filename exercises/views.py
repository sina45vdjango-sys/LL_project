import json

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts import xp
from accounts.models import UserProfile
from exercises.grading import grade
from exercises.hints import hint_for, hint_strength
from exercises.history import exercise_history, wrong_counts
from exercises.models import Exercise, ExerciseAttempt
from exercises.conversation import conversation_turns
from exercises.runner import build_runner, question_rows, scoreable_count
from exercises.session import build_session, session_lesson
from lessons.models import Lesson
from lessons.skill_path import SKILLS, grammar_exercise_ids, skill_of
from vocabulary.progress import record_word_progress, tested_word
from vocabulary.status import MISTAKE_LIMIT

#: A response time longer than this is not worth storing — an hour on one question
#: means the tab sat open while the learner was away, not that they were thinking.
MAX_RESPONSE_TIME = 3600


def _response_time(value):
    """The browser's measurement in seconds, or ``None`` when it is unusable.

    This is learning analytics, not a security control, so an unusable value is simply
    left out instead of rejecting the submission that came with it.
    """
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None

    if seconds < 0 or seconds > MAX_RESPONSE_TIME:
        return None

    return round(seconds, 1)


class ExerciseListView(View):
    """One lesson's exercise list, and the old bare URL as a redirect.

    The bare URL used to print every card, then one row per lesson. Both were still a wall
    of exercises, so the practice path (concept 23, ``lessons/skill_path.py``) took its
    place. That page already has an address of its own — ``lessons:practice-path`` at
    ``/lessons/today/`` — so the bare exercises URL does not draw a second copy: it
    redirects there. ``?lesson=<id>`` is unchanged and is where the lesson journey, the
    session footer and the runner link.

    Only published exercises of published lessons in published courses are counted and
    listed — the same rule the dashboard, the learning path and the lesson journey already
    follow, so a draft never shows up in a learner-facing list.
    """

    template_name = "exercises/exercise_list.html"

    def published_exercises(self):
        """Every reachable exercise, with its question count."""
        return (
            Exercise.objects.filter(
                is_published=True,
                lesson__is_published=True,
                lesson__course__is_published=True,
            )
            .select_related("lesson", "lesson__course")
            .annotate(question_count=Count("questions"))
        )

    def get(self, request, *args, **kwargs):
        # The bare URL is the practice path now, and that page already lives at
        # lessons:practice-path. Rather than render the same template from two views, this
        # one sends the learner there. A visitor is passed along too and reads the path's
        # own "this needs an account" notice.
        lesson_pk = request.GET.get("lesson")

        if not lesson_pk:
            return redirect("lessons:practice-path")

        lesson = get_object_or_404(Lesson, pk=lesson_pk, is_published=True)
        exercises = list(self.published_exercises().filter(lesson=lesson).order_by("order"))

        question_total = 0
        for exercise in exercises:
            question_total += exercise.question_count

        return render(
            request,
            self.template_name,
            {
                "lesson": lesson,
                "exercises": exercises,
                "exercise_total": len(exercises),
                "question_total": question_total,
            },
        )


class ExerciseDetailView(View):
    """A single exercise, run one question at a time.

    The question list comes from ``exercises/runner.py`` (kind, options, passage). The
    correct answers are deliberately **not** rendered: the learner submits to
    ``ExerciseSubmitView`` and the verdict comes back with the expected answer.

    A signed-in learner who has answered this exercise before also gets their own past
    result (``exercises/history.py``), because otherwise a reload would look like a
    fresh start even though every answer is already stored.

    Only published exercises of published lessons in published courses are reachable —
    the same rule the index follows, so a draft can never be opened by URL either.
    """

    template_name = "exercises/exercise_detail.html"

    def get(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise.objects.filter(
                is_published=True,
                lesson__is_published=True,
                lesson__course__is_published=True,
            )
            .select_related("lesson")
            .prefetch_related(
                "questions__answers",
                "questions__targets__sentence",
                "questions__targets__word",
            ),
            pk=pk,
        )

        questions = build_runner(exercise)
        siblings = list(
            Exercise.objects.filter(lesson=exercise.lesson, is_published=True).order_by("order")
        )

        # What the learner sees is the exercise's place in this ordered list, not its
        # stored `order`. `order` is a lesson-wide counter the generators keep appending
        # to, so rebuilding the content pushed an authored exercise from 5 to 61; a list
        # position cannot drift that way. This is the same rule the runner already uses
        # for questions — its `number` is the display position, not `Question.order`.
        exercise_number = 0

        # The next published exercise of the lesson, or None when this is the last one.
        next_exercise = None
        for position, sibling in enumerate(siblings, start=1):
            if sibling.pk == exercise.pk:
                exercise_number = position
            if next_exercise is None and sibling.order > exercise.order:
                next_exercise = sibling

        # No hint button by default: a question earns one only from stored mistakes, and a
        # learner with nothing stored has none. The value is set for every question so the
        # template does not have to know whether there is an account behind the page.
        for question in questions:
            question["hint_strength"] = 0

        # What this learner has already done here. A visitor we cannot identify has
        # nothing stored, so they get None and the page simply omits the panel.
        history = None
        if request.user.is_authenticated:
            history = exercise_history(request.user, exercise)

            # A question the learner keeps missing earns a hint. How many times each was
            # missed is read once for the whole exercise (not once per question), and only
            # the strength is put on the page — the hint itself is fetched on demand, so
            # the answer it hides stays off the page until the learner asks.
            misses = wrong_counts(request.user, exercise)
            for question in questions:
                if question["id"] in misses:
                    question["hint_strength"] = hint_strength(misses[question["id"]])

        context = {
            "exercise": exercise,
            "exercise_number": exercise_number,
            "questions": questions,
            "total_questions": len(questions),
            "scoreable_questions": scoreable_count(questions),
            "next_exercise": next_exercise,
            "history": history,
        }
        return render(request, self.template_name, context)


class SessionView(View):
    """Today's practice as one bounded session, in place of the lesson's exercise wall.

    The composition is ``exercises/session.py``: at most fifteen questions, one per word
    or sentence, kinds interleaved, and nothing already practised today. This view only
    decides which lesson today means and hands the questions to the same runner an
    exercise page uses, so grading, recording, XP and the word-review schedule all keep
    working without a second code path.

    A visitor gets a session too — the content is public — but with nothing filtered out,
    because there is nothing stored about them to filter by.
    """

    template_name = "exercises/session.html"

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        lesson = session_lesson(request.user)

        if lesson is None:
            questions = []
            session = {"goal": 0, "skills": []}
        else:
            session = build_session(request.user, today, lesson)
            questions = question_rows(session["questions"])

        # A session does not pre-read hint strength. Hints are counted per exercise
        # (exercises/history.py), and the submission's own response already carries the
        # strength a fresh mistake earns — so a hint still appears the moment it is owed,
        # it just is not pre-computed across fifteen exercises here.
        for question in questions:
            question["hint_strength"] = 0

        context = {
            "lesson": lesson,
            "questions": questions,
            "total_questions": len(questions),
            "goal": session["goal"],
            "skills": session["skills"],
        }
        return render(request, self.template_name, context)


class PracticeChatView(View):
    """Concept 9 — the lesson's dialogue said out loud with a teacher.

    The content is the lesson's own ``DIALOGUE`` sentences (``exercises/conversation.py``),
    not an exercise's quiz questions: the teacher speaks the partner's lines, the learner
    answers their own freely, and each answer is checked against the line the lesson
    actually uses. That is why the page reads like a conversation instead of a form.

    Nothing is graded and nothing is stored here — the learner's own line cannot be marked
    right or wrong, which is the same honesty the speaking node keeps. The graded practice
    of the same lesson is one link away, on its exercise page.

    ``lessons/skill_path.py`` gives this page a node of its own, because it is an activity
    about the whole lesson rather than a drill for one skill. The scene and the partner are
    the same conversation concept 13 plays, and only the framing differs.
    """

    template_name = "exercises/chat.html"

    def get(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise.objects.filter(
                is_published=True,
                lesson__is_published=True,
                lesson__course__is_published=True,
            ).select_related("lesson"),
            pk=pk,
        )

        conversation = conversation_turns(exercise.lesson)

        # Which skill this exercise trains, read from the runner's own rule rather than
        # from the query string, so the header cannot claim a skill the exercise is not.
        skill_key = skill_of(exercise, grammar_exercise_ids([exercise]))
        skill_label = ""
        for skill in SKILLS:
            if skill["key"] == skill_key:
                skill_label = skill["label"]

        context = {
            "exercise": exercise,
            "lesson": exercise.lesson,
            "mode": "chat",
            "you": conversation["you"],
            "partner": conversation["partner"],
            "turns": conversation["turns"],
            "mine_count": sum(1 for turn in conversation["turns"] if turn["mine"]),
            "skill_key": skill_key,
            "skill_label": skill_label,
        }
        return render(request, self.template_name, context)


class PracticeDialogueView(View):
    """Concept 13 — the lesson's own dialogue, played as a role-play.

    The lesson already contains a real conversation with a translation and a recording on
    every line (``exercises/conversation.py``); this page sets that scene and lets the
    learner take their own part in it, one line at a time. The partner's lines are said
    for them, and their own lines they answer in their own words — then see the line the
    lesson uses, so they can judge for themselves how close they were.

    This is the role-play framing of the same conversation concept 9 plays, and it is
    reached from that page rather than from a skill node: a dialogue belongs to the whole
    lesson, not to one skill. Nothing is graded and nothing is stored — the learner's own
    line cannot be marked, which is the same honest limit the speaking node keeps.
    """

    template_name = "exercises/dialogue.html"

    def get(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise.objects.filter(
                is_published=True,
                lesson__is_published=True,
                lesson__course__is_published=True,
            ).select_related("lesson", "lesson__course"),
            pk=pk,
        )

        conversation = conversation_turns(exercise.lesson)

        skill_key = skill_of(exercise, grammar_exercise_ids([exercise]))
        skill_label = ""
        for skill in SKILLS:
            if skill["key"] == skill_key:
                skill_label = skill["label"]

        context = {
            "exercise": exercise,
            "lesson": exercise.lesson,
            "mode": "dialogue",
            "you": conversation["you"],
            "partner": conversation["partner"],
            "turns": conversation["turns"],
            "mine_count": sum(1 for turn in conversation["turns"] if turn["mine"]),
            "skill_key": skill_key,
            "skill_label": skill_label,
        }
        return render(request, self.template_name, context)


class ExerciseSubmitView(View):
    """One submitted answer: graded here and, for a signed-in learner, recorded.

    The verdict is the server's either way — that is why the correct answer is no
    longer part of the page — but an ``ExerciseAttempt`` needs a learner, so an
    anonymous visitor is graded and then forgotten.

    The same visibility rule as ``ExerciseDetailView`` applies here. A learner cannot
    submit to an exercise the runner would refuse to show them, so a stored attempt can
    never point at a draft.
    """

    def post(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            is_published=True,
            lesson__is_published=True,
            lesson__course__is_published=True,
        )

        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        question = exercise.questions.filter(pk=payload.get("question")).first()
        if question is None:
            return JsonResponse({"error": "unknown question"}, status=400)

        verdict = grade(question, payload.get("answer"), payload.get("response_text"))
        if verdict is None:
            return JsonResponse({"error": "question cannot be graded"}, status=400)

        recorded = False
        strength = 0
        # Set for everyone: an anonymous visitor is graded and forgotten, so there is
        # nothing to credit and the response says so with a null rather than a zero.
        points = 0
        xp_summary = None
        word_progress = None
        if request.user.is_authenticated:
            # A new row every time on purpose: the learner's answers are history, not a
            # tally, so a later feature can look back at what they got wrong.
            response_time = _response_time(payload.get("response_time"))
            ExerciseAttempt.objects.create(
                user=request.user,
                exercise=exercise,
                question=question,
                answer=verdict["answer"],
                response_text=verdict["response_text"],
                is_correct=verdict["is_correct"],
                response_time=response_time,
            )
            # The same submission moves the word's review schedule, using this answer's
            # response time to nudge the next interval (vocabulary/schedule.py). The row
            # comes back so the results screen can name the word that was missed.
            word_progress = record_word_progress(
                request.user, question, verdict["is_correct"], response_time
            )
            recorded = True

            # Read back after recording: a wrong answer just now is one of the misses, so
            # the strength the page is told about includes it and a repeated mistake makes
            # the hint available at once.
            misses = wrong_counts(request.user, exercise)
            strength = hint_strength(misses.get(question.pk, 0))

            # The practice path's feedback layer (accounts/xp.py). A correct answer is
            # worth points; a wrong one is worth none but still counts as showing up, so
            # ``award`` is called either way and it is the amount that changes. The XP is
            # read back as the new totals rather than as a delta, so the page can redraw
            # the bar without doing arithmetic of its own.
            #
            # A second try at the same question earns nothing, even when it is right: the
            # points for this question were decided by the first attempt, and paying for a
            # retry would reward guessing once to see the answer and then answering again.
            # The attempt is still recorded and still moves the word's schedule, because
            # the learner did answer.
            if verdict["is_correct"] and not payload.get("retry"):
                points = xp.XP_PER_CORRECT_ANSWER

            profile = UserProfile.objects.filter(user=request.user).first()
            xp_summary = xp.award(profile, points, timezone.localdate())

        # The word behind this question, with what a learner needs to actually learn it:
        # the article, the plural, how it sounds and what it means. This is the teaching
        # moment a miss otherwise lacks. Most questions carry no written explanation (89
        # of 5428), but almost every one tests a real Word row, so the card is built from
        # the word itself rather than from an authored note that is not there.
        #
        # Sent to a visitor as well, not only to a signed-in learner: the word is public
        # content and a visitor deserves the same teaching. Only the counters are
        # personal, so they are added when there is a WordProgress to read them from.
        # The server also gathers these into the results screen's "weak words" list, so a
        # word missed here and missed before is still called out by the same rule the
        # lesson rows use (``MISTAKE_LIMIT``, vocabulary/status.py).
        word_card = None
        if not verdict["is_correct"]:
            word = tested_word(question)
            if word is not None:
                word_card = {
                    "id": word.pk,
                    "word": word.word,
                    "article": word.article,
                    "plural": word.plural,
                    "pronunciation": word.pronunciation,
                    "meaning_fa": word.meaning_fa,
                    "word_type": word.type_label,
                    "url": reverse("vocabulary:word-detail", args=[word.pk]),
                    "repeated": False,
                    "wrong_count": 0,
                }
                if word_progress is not None:
                    word_card["repeated"] = word_progress.wrong_count >= MISTAKE_LIMIT
                    word_card["wrong_count"] = word_progress.wrong_count

        return JsonResponse(
            {
                "correct": verdict["is_correct"],
                # The option the page should flag, and the answers to show when the
                # learner missed it.
                "correct_answer": verdict["correct_answer_id"],
                "expected": verdict["expected"],
                "explanation": question.explanation,
                "recorded": recorded,
                # The missed word behind this question, with its teaching facts, or null.
                "tested_word": word_card,
                # How strong a hint this question has earned by now. The page shows the
                # hint button when it is above zero; the hint text is fetched separately.
                "hint_strength": strength,
                # The new XP/level/streak totals, or None for a visitor. The runner uses
                # this to show a small "+10 امتیاز" note; nothing is stored on the page.
                "xp": xp_summary,
                "xp_gained": points,
            }
        )


class ExerciseHintView(View):
    """One question's hint, for a learner who has earned it.

    The hint is computed here rather than rendered into the page, because the answer it
    hides must stay off the page (``exercises/runner.py``). The learner has to ask for it,
    and the server decides whether they have missed the question enough times to be owed
    one — a page cannot claim a hint it has not earned.

    The same visibility rule as the other views applies: a hint for a draft exercise is a
    hint for an exercise the learner cannot open anyway.
    """

    def get(self, request, pk, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "no account"}, status=403)

        exercise = get_object_or_404(
            Exercise,
            pk=pk,
            is_published=True,
            lesson__is_published=True,
            lesson__course__is_published=True,
        )

        question = exercise.questions.filter(pk=request.GET.get("question")).first()
        if question is None:
            return JsonResponse({"error": "unknown question"}, status=400)

        misses = wrong_counts(request.user, exercise)
        strength = hint_strength(misses.get(question.pk, 0))
        if strength == 0:
            return JsonResponse({"error": "no hint yet"}, status=404)

        # The kind comes from the runner, so a choice question's hint and its rendering
        # cannot drift apart.
        rows = question_rows([question], scramble=exercise.type == Exercise.ExerciseType.SCRAMBLE)
        kind = rows[0]["kind"]

        return JsonResponse({"hint": hint_for(question, kind, strength), "strength": strength})
