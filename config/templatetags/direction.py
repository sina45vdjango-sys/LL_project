"""The ``direction`` template filter — explicit language direction for mixed text.

Registered in ``settings.TEMPLATES[0]["OPTIONS"]["builtins"]``, so every template can use
``{{ value|direction }}`` without a ``{% load %}``. Direction is a property of the
content everywhere in this product, not of one app's templates.

What it does is defined in ``vocabulary/text_direction.py``; this module is only the
template-facing wrapper that marks the result safe, because the text is escaped piece by
piece inside that module.
"""

from django import template
from django.utils.safestring import mark_safe

from vocabulary.text_direction import rendered

register = template.Library()


@register.filter(name="direction")
def direction(value):
    """Render ``value`` with one isolated, explicitly directed run per language.

    Safe to chain with ``linebreaks`` / ``linebreaksbr``: the result is marked safe, and
    those filters leave already-safe text alone, so the ``<bdi>`` tags survive while the
    line structure is turned into paragraphs and ``<br>``.
    """
    if value is None:
        return ""
    return mark_safe(rendered(value))
