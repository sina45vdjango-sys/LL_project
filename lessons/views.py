import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts import xp
from accounts.badges import badges_for
from accounts.models import UserProfile
from exams.step import STEP_SIZE
from exercises.eligibility import course_lessons, eligible_lesson_ids
from exercises.models import Exercise, Question
from exercises.runner import question_rows
from vocabulary import status as vocabulary_status
from vocabulary.models import Grammar, Word
from vocabulary.review import lesson_mistakes, review_plan

from .check import check_questions, pass_needed
from .journey import build_journey, content_step_count
from .models import Course, Lesson, LessonProgress, LessonWord
from .progress import (
    complete_lesson,
    import_guest_progress,
    progress_dict,
    progress_rows,
    progress_state,
    record_step,
)
from .readiness import course_progress, goal_of, learning_pace, readiness
from .review import build_review
from .skill_path import lesson_practice, today_board
from .today import day_summary, last_activity, weekly_activity

#: Words shown per page inside the lesson's vocabulary step. Lessons carry up to
#: ~170 words, so the step is paginated rather than one enormous scroll.
WORDS_PER_STEP = 24


def _lesson_payload(lessons):
    """The minimal lesson rows the browser needs to resolve a stored lesson id.

    Shared by the dashboard and the learning path so both hand the client the same
    shape (see ``static/js/lesson_status.js``).
    """
    rows = []
    for lesson in lessons:
        rows.append(
            {
                "id": lesson.pk,
                "order": lesson.order,
                # The Persian title, because this payload is read back by the Persian pages:
                # the dashboard and the learning path both show it as the lesson's name.
                "title": lesson.display_title,
                "minutes": lesson.estimated_time,
                "url": reverse("lessons:lesson-detail", args=[lesson.pk]),
            }
        )

    return rows


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

    # The first lesson of the path, or None when the course has no published lesson.
    first_lesson = None
    if lessons:
        first_lesson = lessons[0]

    # The learner's own progress, or None for a visitor we cannot identify.
    progress = None
    if user.is_authenticated:
        progress = progress_state(user)

    return {
        "course": course,
        "courses": list(_published_courses()),
        "groups": groups,
        "first_lesson": first_lesson,
        "lesson_total": len(lessons),
        "hours_total": round(total_minutes / 60),
        "lessons_payload": _lesson_payload(lessons),
        "progress_state": progress,
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

        # The learner's goal, how much of the course is behind them, and the pace their
        # own date implies. All three stay None for a visitor we cannot identify, so the
        # page says nothing about a goal rather than showing an empty one.
        today = timezone.localdate()
        goal = None
        pace = None
        course_stats = None
        review = None
        board = None
        today_stats = None
        last_seen = None
        progress = None
        weekly = None
        rows = None

        if request.user.is_authenticated:
            profile = UserProfile.objects.filter(user=request.user).first()
            goal = goal_of(profile)
            # The learner's own progress rows and the course's own lesson list, read once
            # and handed to everything below. Each of the questions this page asks — where
            # the learner stopped, which lessons are finished, which lessons they may
            # practise, what is due, when they were last here — used to read one or both of
            # these tables for itself, which made one page load read the same handful of
            # rows five times over.
            rows = progress_rows(request.user)
            all_lessons = course_lessons()
            lesson_ids = eligible_lesson_ids(request.user, all_lessons, rows)
            course_stats = course_progress(request.user, all_lessons, rows)
            pace = learning_pace(course_stats, goal, today)
            # The learner's own missed words and the exercises that test them — the
            # personal review panel, two exercises deep. Built once and handed to
            # ``today_board`` below so one page does not compute the same plan twice.
            review = review_plan(
                request.user, word_limit=3, exercise_limit=2, lesson_ids=lesson_ids
            )
            # «امروز»: the one guided day both this page and «مسیر امروز» render, so the
            # two pages cannot disagree about what today is
            # (lessons/skill_path.py::today_board).
            board = today_board(
                request.user,
                today,
                STEP_SIZE,
                review,
                lessons=all_lessons,
                lesson_ids=lesson_ids,
                rows=rows,
            )
            # What the learner has already answered today, and when they were last here,
            # counted from their stored rows (lessons/today.py).
            today_stats = day_summary(request.user, today)
            last_seen = last_activity(request.user, rows)
            # The learner's own progress payload and their last seven days of answers,
            # both built from the rows already read above (lessons/today.py owns the rule
            # for the weekly chart).
            progress = progress_state(request.user, rows)
            weekly = weekly_activity(request.user, today)

        # The course's level and its first lesson, or None when the course does not exist
        # yet. Read once here rather than re-deciding both inside the page's context.
        level = None
        if course is not None:
            level = course.language_level

        first_lesson = None
        if lessons:
            first_lesson = lessons[0]

        return render(
            request,
            "dashboard.html",
            {
                "course": course,
                "level": level,
                "lesson_total": len(lessons),
                "first_lesson": first_lesson,
                "preview_lessons": lessons[:4],
                "lessons_payload": lessons_payload,
                # Real counts for the quick actions — nothing here is estimated, and they
                # are the *course's* numbers rather than the database's. The dashboard used
                # to advertise every published word row (3,226 of them), including the 2,208
                # that belong to no lesson and no course at all: a 24-lesson A1 course that
                # claimed three thousand words was describing a different thing from the one
                # it teaches. These three queries count what the path in `lessons` above
                # actually contains, which is the only number a learner can check by
                # studying.
                "word_total": LessonWord.objects.filter(
                    lesson__in=lessons,
                    word__is_published=True,
                ).values("word_id").distinct().count(),
                "grammar_total": Grammar.objects.filter(is_published=True).count(),
                "exercise_total": Exercise.objects.filter(
                    is_published=True,
                    lesson__in=lessons,
                ).count(),
                "question_total": Question.objects.filter(
                    exercise__is_published=True,
                    exercise__lesson__in=lessons,
                ).count(),
                # The learner's own progress, or None for a visitor we cannot identify.
                "progress_state": progress,
                # The only answer on this page that comes from the learner's own answers
                # instead of from where the course happens to be: the words they got
                # wrong and the exercises that test them (vocabulary/review.py). None
                # for a visitor, and None for a learner who has not missed anything —
                # the panel is omitted rather than filled with an invented summary.
                "review": review,
                # The learner's stated goal and the one line that connects it to where
                # the course is. All three are None for a visitor we cannot identify, so
                # the page says nothing rather than showing an empty goal.
                # (lessons/readiness.py owns the arithmetic.)
                "goal": goal,
                "pace": pace,
                "course_stats": course_stats,
                # «امروز»: the one guided day — review what is due or missed, read the
                # lesson, practise, be measured — built by the same function that builds
                # «مسیر امروز», so the two pages agree. None for a visitor we cannot
                # identify, who has no stored rows to plan from.
                "board": board,
                # What the learner has answered today and when they were last here. None
                # for a visitor we cannot identify, who has no stored rows to read.
                "today_stats": today_stats,
                "last_activity": last_seen,
                # The last seven days of the learner's own answers, counted from the same
                # rows «امروز» counts. None for a visitor we cannot identify, who has no
                # stored answers to chart (lessons/today.py owns the rule).
                "weekly": weekly,
            },
        )


class BentoDashboardView(View):
    """Bento Grid Dashboard view for interactive learner overview."""

    def get(self, request, *args, **kwargs):
        course = (
            Course.objects.filter(is_published=True)
            .select_related("language_level")
            .order_by("language_level__order", "pk")
            .first()
        )
        lessons = []
        active_lesson = None
        sample_audio = None
        if course is not None:
            lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))
            if lessons:
                if len(lessons) > 5:
                    active_lesson = lessons[5]
                else:
                    active_lesson = lessons[0]

        from vocabulary.models import Sentence
        sample_sentence = Sentence.objects.filter(audio__isnull=False).exclude(audio="").first()
        if sample_sentence is not None:
            if sample_sentence.audio:
                sample_audio = sample_sentence.audio

        context = {
            "course": course,
            "active_lesson": active_lesson,
            "sample_audio": sample_audio,
            "readiness_score": 78,
            "brand": {"name": "ولینگو", "tagline": "یادگیری آلمانی برای فارسی‌زبان‌ها"},
        }
        return render(request, "bento_dashboard.html", context)


class ReadinessView(View):
    """«آمادگی من»: how this learner is doing, from their own stored rows.

    A public URL with personal content, exactly like the review page: a visitor we
    cannot identify is told that this needs an account instead of being redirected, and
    nobody ever sees another learner's numbers — ``lessons/readiness.py`` reads rows for
    one user and one user only.

    Nothing here writes, and nothing here estimates. The module docstring says what each
    number means and what the data cannot support; the page repeats the second half to
    the learner.
    """

    template_name = "readiness.html"

    def get(self, request, *args, **kwargs):
        data = None

        if request.user.is_authenticated:
            data = readiness(request.user)

        # `onboarding=1` means the learner arrived here from the goal form during their first
        # run, so this page is step two of two and says so. Every other visit is the ordinary
        # «آمادگی من» and renders exactly as it always did.
        return render(
            request,
            self.template_name,
            {
                "readiness": data,
                "onboarding": request.GET.get("onboarding") == "1",
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
        # `?mode=short` walks the 15-minute path through this same lesson: the same content,
        # the same step templates, the same exercise pages and the same completion rule — only
        # less of it at once (lessons/journey.py decides what "less" means and says so). A
        # query parameter rather than a second URL, so there is one lesson page and no way for
        # the two versions to drift apart.
        short = request.GET.get("mode") == "short"

        if short:
            # The short path never paginates, so it always reads page one: the query string
            # must not be able to put it on page 4 of the list it is about to trim anyway.
            word_page = Paginator(word_links, WORDS_PER_STEP).get_page(1)
        else:
            word_page = Paginator(word_links, WORDS_PER_STEP).get_page(request.GET.get("words_page"))

        # The vocabulary rows carry the one label each word earns for *this* learner, so
        # they are built here, where the request's user is known (vocabulary/status.py).
        word_rows = vocabulary_status.word_rows(word_page, request.user, timezone.now())
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
            word_rows=word_rows,
            exercises=exercises,
            short=short,
        )

        # The journey's «تمرین» step shows the same skill map «مسیر امروز» shows, instead
        # of the lesson's whole exercise list: the grouping exists to replace that wall,
        # and the page that teaches the lesson is where the wall did the most damage
        # (lessons/skill_path.py::lesson_practice owns the grouping).
        for step in steps:
            if step["key"] == "practice":
                step["practice_path"] = lesson_practice(lesson, request.user, timezone.localdate())

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

        # Progress on arrival: step 1 of N, or 0 when the lesson has no steps at all.
        journey_percent = 0
        if steps:
            journey_percent = round(100 / len(steps))

        # How far the learner has come across the whole course — the same payload the
        # dashboard uses, and None for a visitor we cannot identify.
        progress = None
        if request.user.is_authenticated:
            progress = progress_state(request.user)

        siblings = lesson.course.lessons.filter(is_published=True).order_by("order", "pk")
        next_lesson = siblings.filter(order__gt=lesson.order).first()

        # The last lesson of the course has no «درس بعدی» to offer, so it says what finishing
        # the course means instead (P-30: the course used to simply stop here). Both numbers
        # are read from the content, never written into the page: how many lessons the course
        # has, and whether a later course exists to point at. The extra queries run only on
        # that one page, which is the only page that needs them.
        course_lesson_total = siblings.count()
        next_course = None
        lesson_finished = False

        if request.user.is_authenticated and lesson_progress is not None:
            lesson_finished = lesson_progress.status == LessonProgress.Status.COMPLETED

        if next_lesson is None:
            next_course = (
                Course.objects.filter(
                    is_published=True,
                    language_level__order__gt=lesson.course.language_level.order,
                )
                .select_related("language_level")
                .order_by("language_level__order")
                .first()
            )

        return render(request, "lessons/lesson_detail.html", {
            "lesson": lesson,
            "steps": steps,
            # "short" is the 15-minute path; the template uses it to say so and to offer the
            # way back to the full lesson.
            "mode": "short" if short else "full",
            "journey_step_count": len(steps),
            "material_step_count": content_step_count(steps),
            # Progress on arrival: step 1 of N, for visitors with no JavaScript.
            "journey_percent": journey_percent,
            "previous_lesson": siblings.filter(order__lt=lesson.order).last(),
            "next_lesson": next_lesson,
            # What the finish step says when there is no next lesson: how long the course is,
            # whether the learner has finished it, and whether a later course exists.
            "course_lesson_total": course_lesson_total,
            "lesson_finished": lesson_finished,
            "next_course": next_course,
            "resume_step": resume_step,
            "progress_state": progress,
            # What this learner got wrong *in this lesson*, so the finish step can name
            # it instead of only counting the steps behind them. Empty for a visitor we
            # cannot identify and for a lesson with no mistakes in it
            # (vocabulary/review.py owns the rule).
            "lesson_mistakes": lesson_mistakes(request.user, lesson),
            "new_words_count": lesson.lesson_words.filter(
                role=LessonWord.Role.NEW, word__is_published=True
            ).count(),
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


class LessonImportView(LoginRequiredMixin, View):
    """Takes the progress a visitor made in this browser and puts it on their account.

    A visitor learns without an account and their progress lives in ``localStorage``
    (``static/js/progress.js``). The moment they sign up, the dashboard starts showing the
    server's answer — which is empty — so the work they did is not wrong, it is simply no
    longer looked at. That is a silent loss, and this endpoint is the way back: the
    dashboard reads the browser, asks «بیاورم؟», and posts what the browser reported.

    The browser is a claim, not a source of truth, so the rules live in
    ``lessons/progress.py::import_guest_progress``: an unknown or unpublished lesson is
    ignored, a lesson cannot be un-finished, and a report of «started» never writes a
    completion the browser never claimed. Nothing here reads another learner's rows — the
    write is always against ``request.user``.

    ``raise_exception``, like ``LessonProgressView``: a redirect to the login page is not a
    useful answer to a fetch().
    """

    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        reported = payload.get("lessons")
        if not isinstance(reported, dict):
            return JsonResponse({"error": "lessons must be an object"}, status=400)

        cleaned = {}
        for key, status in reported.items():
            # The keys arrive as JSON object keys, so they are strings: "7", not 7.
            if not str(key).isdigit():
                return JsonResponse({"error": "lesson ids must be numbers"}, status=400)
            if status not in ("started", "completed"):
                return JsonResponse({"error": "unknown status"}, status=400)
            cleaned[int(key)] = status

        written = import_guest_progress(request.user, cleaned)

        return JsonResponse({"imported": written})


class LessonReviewView(View):
    """One lesson's material as a single scannable page — the revision pass.

    The journey teaches a lesson; this revisits it. The same rows (``lessons/review.py``)
    are shown as lists instead of narrative steps, so a learner can bring a lesson back to
    mind in a minute rather than walking the stepper again — which is exactly what TODO
    item A asks for and what "re-read the lesson" was standing in for.

    Published-only, exactly like ``LessonDetailView``: a draft lesson, course, word, rule
    or sentence is not reachable here either. Nothing is written on arrival.

    It also offers the same completion action the journey's last step does, through the
    same endpoint: reading the lesson the short way has to count as reading it, or the
    day's first step could only ever be finished by walking all eight screens. The
    learner's stored progress is handed over for the same reason the journey hands it
    over — so the button knows whether it is already done.
    """

    template_name = "lessons/lesson_review.html"

    def get(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course__language_level"),
            pk=pk, is_published=True, course__is_published=True,
        )
        review = build_review(lesson)
        # The vocabulary rows carry the one label each word earns for *this* learner, so
        # they are built here, where the request's user is known (vocabulary/status.py).
        word_rows = vocabulary_status.word_rows(review["words"], request.user, timezone.now())

        # The learner's own progress, or None for a visitor we cannot identify — the same
        # payload the dashboard and the journey already ship.
        progress = None
        if request.user.is_authenticated:
            progress = progress_state(request.user)

        return render(
            request,
            self.template_name,
            {
                "lesson": lesson,
                "review": review,
                "word_rows": word_rows,
                "progress_state": progress,
            },
        )


class LessonCheckView(LoginRequiredMixin, View):
    """«این درس را می‌دانم»: a short sample check from the lesson's own questions.

    The journey teaches a lesson in eight screens, which is the right way to learn it and a
    long way to walk for a learner who already knows the material. This page asks a handful
    of the lesson's own real questions (``lessons/check.py``) and, when they pass, offers to
    record the lesson as read — the same endpoint the finish button posts to, so the check
    is a second way to *prove* the lesson was read, not a way to skip the record.

    Login-only, like the finish button and for the same reason: the completion is a
    LessonProgress row, and a visitor we cannot identify has nowhere to store one. The
    answers themselves are graded and recorded by the ordinary ``ExerciseSubmitView``.
    """

    template_name = "lessons/lesson_check.html"

    def get(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course__language_level"),
            pk=pk, is_published=True, course__is_published=True,
        )

        questions = check_questions(lesson)
        rows = question_rows(questions)

        # A fresh check pre-reads no hint strength: a hint still appears the moment a miss
        # earns one, carried by the submission's own response (the same rule the daily
        # session follows).
        for row in rows:
            row["hint_strength"] = 0

        return render(
            request,
            self.template_name,
            {
                "lesson": lesson,
                "questions": rows,
                "total_questions": len(rows),
                "pass_needed": pass_needed(len(rows)),
            },
        )


class PracticePathView(View):
    """«مسیر امروز»: today's practice as one node per skill, plus the level header.

    This is the page the owner asked for in place of a lesson's exercise wall: instead of
    listing all 31 exercises, it shows a short path — one node per skill the lesson
    actually has material for — and where the learner is inside it
    (``lessons/skill_path.py`` owns the grouping and the rules).

    Public, like every other learner page except the profile: a visitor without an
    account has no ``LessonProgress`` and no attempts, so there is nothing to plan from.
    They are shown the page's explanation rather than a redirect — ``path`` is ``None``
    for them, exactly the way the dashboard's ``board`` is.

    Nothing is written on arrival: XP moves only when an answer is recorded.
    """

    template_name = "practice_path.html"

    def get(self, request, *args, **kwargs):
        # The same board the dashboard renders, built by the same function: one answer to
        # «what is today», so «مسیر امروز» and the home page cannot drift apart.
        board = today_board(request.user, timezone.localdate(), STEP_SIZE)

        profile = None
        badges = []
        if request.user.is_authenticated:
            profile = UserProfile.objects.filter(user=request.user).first()
            # Only the badges actually earned, derived from rows that already exist
            # (accounts/badges.py). An empty list for a visitor — never a locked grid.
            badges = badges_for(request.user, profile)

        return render(
            request,
            self.template_name,
            {
                "path": board["path"],
                # The steps of one guided day (مرور → درس → تمرین → آزمون) with the one to
                # start on, or None for a visitor we cannot identify.
                "day": board["day"],
                # Only the badges actually earned, derived from rows that already exist
                # (accounts/badges.py). An empty list for a visitor — never a locked grid.
                "badges": badges,
                # None for a visitor, so the header is omitted rather than shown empty.
                "xp": xp.summary(profile),
            },
        )


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
