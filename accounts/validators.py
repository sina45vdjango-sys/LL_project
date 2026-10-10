"""The one password rule that Django cannot say in Persian.

``AUTH_PASSWORD_VALIDATORS`` uses Django's own validators, and three of the four already
speak Persian: Django's ``fa`` catalog translates "too common", "entirely numeric" and
"too similar". The minimum-length one does not land, and the learner sees raw English
inside an otherwise Persian form: the source string in Django is
``"... at least %d characters."`` while the catalog's entry for it is written with
``%(min_length)d``, so the two never match and the translation is skipped.

That is upstream data, not something this project can correct. So the message the product
wants is stated here instead — one class, referenced from ``AUTH_PASSWORD_VALIDATORS``, so
every caller of ``validate_password`` gets it rather than each form re-writing the rule.
"""

from django.contrib.auth.password_validation import MinimumLengthValidator

from .jalali import persian_number


class PersianMinimumLengthValidator(MinimumLengthValidator):
    """Django's minimum length rule, with the message written in Persian."""

    def get_error_message(self):
        return f"گذرواژه باید حداقل {persian_number(self.min_length)} نویسه باشد."
