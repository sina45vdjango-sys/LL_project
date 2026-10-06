"""The exam pages: the shape of the exam, one sitting of it, and its score.

The exam is the one part of the product that asks for an account before it does anything,
and the reason is the same one «مرور واژه‌های دشوار» gives: a sitting is stored, and there
is nowhere to store it for a visitor we cannot identify. The index itself is public — the
official shape, the sections and the instruction words are content, not personal data —
and everything below that (start, run, submit, finish) belongs to one learner's own rows.

The scoring is never computed here. ``exams/paper.py`` marks the paper, and this module
only decides what to show; that keeps the official arithmetic in one place and testable
without a browser.
"""

import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from exercises.grading import grade
from exercises.models import ExerciseAttempt
from exercises.runner import question_rows
from vocabulary.progress import record_word_progress

from .models import ExamRun
from .paper import (
    build_paper,
    instruction_rows,
    open_run,
    paper_problems,
    remaining_minutes,
    score,
    spoken_practice,
    time_is_up,
)
from .spec import (
    DURATION_MINUTES,
    ITEMS_PER_SECTION,
    MAX_POINTS,
    PASS_POINTS,
    SCORE_FACTOR,
    SECTION_FACTS,
    SECTION_ORDER,
    SOURCE,
    SPOKEN_MAX_POINTS,
    SPRECHEN,
    WRITTEN_MAX_POINTS,
    WRITTEN_MINIMUM,
)
from .step import STEP_SIZE, step_questions

#: A response time longer than this is not worth storing — an hour on one question means
#: the tab sat open while the learner was away, not that they were thinking. The same rule
#: and the same limits as the exercise runner's, kept here rather than imported from a view
#: module: two short blocks that say the same thing are easier to follow than a view
#: reaching into another view's private helper.
MAX_RESPONSE_TIME = 3600


def response_time(value):
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


class ExamIndexView(View):
    """What the exam is, what a sitting does here, and how the last ones went.

    Public on purpose: the official shape, the sections, the scoring and the instruction
    words are the most useful thing this page has for a learner who has not signed up yet,
    and the leaning goal is a passed exam. Only the learner's own past sittings are
    personal, and they are simply not rendered for a visitor.
    """

    template_name = "exams/exam_index.html"

    def get(self, request, *args, **kwargs):
        sections = []
        for code in SECTION_ORDER:
            facts = SECTION_FACTS[code]
            sections.append({
                "code": code,
                "german": facts["german"],
                "label": facts["label"],
                "minutes": facts["minutes"],
                "items": facts["items"],
                "note": facts["note"],
            })

        running = None
        finished = []

        if request.user.is_authenticated:
            running = open_run(request.user)
            recent = ExamRun.objects.filter(user=request.user, finished_at__isnull=False)[:5]
            for run in recent:
                finished.append({"run": run, "score": score(run)})

        return render(request, self.template_name, {
            "sections": sections,
            "sprechen": SPRECHEN,
            "source": SOURCE,
            "items_per_section": ITEMS_PER_SECTION,
            "duration_minutes": DURATION_MINUTES,
            "written_max_points": WRITTEN_MAX_POINTS,
            "spoken_max_points": SPOKEN_MAX_POINTS,
            "max_points": MAX_POINTS,
            "pass_points": PASS_POINTS,
            "written_minimum": WRITTEN_MINIMUM,
            "score_factor": SCORE_FACTOR,
            "instructions": instruction_rows(),
            "problems": paper_problems(),
            "running": running,
            "finished": finished,
        })


class StepTestView(LoginRequiredMixin, View):
    """Concept 20 — the short station on the path, not a second exam.

    Twelve questions, four from each written skill, drawn by ``exams/step.py`` and run
    through the ordinary exercise runner: every answer is graded, recorded and scheduled
    exactly like any other practice, because that is what it is.

    It asks for an account for the same reason every other page that *records* does: the
    answers are stored, and there is nowhere to store them for a visitor we cannot
    identify. The page is short and skippable — the learner can walk away at any point and
    the answers already given still count, so nothing is wasted.

    There is no official score here on purpose (``exams/step.py`` says why), and the page
    says so rather than borrowing the full exam's numbers.
    """

    template_name = "exams/step_test.html"

    def get(self, request, *args, **kwargs):
        questions = step_questions(request.user, timezone.localdate())

        rows = []
        if questions is not None:
            rows = question_rows(questions)

        # A step test does not pre-read hint strength: the submission's own response
        # carries the strength a fresh mistake earns, so a hint still appears the moment
        # it is owed. The same rule the daily session follows.
        for row in rows:
            row["hint_strength"] = 0

        return render(request, self.template_name, {
            "questions": rows,
            "total_questions": len(rows),
            "step_size": STEP_SIZE,
            "source": SOURCE,
            "sections": SECTION_ORDER,
        })


class ExamStartView(LoginRequiredMixin, View):
    """Start a sitting, or hand back the one that is still open.

    Two guards, both about not producing a paper that cannot be scored like the real exam:
    an unfinished run is resumed instead of stacking a second one on top of it, and a
    content pool too thin for 15 questions per section refuses to start at all.
    """

    def get(self, request, *args, **kwargs):
        """The exam index, not a blank page.

        This address is the exam's start *button*, so it only ever accepts a form
        submission — and a ``GET`` used to answer 405 with an empty body, which is what a
        learner got by typing the address or reloading the page after starting. Sending
        them to the exam page is the honest answer: it is where the button, the shape of
        the exam and the score of a half-finished sitting all live, and it shows the way
        back into an unfinished run.
        """
        return redirect("exams:exam-index")

    def post(self, request, *args, **kwargs):
        running = open_run(request.user)
        if running is not None:
            return redirect("exams:exam-run", pk=running.pk)

        if paper_problems():
            return redirect("exams:exam-index")

        # One transaction, so a paper that cannot be built leaves no half-made sitting
        # behind. Without it a failure here stored an empty run, and the learner's next
        # visit resumed that empty run instead of starting a real exam.
        with transaction.atomic():
            run = ExamRun.objects.create(user=request.user)
            build_paper(run)

        return redirect("exams:exam-run", pk=run.pk)


class ExamRunView(LoginRequiredMixin, View):
    """One sitting: the paper while it is open, and what it was worth once it is closed.

    The paper is rendered in full, question by question, exactly as the exercise runner
    renders an exercise — the same ``exercises/runner.py`` shapes and the same client-side
    module, because "how a question is answered" must not have two definitions. The clock
    is the run's own ``started_at``, so the deadline is the server's and the timer in the
    browser is only a display of it.

    A run is found through its owner, so another learner's sitting is a 404 rather than a
    page that happens not to show it.
    """

    template_name = "exams/exam_run.html"

    def get(self, request, pk, *args, **kwargs):
        run = get_object_or_404(ExamRun.objects.select_related("user"), pk=pk, user=request.user)

        if run.finished_at is not None:
            return render(request, self.template_name, self.finished_context(run))

        return render(request, self.template_name, self.open_context(run))

    def finished_context(self, run):
        """What the closed sitting was worth, and what was missed in it."""
        data = score(run)

        missed = []
        rows = run.questions.select_related("question").order_by("order")
        for row in rows:
            if row.is_correct is not False:
                continue
            missed.append({
                "order": row.order,
                "section_label": SECTION_FACTS[row.section]["label"],
                "prompt": row.question.prompt,
            })

        return {
            "run": run,
            "result": data,
            "missed": missed,
            "sprechen": SPRECHEN,
            "score_factor": SCORE_FACTOR,
            "source": SOURCE,
        }

    def open_context(self, run):
        """The paper itself, in one sequence, with the section each question belongs to."""
        rows = list(
            run.questions.select_related("question__exercise")
            .prefetch_related("question__answers", "question__targets__sentence")
            .order_by("order")
        )

        drawn = []
        for row in rows:
            drawn.append(row.question)

        questions = question_rows(drawn)

        for row, question in zip(rows, questions):
            facts = SECTION_FACTS[row.section]
            question["section"] = row.section
            question["section_label"] = facts["label"]
            question["section_german"] = facts["german"]

        minutes_left = remaining_minutes(run)
        expired = time_is_up(run)

        # The sections this paper actually has, with their sizes, for the bar the learner
        # reads before starting: a rundown of what is coming rather than a claim about the
        # official exam.
        sections = []
        for section in SECTION_ORDER:
            asked = 0
            for question in questions:
                if question["section"] == section:
                    asked += 1
            if asked == 0:
                continue
            sections.append({
                "german": SECTION_FACTS[section]["german"],
                "label": SECTION_FACTS[section]["label"],
                "asked": asked,
            })

        return {
            "run": run,
            "questions": questions,
            "sections": sections,
            "total_questions": len(questions),
            "minutes_left": minutes_left,
            # The deadline is handed to the browser as an instant, not as a countdown: a
            # timer that started when the page loaded would give back the seconds a slow
            # page load, a refresh or a closed tab cost the learner.
            "deadline": run.started_at + timedelta(minutes=DURATION_MINUTES),
            "expired": expired,
            "source": SOURCE,
        }


class ExamSubmitView(LoginRequiredMixin, View):
    """One answer inside one sitting: graded, recorded, and written onto the paper.

    The verdict comes from ``exercises/grading.py`` — the same rule as every other answer
    in the product — and the submission is stored twice on purpose: as an
    ``ExerciseAttempt``, so review, readiness and «امروز» treat the exam as the practice it
    is, and as the ``is_correct`` snapshot on the run's own question row, so the sitting's
    score stays the sitting's score.

    Answers are refused once the clock has run out. The exam is timed, and a deadline the
    browser enforces alone is not a deadline.
    """

    def post(self, request, pk, *args, **kwargs):
        run = get_object_or_404(ExamRun, pk=pk, user=request.user)

        if run.finished_at is not None:
            return JsonResponse({"error": "exam is finished"}, status=400)

        if time_is_up(run):
            return JsonResponse({"error": "time is up"}, status=400)

        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        row = run.questions.filter(question=payload.get("question")).first()
        if row is None:
            return JsonResponse({"error": "unknown question"}, status=400)

        question = row.question

        verdict = grade(question, payload.get("answer"), payload.get("response_text"))
        if verdict is None:
            return JsonResponse({"error": "question cannot be graded"}, status=400)

        row.is_correct = verdict["is_correct"]
        row.save(update_fields=["is_correct"])

        ExerciseAttempt.objects.create(
            user=request.user,
            exercise=question.exercise,
            question=question,
            answer=verdict["answer"],
            response_text=verdict["response_text"],
            is_correct=verdict["is_correct"],
            response_time=response_time(payload.get("response_time")),
        )
        record_word_progress(request.user, question, verdict["is_correct"])

        return JsonResponse(
            {
                "correct": verdict["is_correct"],
                "correct_answer": verdict["correct_answer_id"],
                "expected": verdict["expected"],
                "explanation": question.explanation,
                "recorded": True,
            }
        )


class ExamFinishView(LoginRequiredMixin, View):
    """Close a sitting and hand back where its result is.

    Closing is idempotent: the browser's timer and the learner's own button both end up
    here, and whichever arrives second must not move the ``finished_at`` that the score
    was computed from.
    """

    def post(self, request, pk, *args, **kwargs):
        run = get_object_or_404(ExamRun, pk=pk, user=request.user)

        if run.finished_at is None:
            run.finished_at = timezone.now()
            run.save(update_fields=["finished_at"])

        return JsonResponse({
            "finished": True,
            "url": reverse("exams:exam-run", args=[run.pk]),
        })


class SprechenView(View):
    """The oral section as a rehearsal, because it is the one part nothing here can grade.

    The page is public and honest about the asymmetry: HÖREN, LESEN and SCHREIBEN are
    counted on the exam pages, and this part is 15 points of the official 100 that this
    product can describe but not mark. What it can do is make sure the phrases are
    practised — each phrase points at the real questions about the course sentence it
    matches, where such a sentence exists.
    """

    template_name = "exams/sprechen.html"

    def get(self, request, *args, **kwargs):
        parts = spoken_practice(SPRECHEN["parts"])

        # How many phrases the self-report can be about, counted from the same list the
        # page renders, so the counter can never claim more than is on the page.
        phrase_total = 0
        for part in parts:
            phrase_total += len(part["phrases"])

        return render(request, self.template_name, {
            "sprechen": SPRECHEN,
            "parts": parts,
            "phrase_total": phrase_total,
            "source": SOURCE,
            "pass_points": PASS_POINTS,
            "max_points": MAX_POINTS,
        })
