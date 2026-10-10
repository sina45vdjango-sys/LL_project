from django.db import models
from django.conf import settings

class Word(models.Model):
    """A German vocabulary word."""

    class WordType(models.TextChoices):
        NOUN = "NOUN", "Noun"
        VERB = "VERB", "Verb"
        ADJECTIVE = "ADJECTIVE", "Adjective"
        ADVERB = "ADVERB", "Adverb"
        PREPOSITION = "PREPOSITION", "Preposition"
        PRONOUN = "PRONOUN", "Pronoun"
        OTHER = "OTHER", "Other"

    class Gender(models.TextChoices):
        MASCULINE = "M", "Masculine (der)"
        FEMININE = "F", "Feminine (die)"
        NEUTER = "N", "Neuter (das)"

    class PerfectAuxiliary(models.TextChoices):
        HABEN = "HABEN", "Haben"
        SEIN = "SEIN", "Sein"

    word = models.CharField(
        max_length=200,
        help_text="The German word in its basic form.",
    )

    word_type = models.CharField(
        max_length=20,
        choices=WordType.choices,
        default=WordType.OTHER,
    )

    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        blank=True,
        null=True,
        help_text="Only used for nouns.",
    )

    article = models.CharField(
        max_length=3,
        blank=True,
        help_text="der, die, or das",
    )

    plural = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Plural form of the word.",
    )

    meaning_fa = models.CharField(max_length=500)

    meaning_en = models.CharField(
        max_length=500,
        blank=True,
    )

    pronunciation = models.CharField(
        max_length=200,
        blank=True,
    )

    is_separable = models.BooleanField(
        default=False,
    )

    perfect_auxiliary = models.CharField(
        max_length=5,
        choices=PerfectAuxiliary.choices,
        blank=True,
        null=True,
    )

    is_exam_important = models.BooleanField(
        default=False,
        help_text=(
            "The A1 exam asks the learner to produce this word's form, not only to "
            "recognise its meaning: a separable verb, a verb with `sein` in the "
            "perfect, or a noun whose plural takes an umlaut. `import_a1_words` sets it "
            "from the word's own data, and the lesson vocabulary row shows it as its "
            "«مهم برای آزمون» label."
        ),
    )

    level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.PROTECT,
        related_name="words",
    )

    audio = models.FileField(
        upload_to="words/audio/",
        blank=True,
        null=True,
    )

    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["word"]

        constraints = [
            models.UniqueConstraint(
                fields=["word", "word_type", "gender"],
                name="unique_word_type_gender",
            ),
        ]

    # Persian labels for the learner-facing pages. `get_word_type_display()` stays English
    # because the admin uses it. Properties only — no field, so no migration. One
    # definition, used by the word list, the word page, the lesson word cards and the
    # lookup popover.
    TYPE_LABELS = {
        WordType.NOUN: "اسم",
        WordType.VERB: "فعل",
        WordType.ADJECTIVE: "صفت",
        WordType.ADVERB: "قید",
        WordType.PREPOSITION: "حرف اضافه",
        WordType.PRONOUN: "ضمیر",
        WordType.OTHER: "سایر",
    }
    GENDER_LABELS = {
        Gender.MASCULINE: "مذکر",
        Gender.FEMININE: "مؤنث",
        Gender.NEUTER: "خنثی",
    }

    @property
    def type_label(self):
        if self.word_type in self.TYPE_LABELS:
            return self.TYPE_LABELS[self.word_type]
        return self.get_word_type_display()

    @property
    def gender_label(self):
        """Empty for words that have no gender (anything but a noun)."""
        if self.gender in self.GENDER_LABELS:
            return self.GENDER_LABELS[self.gender]
        return ""

    def __str__(self):
        if self.article:
            return f"{self.article} {self.word} ({self.word_type})"
        return f"{self.word} ({self.word_type})"

class Grammar(models.Model):
    title = models.CharField(max_length=200)
    explanation = models.TextField()
    level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.PROTECT,
        related_name="grammars",
    )
    audio = models.FileField(upload_to="grammars/audio/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
    # Examples live in Sentence (linked via LessonSentence), not in this text.

    class Meta:
        ordering = ["level__order", "title"]

    def __str__(self):
        return self.title


class Sentence(models.Model):
    """Reusable in lessons, grammar examples, listening, and questions."""

    text = models.TextField()
    translation_fa = models.TextField()
    level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.PROTECT,
        related_name="sentences",
    )
    audio = models.FileField(upload_to="sentences/audio/", blank=True, null=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["level__order", "id"]

    def __str__(self):
        return self.text


class WordProgress(models.Model):
    """One learner's spaced-repetition state for one word.

    The counters (``attempt_count``/``correct_count``/``wrong_count`` and the ``last_*_at``
    stamps) say how the word has gone so far. The scheduling fields say what to do about
    it: a state, the interval it is on, an ease value, and how many times it has been
    repeated or failed. ``vocabulary/schedule.py`` owns the arithmetic; this model only
    stores the result.
    """

    class State(models.TextChoices):
        NEW = "NEW", "New"
        LEARNING = "LEARNING", "Learning"
        REVIEW = "REVIEW", "Review"
        RELEARNING = "RELEARNING", "Relearning"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="word_progress",
    )

    word = models.ForeignKey(
        "Word",
        on_delete=models.CASCADE,
        related_name="user_progress",
    )

    attempt_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times the user has been tested on this word.",
    )

    correct_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of correct answers for this word.",
    )

    wrong_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of wrong answers for this word.",
    )

    last_attempted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_correct_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_wrong_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    due_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this word should next be reviewed.",
    )

    state = models.CharField(
        max_length=12,
        choices=State.choices,
        default=State.NEW,
        help_text="Where this word stands in the review schedule.",
    )

    interval_days = models.PositiveIntegerField(
        default=0,
        help_text="The gap this word is currently on, in days. 0 means never scheduled.",
    )

    ease = models.FloatField(
        default=2.5,
        help_text=(
            "How easily this word is recalled; the multiplier the next interval is built "
            "from. Bounded by vocabulary/schedule.py (1.3 … 2.8)."
        ),
    )

    repetitions = models.PositiveIntegerField(
        default=0,
        help_text="How many times this word has been answered correctly.",
    )

    lapses = models.PositiveIntegerField(
        default=0,
        help_text="How many times a word already in review was failed and fell to relearning.",
    )

    consecutive_correct = models.PositiveIntegerField(
        default=0,
        help_text="How many correct answers in a row, from the most recent answer backwards.",
    )

    consecutive_wrong = models.PositiveIntegerField(
        default=0,
        help_text="How many wrong answers in a row, from the most recent answer backwards.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "word"],
                name="unique_user_word_progress",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.word}"
