from django.db import models


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

    def __str__(self):
        article = f"{self.article} " if self.article else ""
        return f"{article}{self.word} ({self.word_type})"

class Grammar(models.Model):
    title = models.CharField(max_length=200)
    explanation = models.TextField()
    level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.PROTECT,
        related_name="grammars",
    )
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