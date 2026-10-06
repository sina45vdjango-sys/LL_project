"""Project-wide template guards.

This app has no views of its own. It is the home for checks that belong to the whole
project rather than to one feature app.

Run with::

    python manage.py test tests
"""

import importlib
import os
import pathlib
import re
import tempfile

from django.apps import apps
from django.conf import settings
from django.template.loader import render_to_string
from django.http import Http404, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import clear_url_caches, resolve, reverse
from django.urls.exceptions import Resolver404
from django.utils.http import http_date

import config.urls
from config.media import serve_media
from config.middleware import MethodNotAllowedMiddleware

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


class DirectionAttributeTests(SimpleTestCase):
    """No template may hand direction to the browser's `dir="auto"` heuristic.

    Mixed Persian/German content gets explicit, isolated runs from the `direction`
    filter (``vocabulary/text_direction.py``). ``dir="auto"`` resolves from the first
    strong character of the element, which is exactly the guess that reorders a German
    sentence inside a Persian line. A pure-language field uses an explicit ``dir``;
    anything mixed uses the filter. This check keeps the heuristic from coming back.
    """

    def test_no_template_uses_dir_auto(self):
        offenders = []
        for path in template_paths():
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                if 'dir="auto"' in line:
                    offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{number}")

        self.assertEqual(
            offenders,
            [],
            "Pass the value through the `direction` filter, or set an explicit dir, "
            'instead of dir="auto":\n  ' + "\n  ".join(offenders),
        )


#: Nothing on the page may ask for text smaller than this. A phone held at arm's length
#: in a bright room is the device this course is studied on.
MINIMUM_FONT_SIZE_PX = 12.0


class FontSizeFloorTests(SimpleTestCase):
    """No stylesheet may declare text below 12px.

    The audit found the brand's Latin letters at 9px and 10–11px labels across the shell
    ("small caps" and chip text — which is exactly the text a learner reads at a glance).
    A Django test has no layout engine, so this reads the declarations out of the files:
    the number in the source is the thing that was wrong, and the thing that would come
    back. Files under ``design-prototypes/`` are not served and are not checked.
    """

    FONT_DECLARATION = re.compile(r"\bfont(?:-size)?\s*:\s*([^;{}]+)")
    PIXEL_SIZE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)px")

    def test_no_stylesheet_declares_text_below_the_floor(self):
        roots = {pathlib.Path(settings.BASE_DIR) / "static"}
        for app_config in apps.get_app_configs():
            app_static = pathlib.Path(app_config.path) / "static"
            if app_static.is_dir():
                roots.add(app_static)

        offenders = []
        for root in sorted(roots):
            for path in sorted(root.rglob("*.css")):
                text = path.read_text(encoding="utf-8")
                for declaration in self.FONT_DECLARATION.finditer(text):
                    for size in self.PIXEL_SIZE.finditer(declaration.group(1)):
                        if float(size.group(1)) < MINIMUM_FONT_SIZE_PX:
                            line = text[: declaration.start()].count("\n") + 1
                            relative = path.relative_to(settings.BASE_DIR)
                            offenders.append(f"{relative}:{line}  {declaration.group(0).strip()}")

        self.assertEqual(
            offenders,
            [],
            f"Raise these to at least {MINIMUM_FONT_SIZE_PX:.0f}px:\n  " + "\n  ".join(offenders),
        )


class ErrorPageTests(SimpleTestCase):
    """The custom 403, 404, 405 and 500 pages must render.

    They only appear when `DEBUG = False`, so the development server never shows them to
    anyone — which means a broken one could ship unnoticed. The 500 in particular is
    rendered by Django with **no context at all**, so it is rendered that way here too.

    403 and 404 are Django's own default views looking for a template of that name; 405
    has no default view at all and is rendered by ``config.middleware``, which is checked
    in ``MethodNotAllowedPageTests`` below.
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

    def test_permission_denied_page_renders(self):
        html = render_to_string("403.html")
        self.assertIn("error-page", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)

    def test_method_not_allowed_page_renders(self):
        html = render_to_string("405.html")
        self.assertIn("error-page", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)


class MethodNotAllowedPageTests(SimpleTestCase):
    """A 405 must be a page, not an empty body.

    Django ships default views for 403, 404 and 500 but **not** for 405: a view that only
    implements ``post`` answers a ``GET`` with an empty body, and a blank screen is the
    one answer from which a working site cannot be told apart. ``config.middleware``
    renders the site's own page instead — but only for a request that asked for HTML, so
    the JSON endpoints keep answering in JSON.
    """

    def handler(self, request):
        """A stand-in view: this request is not allowed, and nothing else."""
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    def test_a_browser_gets_the_page(self):
        # The theme form is POST-only, so opening its address by hand is exactly the case
        # that used to answer with an empty body. This goes through the real middleware
        # stack (a RequestFactory request has no `user`, and the shell context processor
        # reads it), which is why the client is used rather than calling the middleware
        # directly.
        response = self.client.get(
            reverse("accounts:theme"), HTTP_ACCEPT="text/html"
        )

        self.assertEqual(response.status_code, 405)
        self.assertContains(response, "error-page", status_code=405)
        self.assertContains(response, "\u06f4\u06f0\u06f5", status_code=405)

    def test_a_json_request_is_left_as_it_was(self):
        middleware = MethodNotAllowedMiddleware(self.handler)
        request = RequestFactory().get("/somewhere/", HTTP_ACCEPT="application/json")
        response = middleware(request)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content, b"")

    def test_another_status_is_untouched(self):
        from django.http import HttpResponse

        def ok(request):
            return HttpResponse("fine")

        middleware = MethodNotAllowedMiddleware(ok)
        request = RequestFactory().get("/somewhere/", HTTP_ACCEPT="text/html")
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"fine")


class FaviconTests(SimpleTestCase):
    """``/favicon.ico`` must answer with the product's icon, not 404.

    Every browser asks for this one address by itself, whether or not a page declares an
    icon, so a 404 here was logged on every single page load. The icon lives in one file
    and this route points at it rather than keeping a second copy that could fall out of
    date.
    """

    def test_the_address_resolves_and_points_at_the_icon(self):
        match = resolve("/favicon.ico")
        self.assertEqual(match.url_name, "favicon")

        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.FAVICON_PATH, response["Location"])

    def test_the_icon_the_redirect_points_at_exists(self):
        path = pathlib.Path(settings.BASE_DIR) / "static" / settings.FAVICON_PATH
        self.assertTrue(path.is_file(), f"missing icon: {path}")


def resolved_media_view(serve_media):
    """The view a /media/ path resolves to, with SERVE_MEDIA forced to a value.

    `config.urls` decides whether to route /media/ once, at import time, from
    ``settings.SERVE_MEDIA`` -- so checking either branch means rebuilding the module,
    and ``clear_url_caches`` is what makes the resolver notice. The rebuild is done
    again after the override has been undone, so the real URLconf is what the next test
    sees. Returns ``None`` when nothing routes the path.
    """
    with override_settings(SERVE_MEDIA=serve_media):
        importlib.reload(config.urls)
        clear_url_caches()
        try:
            match = resolve("/media/grammars/audio/example.mp3")
            view = match.func
        except Resolver404:
            view = None

    importlib.reload(config.urls)
    clear_url_caches()
    return view


class MediaServingTests(SimpleTestCase):
    """The generated audio is actually reachable when Django is asked to serve it.

    `runserver --insecure` covers /static/ only, and Django's own `static()` helper
    becomes a no-op once DEBUG is off, so before ``SERVE_MEDIA`` existed nothing served
    /media/ -- on a copy of the project handed to someone else, that meant every one of
    the ~1,500 audio files answered 404 while the pages still looked fine.

    The failure is silent, which is why it is checked here. ``MEDIA_URL`` reads back as
    "/media/" but patterns are matched without that leading slash, so an unstripped
    prefix produces a route that never matches anything.
    """

    def test_media_is_routed_when_serve_media_is_on(self):
        self.assertIs(resolved_media_view(True), serve_media)

    def test_media_is_not_routed_when_serve_media_is_off(self):
        self.assertIsNone(resolved_media_view(False))


class MediaRangeTests(SimpleTestCase):
    """`config.media.serve_media` answers Range requests, so audio can be seeked.

    Django's own `static.serve` sends the whole file with a 200 whatever the `Range`
    header says, and an <audio> element then cannot be moved: the player asks for a
    byte range, receives the whole file, and the scrub bar snaps back. Every assertion
    here is one of the answers a browser needs to seek.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.payload = bytes(range(256)) * 4  # 1024 distinguishable bytes
        (self.root / "clip.mp3").write_bytes(self.payload)

        override = override_settings(MEDIA_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)

        self.factory = RequestFactory()

    def body(self, response):
        """The bytes a response would send, whether it streams or not."""
        if isinstance(response, StreamingHttpResponse):
            return b"".join(response.streaming_content)
        return response.content

    def test_range_returns_206_with_exactly_the_requested_bytes(self):
        request = self.factory.get("/media/clip.mp3", HTTP_RANGE="bytes=10-19")
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 10-19/1024")
        self.assertEqual(response["Content-Length"], "10")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(self.body(response), self.payload[10:20])

    def test_suffix_range_returns_the_last_bytes(self):
        request = self.factory.get("/media/clip.mp3", HTTP_RANGE="bytes=-10")
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 1014-1023/1024")
        self.assertEqual(self.body(response), self.payload[1014:])

    def test_open_range_returns_to_the_end_of_the_file(self):
        request = self.factory.get("/media/clip.mp3", HTTP_RANGE="bytes=1000-")
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response["Content-Range"], "bytes 1000-1023/1024")
        self.assertEqual(self.body(response), self.payload[1000:])

    def test_range_for_the_whole_file_is_still_a_206(self):
        request = self.factory.get("/media/clip.mp3", HTTP_RANGE="bytes=0-")
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Length"], "1024")
        self.assertEqual(self.body(response), self.payload)

    def test_no_range_returns_the_whole_file_and_advertises_ranges(self):
        request = self.factory.get("/media/clip.mp3")
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], "1024")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(self.body(response), self.payload)

    def test_unsatisfiable_range_returns_416_with_the_real_size(self):
        request = self.factory.get("/media/clip.mp3", HTTP_RANGE="bytes=5000-6000")
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response.status_code, 416)
        self.assertEqual(response["Content-Range"], "bytes */1024")

    def test_a_cached_copy_is_answered_with_304(self):
        stamp = http_date(os.path.getmtime(self.root / "clip.mp3"))
        request = self.factory.get("/media/clip.mp3", HTTP_IF_MODIFIED_SINCE=stamp)
        response = serve_media(request, "clip.mp3")

        self.assertEqual(response.status_code, 304)

    def test_missing_file_is_not_found(self):
        request = self.factory.get("/media/nope.mp3")
        with self.assertRaises(Http404):
            serve_media(request, "nope.mp3")

    def test_a_path_that_climbs_out_of_media_root_is_not_found(self):
        request = self.factory.get("/media/x")
        with self.assertRaises(Http404):
            serve_media(request, "../outside.mp3")
