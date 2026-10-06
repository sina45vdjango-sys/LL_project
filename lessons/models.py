from django.conf import settings
from django.db import models


class LanguageLevel(models.Model):
    """A1, A2, B1, B2, C1, C2"""

    level = models.CharField(max_length=2, unique=True)
    title = models.CharField(max_length=40)
    order = models.PositiveIntegerField(unique=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.level


class Course(models.Model):
    """Each level has 1 course"""

    language_level = models.OneToOneField(LanguageLevel, on_delete=models.CASCADE, related_name="course")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # The Persian summary of the course, shown on the pages a Persian-speaking visitor
    # reads. `description` above is kept as the German/English one — the admin and the
    # export show it — and the same rule as Lesson applies: the Persian page shows the
    # Persian text, falling back to the other one only while a translation is missing.
    # An English paragraph on the front page of a Persian product read as unfinished, and
    # the audit found it as the only text that explained what the product is.
    description_fa = models.TextField(
        blank=True,
        help_text="Persian summary, shown on the learner pages. The other description stays as the course's own.",
    )
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["language_level__order"]

    @property
    def display_description(self):
        if self.description_fa:
            return self.description_fa
        return self.description

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=250)
    title_fa = models.CharField(
        max_length=250,
        blank=True,
        help_text=(
            "Persian title, shown as the lesson's own title on every learner page. "
            "The German title stays beside it as the lesson's German name."
        ),
    )
    description = models.TextField(blank=True)
    description_fa = models.TextField(
        blank=True,
        help_text="Persian one-line summary, shown under the title on the learner pages.",
    )
    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    estimated_time = models.PositiveIntegerField()

    # The Persian page shows a Persian title; the German one is the lesson's German
    # name and is displayed beside it, not instead of it. Falling back to the German
    # title means a lesson whose translation is not written yet still reads as itself
    # rather than as an empty heading. Properties only — the fields above are the data.
    @property
    def display_title(self):
        if self.title_fa:
            return self.title_fa
        return self.title

    @property
    def display_description(self):
        if self.description_fa:
            return self.description_fa
        return self.description

    class Meta:
        ordering = ["course", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_lesson_order_per_course",
            )
        ]

    def __str__(self):
        return f"{self.course} – {self.title}"


class LessonContent(models.Model):
    """Lesson blocks to make them easier to order instead of one big text field in the lesson"""

    class ContentType(models.TextChoices):
        EXPLANATION = "EXPLANATION", "Explanation"
        VOCABULARY = "VOCABULARY", "Vocabulary"
        GRAMMAR = "GRAMMAR", "Grammar"
        EXAMPLE = "EXAMPLE", "Example"
        DIALOGUE = "DIALOGUE", "Dialogue"
        NOTE = "NOTE", "Note"

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="contents",
    )
    type = models.CharField(max_length=20, choices=ContentType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    audio = models.FileField(upload_to="contents/audio/", blank=True, null=True)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["lesson", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "order"],
                name="unique_content_order_per_lesson",
            ),
        ]

    def __str__(self):
        return f"{self.lesson} – {self.order}. {self.title}"


class LessonWord(models.Model):
    """What are the words used in the lessons?"""

    class Role(models.TextChoices):
        NEW = "NEW", "New"
        REVIEW = "REVIEW", "Review"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_words")
    word = models.ForeignKey("vocabulary.Word", on_delete=models.CASCADE, related_name="lesson_links")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.NEW)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["lesson", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "word"],
                name="unique_word_per_lesson",
            ),
        ]

    def __str__(self):
        return f"{self.lesson} – {self.word}"


class LessonGrammar(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_grammars")
    grammar = models.ForeignKey("vocabulary.Grammar", on_delete=models.CASCADE, related_name="lesson_links")
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["lesson", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "grammar"],
                name="unique_grammar_per_lesson",
            ),
        ]

    def __str__(self):
        return f"{self.lesson} – {self.grammar}"


class LessonSentence(models.Model):
    class Role(models.TextChoices):
        EXAMPLE = "EXAMPLE", "Example"
        DIALOGUE = "DIALOGUE", "Dialogue"
        READING = "READING", "Reading"
        LISTENING = "LISTENING", "Listening"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_sentences")
    sentence = models.ForeignKey("vocabulary.Sentence", on_delete=models.CASCADE, related_name="lesson_links")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EXAMPLE)
    speaker = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["lesson", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "sentence"],
                name="unique_sentence_per_lesson",
            ),
        ]

    def __str__(self):
        return f"{self.lesson} – {self.sentence}"


class LessonProgress(models.Model):

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    class Step(models.TextChoices):
        INTRO = "intro", "Introduction"
        EXPLANATION = "explanation", "Explanation"
        VOCABULARY = "vocabulary", "Vocabulary"
        GRAMMAR = "grammar", "Grammar"
        EXAMPLES = "examples", "Examples"
        DIALOGUE = "dialogue", "Dialogue"
        READING = "reading", "Reading"
        LISTENING = "listening", "Listening"
        PRACTICE = "practice", "Practice"
        FINISH = "finish", "Finish"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )

    current_step = models.CharField(
        max_length=20,
        choices=Step.choices,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_activity_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="unique_user_lesson_progress",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.lesson} ({self.status})"