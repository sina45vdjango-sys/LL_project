from django.db import models
from django.conf import settings

from exams.sections import Section


class Exercise(models.Model):
    class ExerciseType(models.TextChoices):
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
        TRANSLATION = "TRANSLATION", "Translation"
        FILL_BLANK = "FILL_BLANK", "Fill in the Blank"
        LISTENING = "LISTENING", "Listening"
        READING = "READING", "Reading"
        TRUE_FALSE = "TRUE_FALSE", "True / False"
        SPEAKING = "SPEAKING", "Speaking"
        WRITING = "WRITING", "Writing"
        SCRAMBLE = "SCRAMBLE", "Scramble"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    title = models.CharField(max_length=200)
    instruction = models.TextField(blank=True)

    type = models.CharField(
        max_length=20,
        choices=ExerciseType.choices,
    )

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )

    order = models.PositiveIntegerField()

    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["lesson_id", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "order"],
                name="unique_exercise_order_per_lesson",
            ),
        ]

    # Persian labels for the learner-facing pages. `get_type_display()` /
    # `get_difficulty_display()` stay English because the admin uses them. Properties
    # only — no field, so no migration. One definition, used by the exercise list, the
    # exercise page and the lesson journey's practice step.
    TYPE_LABELS = {
        ExerciseType.MULTIPLE_CHOICE: "چندگزینه‌ای",
        ExerciseType.TRANSLATION: "ترجمه",
        ExerciseType.FILL_BLANK: "جای خالی",
        ExerciseType.LISTENING: "شنیدن",
        ExerciseType.READING: "خواندن",
        ExerciseType.TRUE_FALSE: "درست / نادرست",
        ExerciseType.SPEAKING: "گفتن",
        ExerciseType.WRITING: "نوشتن",
        ExerciseType.SCRAMBLE: "مرتب کردن جمله",
    }
    DIFFICULTY_LABELS = {
        Difficulty.EASY: "آسان",
        Difficulty.MEDIUM: "متوسط",
        Difficulty.HARD: "سخت",
    }

    @property
    def type_label(self):
        if self.type in self.TYPE_LABELS:
            return self.TYPE_LABELS[self.type]
        return self.get_type_display()

    @property
    def difficulty_label(self):
        if self.difficulty in self.DIFFICULTY_LABELS:
            return self.DIFFICULTY_LABELS[self.difficulty]
        return self.get_difficulty_display()

    def __str__(self):
        return f"{self.lesson} – {self.title}"


class Question(models.Model):
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    prompt = models.TextField()

    #: The exam section this question was curated for, or blank for practice-only.
    #:
    #: The mock exam's paper is drawn from these rows and from nothing else. Before this
    #: field existed the paper was "every published question that fits the skill", which
    #: meant a newly generated drill silently changed the exam — the audit found a reading
    #: generator supplying a third of LESEN. Now the exam only moves when someone marks a
    #: question on purpose, and the marks live in ``exams/data/a1_exam_items.json``.
    #:
    #: The codes come from ``exams/sections.py``, which both this app and the exams app can
    #: import without a circular import. Blank is the default and the normal case: almost
    #: every question in the database is practice content.
    exam_section = models.CharField(
        max_length=20,
        choices=Section.choices,
        blank=True,
    )

    audio = models.FileField(
        upload_to="questions/audio/",
        blank=True,
    )

    image = models.FileField(
        upload_to="questions/images/",
        blank=True,
    )

    order = models.PositiveIntegerField()

    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["exercise", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["exercise", "order"],
                name="unique_question_order_per_exercise",
            ),
        ]

    def __str__(self):
        return f"{self.exercise} – Q{self.order}"


class QuestionTarget(models.Model):
    class Role(models.TextChoices):
        TESTED_ITEM = "TESTED_ITEM", "Tested Item"
        # The grammar rule the question exercises, when it exercises one. A question can
        # test a word *and* exercise a rule — "which article does Abend take?" asks for
        # a stored fact and for the Artikel rule at once — so the rule needs a role of
        # its own: `unique_tested_item_per_question` allows only one TESTED_ITEM row per
        # question, and `CONTEXT` means words the question merely uses.
        GRAMMAR = "GRAMMAR", "Grammar"
        CONTEXT = "CONTEXT", "Context"
        PROMPT = "PROMPT", "Prompt"

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="targets",
    )

    word = models.ForeignKey(
        "vocabulary.Word",
        on_delete=models.CASCADE,
        related_name="question_targets",
        blank=True,
        null=True,
    )

    grammar = models.ForeignKey(
        "vocabulary.Grammar",
        on_delete=models.CASCADE,
        related_name="question_targets",
        blank=True,
        null=True,
    )

    sentence = models.ForeignKey(
        "vocabulary.Sentence",
        on_delete=models.CASCADE,
        related_name="question_targets",
        blank=True,
        null=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TESTED_ITEM,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        word__isnull=False,
                        grammar__isnull=True,
                        sentence__isnull=True,
                    )
                    | models.Q(
                        word__isnull=True,
                        grammar__isnull=False,
                        sentence__isnull=True,
                    )
                    | models.Q(
                        word__isnull=True,
                        grammar__isnull=True,
                        sentence__isnull=False,
                    )
                ),
                name="questiontarget_exactly_one_target",
            ),

            # A question can have only one Tested Item.
            models.UniqueConstraint(
                fields=["question", "role"],
                condition=models.Q(role="TESTED_ITEM"),
                name="unique_tested_item_per_question",
            ),
        ]

    def __str__(self):
        # Exactly one of the three targets is set (see the check constraint above).
        if self.word:
            target = self.word
        elif self.grammar:
            target = self.grammar
        else:
            target = self.sentence
        return f"{self.question} → {self.role}: {target}"


class Answer(models.Model):
    class MatchType(models.TextChoices):
        EXACT = "EXACT", "Exact"
        ANY_OF = "ANY_OF", "Any of"
        CONTAINS = "CONTAINS", "Contains"

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    text = models.CharField(max_length=500)

    is_correct = models.BooleanField(default=False)

    match_type = models.CharField(
        max_length=10,
        choices=MatchType.choices,
        default=MatchType.EXACT,
    )

    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["question_id", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "order"],
                name="unique_answer_order_per_question",
            ),
        ]

    def __str__(self):
        return f"{self.question} – {self.text}"

class ExerciseAttempt(models.Model):
    """One learner's answer to one question.

    A new row is written for every submission, so the history is never overwritten.
    How the learner answered is stored one of two ways:

    * ``answer`` — the option they picked, for the questions that are answered by
      choosing one of the authored options (MULTIPLE_CHOICE, TRUE_FALSE, READING,
      and FILL_BLANK questions that were authored with distractors).
    * ``response_text`` — what they typed, for the questions that are answered by
      typing (TRANSLATION, and FILL_BLANK questions without distractors). Those
      questions have exactly one ``Answer`` row — the correct one — so a wrong
      typed answer has no row to point at, and the text is kept here instead.

    Exactly one of the two is filled for a graded answer.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_attempts",
    )

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="attempts",
        blank=True,
        null=True,
    )

    response_text = models.CharField(
        max_length=500,
        blank=True,
        help_text="The typed answer, for questions that are not answered by choosing an option.",
    )

    is_correct = models.BooleanField()

    response_time = models.FloatField(
        blank=True,
        null=True,
        help_text="Response time in seconds",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        verdict = "correct" if self.is_correct else "wrong"
        return f"{self.user} → {self.question} ({verdict})"