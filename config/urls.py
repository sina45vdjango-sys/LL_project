"""
URL configuration for the Language_Learning project.

Each local app exposes its own urlpatterns in <app>/urls.py; add routes there
and they become reachable under the prefix declared below.
"""
import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.templatetags.static import static

from config.media import serve_media
from lessons.views import DashboardView, ReadinessView

urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('readiness/', ReadinessView.as_view(), name='readiness'),
    # Every browser asks for /favicon.ico on its own, whether or not a page declares an
    # icon, so this exact address was a 404 on every single page load. The picture lives
    # in one file (the SVG that templates/base.html already declares); this sends the
    # browser to that file instead of keeping a second copy that could drift from it.
    path(
        'favicon.ico',
        RedirectView.as_view(url=static(settings.FAVICON_PATH)),
        name='favicon',
    ),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('lessons/', include('lessons.urls')),
    path('vocabulary/', include('vocabulary.urls')),
    path('exercises/', include('exercises.urls')),
    path('exam/', include('exams.urls')),
    path('tests/', include('tests.urls')),
]

# Generated audio under MEDIA_ROOT is served by `config.media.serve_media`, which answers
# Range requests. Django's own `static()` helper and `django.views.static.serve` both send
# the whole file with a 200 and ignore `Range`, so an <audio> element could play a clip
# but never be seeked inside it — and this project's grammar and content clips run 13-40
# seconds. One route covers both local cases: DEBUG (development) and DJANGO_SERVE_MEDIA
# (a laptop on the LAN with DEBUG off, where `runserver --insecure` covers /static/ only).
if settings.DEBUG or settings.SERVE_MEDIA:
    # MEDIA_URL reads back as "/media/" (Django normalises it), but a URL pattern is
    # matched against the path with the leading slash already consumed, so the prefix has
    # to be stripped -- exactly what `static()` used to do with its own lstrip("/").
    # Getting this wrong is silent: every audio file answers 404 and the pages look fine.
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [
        re_path(
            r"^" + re.escape(media_prefix) + r"(?P<path>.*)$",
            serve_media,
        ),
    ]
