"""The ``jalali`` template filter — one stored date, written the way it is read.

Registered in ``settings.TEMPLATES[0]["OPTIONS"]["builtins"]``, like ``direction``, so any
template can write ``{{ value|jalali }}`` without a ``{% load %}``.

The date itself stays Gregorian in the database (``UserProfile.target_date``) and in every
calculation about it; this only changes how it is *shown*. The conversion lives in
``accounts/jalali.py``, and so does the reason for it — the browser's own date picker speaks
the browser's locale, so a Persian speaker should not have to read a Gregorian date back.
"""

from django import template

from accounts.jalali import format_date

register = template.Library()


@register.filter(name="jalali")
def jalali(value):
    """``value`` as a Jalali date in Persian digits, or ``""`` when there is no date."""
    if not value:
        return ""

    return format_date(value)
