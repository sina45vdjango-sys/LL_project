import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from exercises.models import Exercise
from vocabulary.models import Grammar, Word

from .journey import build_journey, content_step_count
from .models import Course, Lesson, LessonProgress
from .progress import complete_lesson, progress_dict, progress_state, record_step

#: Words shown per page inside the lesson's vocabulary step. Lessons carry up to
#: ~170 words, so the step is paginated rather than one enormous scroll.
WORDS_PER_STEP = 24


def _lesson_payload(lessons):
    """The minimal lesson rows the browser needs to resolve a stored lesson id.

    Shared by the dashboard and the learning path so both hand the client the same
    shape (see ``static/js/lesson_status.js``).
    """
    return [
        {
            "id": lesson.pk,
            "order": lesson.order,
            "title": lesson.title,
            "minutes": lesson.estimated_time,
            "url": reverse("lessons:lesson-detail", args=[lesson.pk]),
        }
        for lesson in lessons
    ]


def _published_courses():
    """Published courses that actually have a published lesson, in level order."""
    return (
        Course.objects.filter(is_published=True, lessons__is_published=True)
        .select_related("language_level")
        .distinct()
        .order_by("language_level__order", "pk")
    )


def _path_context(course, groups, lessons, user):
    """Context for the learning path template, shared by both path routes."""
    total_minutes = 0
    for lesson in lessons:
        total_minutes += lesson.estimated_time

    return {
        "course": course,
        "courses": list(_published_courses()),
        "groups": groups,
        "first_lesson": lessons[0] if lessons else None,
        "lesson_total": len(lessons),
        "hours_total": round(total_minutes / 60),
        "lessons_payload": _lesson_payload(lessons),
        # The learner's own progress, or None for a visitor we cannot identify.
        "progress_state": progress_state(user) if user.is_authenticated else None,
    }


class DashboardView(View):
    """The product home: where the learner is, and what to do next.

    Anonymous-first. The three questions the page answers are "where am I",
    "what is next" and "how do I continue". Course, level and lesson data all come
    from the database. What is personal comes from ``LessonProgress`` for a signed-in
    learner and from the browser (``static/js/progress.js``) for everyone else, and
    the page does not have to care which — both arrive in the same shape.
    """

    def get(self, request, *args, **kwargs):
        course = (
            Course.objects.filter(is_published=True)
            .select_related("language_level")
            .order_by("language_level__order", "pk")
            .first()
        )

        lessons = []
        if course is not None:
            lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))

        # Handed to the client so it can resolve a lesson id stored in
        # localStorage back to a title and a URL.
        lessons_payload = _lesson_payload(lessons)

        return render(
            request,
            "dashboard.html",
            {
                "course": course,
                "level": course.language_level if course else None,
                "lesson_total": len(lessons),
                "first_lesson": lessons[0] if lessons else None,
                "preview_lessons": lessons[:4],
                "lessons_payload": lessons_payload,
                # Real counts for the quick actions — nothing here is estimated.
                "word_total": Word.objects.filter(is_published=True).count(),
                "grammar_total": Grammar.objects.filter(is_published=True).count(),
                "exercise_total": Exercise.objects.filter(is_published=True).count(),
                # The learner's own progress, or None for a visitor we cannot identify.
                "progress_state": progress_state(request.user) if request.user.is_authenticated else None,
            },
        )


class CourseDetailView(View):
    """One course's path, with the course's own header instead of the catalogue."""

    def get(self, request, pk, *args, **kwargs):
        course = get_object_or_404(Course.objects.select_related("language_level"), pk=pk, is_published=True)
        lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))
        groups = [{"course": course, "level": course.language_level, "lessons": lessons}]
        return render(request, "lessons/course_detail.html", _path_context(course, groups, lessons, request.user))


class LessonDetailView(View):
    """One lesson as a guided journey.

    The page is a sequence of small learning moments built from whatever the lesson
    actually contains (see ``lessons/journey.py``). The server renders every step
    in full — the stepper only decides which one is on screen — so the lesson is
    complete and readable with JavaScript unavailable.

    A signed-in learner's own progress comes from ``LessonProgress`` (see
    ``lessons/progress.py``): this view says where to resume, and
    ``LessonProgressView`` records the moves.
    """

    def get(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course__language_level"),
            pk=pk, is_published=True, course__is_published=True,
        )
        blocks = list(lesson.contents.order_by("order", "pk"))
        grammar_links = list(
            lesson.lesson_grammars.filter(grammar__is_published=True)
            .select_related("grammar").order_by("order", "pk")
        )
        sentence_links = list(
            lesson.lesson_sentences.filter(sentence__is_published=True)
            .select_related("sentence").order_by("order", "pk")
        )
        word_links = (
            lesson.lesson_words.filter(word__is_published=True)
            .select_related("word").order_by("order", "pk")
        )
        word_page = Paginator(word_links, WORDS_PER_STEP).get_page(request.GET.get("words_page"))
        exercises = list(
            lesson.exercises.filter(is_published=True)
            .annotate(question_count=Count("questions"))
            .order_by("order", "pk")
        )

        steps = build_journey(
            blocks=blocks,
            grammar_links=grammar_links,
            sentence_links=sentence_links,
            word_page=word_page,
            exercises=exercises,
        )

        # A signed-in learner's own progress: which step to open on, and how far they
        # have come across the whole course (the same payload the dashboard uses).
        # Anonymous visitors get neither and keep the browser-only behaviour.
        lesson_progress = None
        resume_step = None
        if request.user.is_authenticated:
            lesson_progress = LessonProgress.objects.filter(
                user=request.user, lesson=lesson
            ).first()
            if lesson_progress:
                # Open the step the learner stopped on, when the lesson still has it.
                for position, step in enumerate(steps):
                    if step["key"] == lesson_progress.current_step:
                        resume_step = position
                        break

        siblings = lesson.course.lessons.filter(is_published=True).order_by("order", "pk")
        return render(request, "lessons/lesson_detail.html", {
            "lesson": lesson,
            "steps": steps,
            "journey_step_count": len(steps),
            "material_step_count": content_step_count(steps),
            # Progress on arrival: step 1 of N, for visitors with no JavaScript.
            "journey_percent": round(100 / len(steps)) if steps else 0,
            "previous_lesson": siblings.filter(order__lt=lesson.order).last(),
            "next_lesson": siblings.filter(order__gt=lesson.order).first(),
            "resume_step": resume_step,
            "progress_state": progress_state(request.user) if request.user.is_authenticated else None,
        })


class LessonProgressView(LoginRequiredMixin, View):
    """Records where a signed-in learner is in a lesson (POST, JSON in and out).

    The lesson page owns this conversation: one small POST when the learner reaches
    a step, and one when they finish. Keeping it out of the page render means a GET
    stays a read — nothing is written on arrival, and nothing is written for a
    visitor we cannot identify.

    ``raise_exception`` rather than a redirect, because a redirect to the login page
    is not a useful answer to a fetch().
    """

    raise_exception = True

    def post(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(Lesson, pk=pk, is_published=True)

        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        step = payload.get("step", "")
        if step not in LessonProgress.Step.values:
            return JsonResponse({"error": "unknown step"}, status=400)

        if payload.get("complete") is True:
            row = complete_lesson(request.user, lesson, step)
        else:
            row = record_step(request.user, lesson, step)

        return JsonResponse(progress_dict(row))


class LessonListView(View):
    """The learning path: one sequential trail of lessons per course.

    Deliberately **not** paginated — a path that breaks across pages stops being a
    path. Status (completed / current / upcoming) is applied in the browser: from the
    learner's own progress rows when they are signed in, and from the localStorage
    layer otherwise. So the server still renders every lesson as not-started, which is
    the honest answer for a visitor it cannot identify.
    """

    def get(self, request, *args, **kwargs):
        groups, lessons = [], []
        for course in _published_courses():
            course_lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))
            lessons.extend(course_lessons)
            groups.append({"course": course, "level": course.language_level, "lessons": course_lessons})
        return render(request, "lessons/lesson_list.html", _path_context(None, groups, lessons, request.user))
