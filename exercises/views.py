import json

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from exercises.grading import grade
from exercises.history import exercise_history
from exercises.models import Exercise, ExerciseAttempt
from exercises.runner import build_runner, scoreable_count
from lessons.models import Lesson
from vocabulary.progress import record_word_progress

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
    """The exercise index: one lesson's exercises, or every published exercise.

    Only published exercises of published lessons in published courses are listed —
    the same rule the dashboard, the learning path and the lesson journey already
    follow, so a draft never shows up in a learner-facing list.
    """

    template_name = "exercises/exercise_list.html"

    def get(self, request, *args, **kwargs):
        lesson = None
        exercises = (
            Exercise.objects.filter(
                is_published=True,
                lesson__is_published=True,
                lesson__course__is_published=True,
            )
            .select_related("lesson", "lesson__course")
            .annotate(question_count=Count("questions"))
            .order_by("lesson__course__language_level__order", "lesson__order", "order")
        )

        lesson_pk = request.GET.get("lesson")
        if lesson_pk:
            lesson = get_object_or_404(Lesson, pk=lesson_pk, is_published=True)
            exercises = exercises.filter(lesson=lesson)

        # Materialised: the template counts rows, and {% regroup %} needs one pass.
        exercises = list(exercises)

        question_total = 0
        lesson_ids = set()
        for exercise in exercises:
            question_total += exercise.question_count
            lesson_ids.add(exercise.lesson_id)

        context = {
            "lesson": lesson,
            "exercises": exercises,
            "question_total": question_total,
            "lesson_count": len(lesson_ids),
        }
        return render(request, self.template_name, context)


class ExerciseDetailView(View):
    """A single exercise, run one question at a time.

    The question list comes from ``exercises/runner.py`` (kind, options, passage). The
    correct answers are deliberately **not** rendered: the learner submits to
    ``ExerciseSubmitView`` and the verdict comes back with the expected answer.

    A signed-in learner who has answered this exercise before also gets their own past
    result (``exercises/history.py``), because otherwise a reload would look like a
    fresh start even though every answer is already stored.
    """

    template_name = "exercises/exercise_detail.html"

    def get(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise.objects.select_related("lesson").prefetch_related(
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

        # The next published exercise of this lesson, or None when this is the last one.
        next_exercise = None
        for sibling in siblings:
            if sibling.order > exercise.order:
                next_exercise = sibling
                break

        # What this learner has already done here. A visitor we cannot identify has
        # nothing stored, so they get None and the page simply omits the panel.
        history = None
        if request.user.is_authenticated:
            history = exercise_history(request.user, exercise)

        context = {
            "exercise": exercise,
            "questions": questions,
            "total_questions": len(questions),
            "scoreable_questions": scoreable_count(questions),
            "next_exercise": next_exercise,
            "history": history,
        }
        return render(request, self.template_name, context)


class ExerciseSubmitView(View):
    """One submitted answer: graded here and, for a signed-in learner, recorded.

    The verdict is the server's either way — that is why the correct answer is no
    longer part of the page — but an ``ExerciseAttempt`` needs a learner, so an
    anonymous visitor is graded and then forgotten.
    """

    def post(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=pk)

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
        if request.user.is_authenticated:
            # A new row every time on purpose: the learner's answers are history, not a
            # tally, so a later feature can look back at what they got wrong.
            ExerciseAttempt.objects.create(
                user=request.user,
                exercise=exercise,
                question=question,
                answer=verdict["answer"],
                response_text=verdict["response_text"],
                is_correct=verdict["is_correct"],
                response_time=_response_time(payload.get("response_time")),
            )
            record_word_progress(request.user, question, verdict["is_correct"])
            recorded = True

        return JsonResponse(
            {
                "correct": verdict["is_correct"],
                # The option the page should flag, and the answers to show when the
                # learner missed it.
                "correct_answer": verdict["correct_answer_id"],
                "expected": verdict["expected"],
                "explanation": question.explanation,
                "recorded": recorded,
            }
        )
