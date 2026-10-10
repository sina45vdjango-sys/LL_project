from django.contrib.auth.models import User
from django.db import models

from .xp import level_of, xp_percent

class UserProfile(models.Model):
    """Extending django's User model.

    This is also the learner's **goal**: what they are learning German for, where they
    want to get to, and by when. The four fields are deliberately the smallest set that
    lets the product answer "how far have I got and how much time do I have?" — see
    ``lessons/readiness.py`` for the arithmetic, which is done at read time and never
    stored, so a goal can be changed without rewriting any history.
    """

    class Reason(models.TextChoices):
        AUSBILDUNG = "AUSBILDUNG", "Ausbildung"
        UNIVERSITY = "UNIVERSITY", "University"
        WORK = "WORK", "Work"
        MIGRATION = "MIGRATION", "Migration"
        GENERAL = "GENERAL", "General German"

    class Theme(models.TextChoices):
        # The stored value is already the string the page needs on <html>, so the
        # template reads `profile.theme` straight into `data-theme-mode` and no
        # second mapping has to be kept in step with this one.
        SYSTEM = "system", "System"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    current_level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.SET_NULL,
        related_name="user_profiles",
        blank=True,
        null=True,
    )
    target_level = models.ForeignKey(
        "lessons.LanguageLevel",
        on_delete=models.SET_NULL,
        related_name="target_profiles",
        blank=True,
        null=True,
        help_text="Where the learner wants to get to.",
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        blank=True,
        help_text="Why the learner is learning German.",
    )
    theme = models.CharField(
        max_length=10,
        choices=Theme.choices,
        default=Theme.SYSTEM,
        help_text="The colour scheme this learner prefers.",
    )
    target_date = models.DateField(
        blank=True,
        null=True,
        help_text="The day the learner wants to be ready by, if they have one.",
    )
    native_language = models.CharField(max_length=10, default="fa")
    created_at = models.DateTimeField(auto_now_add=True)

    # The practice path's feedback layer. Three stored numbers, no curve and no currency:
    # the arithmetic lives in ``accounts/xp.py`` and XP is only ever added, never spent.
    # Kept on the profile rather than in a table of their own because there is exactly one
    # row per learner and nothing here is history.
    xp = models.PositiveIntegerField(
        default=0,
        help_text="Points earned by answering. Levels are computed from this.",
    )
    streak_days = models.PositiveIntegerField(
        default=0,
        help_text="Days practised in a row, counted from the last recorded answer.",
    )
    last_practice_date = models.DateField(
        blank=True,
        null=True,
        help_text="The last day the learner answered anything, in the project's timezone.",
    )

    class Meta:
        ordering = ["-created_at"]

    # Persian labels for the learner-facing pages. `get_reason_display()` stays English
    # because the admin uses it. Properties only — one definition, used by the goal form's
    # read-only summary, the profile page, the dashboard and the readiness page.
    REASON_LABELS = {
        Reason.AUSBILDUNG: "آوسبیلدونگ",
        Reason.UNIVERSITY: "دانشگاه",
        Reason.WORK: "کار",
        Reason.MIGRATION: "مهاجرت",
        Reason.GENERAL: "آلمانی عمومی",
    }

    # The three choices on the profile page, in the order they are offered. Beside the
    # theme field because ``ThemeView`` validates the submitted value against these keys,
    # so the form, the labels and the validation cannot drift apart.
    THEME_LABELS = {
        Theme.SYSTEM: "سیستم",
        Theme.LIGHT: "روشن",
        Theme.DARK: "تاریک",
    }

    @property
    def reason_label(self):
        """The Persian name of the learner's reason, or "" when they have not said."""
        if self.reason in self.REASON_LABELS:
            return self.REASON_LABELS[self.reason]
        return ""

    @property
    def theme_label(self):
        """The Persian name of the learner's theme, or "" when the value is unusable."""
        if self.theme in self.THEME_LABELS:
            return self.THEME_LABELS[self.theme]
        return ""

    @property
    def level(self):
        """The learner's level, computed from ``xp`` and never stored.

        Read through ``accounts/xp.py`` so the curve has one definition; this property
        exists only so a template can write ``profile.level`` without importing it.
        """
        return level_of(self.xp)

    @property
    def xp_percent(self):
        """How full the level bar is, 0 to 100, read through ``accounts/xp.py``."""
        return xp_percent(self.xp)

    def __str__(self):
        return f"Profile of {self.user.username}"
