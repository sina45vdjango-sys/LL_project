"""Project-wide template guards.

This app has no views of its own. It is the home for checks that belong to the whole
project rather than to one feature app.

Run with::

    python manage.py test tests
"""

import pathlib
import re

from django.apps import apps
from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase

#: An inline template comment `{# … #}` that spans more than one line.
#:
#: Django's `{# #}` tag is **single line only**. A multi-line one is not a comment at
#: all: Django passes it through as literal text and the browser shows it to the
#: learner. Phase 0 found this leaking 110 times on a single lesson page, and one of
#: the leaked blocks contained the characters `<audio>` — the browser then parsed a
#: stray media element that swallowed the real audio controls, so every play button
#: was dead. It is easy to reintroduce, so it is checked here.
#:
#: Use `{% comment %} … {% endcomment %}` for anything longer than one line.
MULTILINE_INLINE_COMMENT = re.compile(r"\{#[^#{}]*\n[^#]*?#\}")


def template_paths():
    """Every template Django can load: the project's own, plus each app's."""
    roots = [pathlib.Path(settings.BASE_DIR) / "templates"]
    for app_config in apps.get_app_configs():
        app_templates = pathlib.Path(app_config.path) / "templates"
        if app_templates.is_dir():
            roots.append(app_templates)
    return sorted(path for root in roots for path in root.rglob("*.html"))


class TemplateCommentTests(SimpleTestCase):
    def test_no_template_contains_a_multiline_inline_comment(self):
        offenders = []
        for path in template_paths():
            text = path.read_text(encoding="utf-8")
            for match in MULTILINE_INLINE_COMMENT.finditer(text):
                line = text[: match.start()].count("\n") + 1
                first = match.group(0).splitlines()[0][:70]
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{line}  {first}")

        self.assertEqual(
            offenders,
            [],
            "These multi-line {# #} comments are rendered as visible text on the page. "
            "Use {% comment %} … {% endcomment %} instead:\n  " + "\n  ".join(offenders),
        )


class ErrorPageTests(SimpleTestCase):
    """The custom 404 and 500 pages must render.

    They only appear when `DEBUG = False`, so the development server never shows them to
    anyone — which means a broken one could ship unnoticed. The 500 in particular is
    rendered by Django with **no context at all**, so it is rendered that way here too.
    """

    def test_not_found_page_renders(self):
        html = render_to_string("404.html")
        self.assertIn("error-page", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)

    def test_server_error_page_renders_without_a_context(self):
        html = render_to_string("500.html")
        self.assertIn("error-page", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)
