from django.db import models


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

    def __str__(self):
        return f"{self.lesson} – {self.title}"


class Question(models.Model):
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    prompt = models.TextField()

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
        target = self.word or self.grammar or self.sentence
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
