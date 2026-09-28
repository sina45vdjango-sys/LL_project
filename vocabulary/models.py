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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "word"],
                name="unique_user_word_progress",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.word}"
