"""The exam mode's stored facts: one sitting of the written mock exam.

There is deliberately **no score field** here. A run stores what it asked
(``ExamRunQuestion``) and, per question, whether the learner got it right; the score is
arithmetic on those rows (``exams/paper.py``). Two reasons:

* the official score is a count of points per section, so it must be derivable from the
  answers rather than typed in beside them;
* a finished run has to stay the run it was. If the score were read from the learner's
  current practice state, answering the same question again next week would silently
  rewrite last week's exam.

``ExerciseAttempt`` still holds every submission the exam mode makes, exactly like any
other practice, so the review plan, «آمادگی من» and «امروز» see the mock exam's answers.
"""

from django.conf import settings
from django.db import models

from .sections import Section


class ExamRun(models.Model):
    """One sitting of the written exam: 45 questions on a single 65-minute clock.

    ``finished_at`` is the only state a run has. It is ``None`` while the learner is
    inside the exam; once it is set the run is a closed record and the page shows what
    the sitting was worth instead of the runner.

    A run belongs to one learner, and both the run page and the submission endpoint only
    ever find a run through its owner — reading somebody else's run is not a permission
    question, it is a 404.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_runs",
    )

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at", "-pk"]

    def __str__(self):
        return f"{self.user} – {self.started_at:%Y-%m-%d %H:%M}"


class ExamRunQuestion(models.Model):
    """One question as it was really asked in one run, and how it went.

    ``order`` counts 1..45 across the whole paper, so the run is one sequence, and
    ``section`` is stored rather than read back out of the question's exercise: the paper
    a run was built from has to stay readable even after the content it was drawn from is
    edited. The codes themselves live in ``exams/sections.py``, because
    ``Question.exam_section`` has to use the same ones and the exercises app cannot
    import this module.

    ``is_correct`` is ``None`` until the learner answers, and it is a snapshot on purpose:
    a finished run's score must not move when the same question is practised again later.
    """

    run = models.ForeignKey(
        ExamRun,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    question = models.ForeignKey(
        "exercises.Question",
        on_delete=models.CASCADE,
        related_name="exam_runs",
    )

    section = models.CharField(
        max_length=20,
        choices=Section.choices,
    )

    order = models.PositiveIntegerField()

    is_correct = models.BooleanField(blank=True, null=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "question"],
                name="unique_question_per_exam_run",
            ),
            models.UniqueConstraint(
                fields=["run", "order"],
                name="unique_order_per_exam_run",
            ),
        ]

    def __str__(self):
        return f"run {self.run_id} #{self.order} ({self.section})"
