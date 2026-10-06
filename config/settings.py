"""
Django settings for Language_Learning project.

Started from 'django-admin startproject' and adapted since: the project now runs
Django 6.1.1 (see ``requirements.txt``), not the version the scaffold was generated
with.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    """Put the ``KEY=VALUE`` lines of a ``.env`` file into the environment.

    This is the whole of the project's configuration library: one line per value is all
    this project needs, and a dozen readable lines here are easier to follow than an
    extra package. A variable that is already exported in the shell always wins, so
    ``DJANGO_DEBUG=False python manage.py check`` works without editing any file.
    Blank lines, comments and lines without an ``=`` are skipped.
    """
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key in os.environ:
            continue
        os.environ[key] = value


# Real values live in .env, which is gitignored. .env.example lists the keys.
load_env_file(BASE_DIR / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# The value comes from DJANGO_SECRET_KEY in the environment (or .env).
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set. Copy .env.example to .env and fill it in."
    )

# SECURITY WARNING: don't run with debug turned on in production!
# The default is the safe one: a machine with no DJANGO_DEBUG set gets a production-shaped
# site rather than a debug page that leaks settings. .env sets it to True locally.
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

# Empty means "localhost only", which is right for development. Before deploying, set
# DJANGO_ALLOWED_HOSTS to a comma separated list: "example.com,www.example.com".
raw_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
if raw_allowed_hosts:
    ALLOWED_HOSTS = raw_allowed_hosts.split(",")
else:
    ALLOWED_HOSTS = []

# Origins allowed to POST to this site, as scheme://host, comma separated.
#
# Needed when the site is reached through something that terminates HTTPS for it without
# forwarding the original scheme -- a reverse proxy, or a tunnel such as Cloudflare's. The
# browser then sends `Origin: https://example.com` while Django, seeing plain HTTP on the
# inside, builds `http://example.com` to compare against — so the check fails and *every*
# POST is rejected with 403, while every GET keeps working. That asymmetry is what makes it
# hard to spot: the pages look fine and only the forms are dead.
#
# This list is the origin the browser sends, so it includes the scheme and no trailing slash.
raw_csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if raw_csrf_origins:
    CSRF_TRUSTED_ORIGINS = raw_csrf_origins.split(",")
else:
    CSRF_TRUSTED_ORIGINS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'accounts',
    'lessons',
    'vocabulary',
    'exercises',
    'exams',
    'tests',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Django has no default view for 405, so a POST-only address opened by hand used to
    # answer with an empty body. This is what renders templates/405.html instead; see the
    # module's docstring for why it only touches HTML requests. Last, so it sees the
    # response every other middleware has already finished with.
    'config.middleware.MethodNotAllowedMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            # The `direction` filter, available everywhere without a `{% load %}`:
            # every template shows Persian and German, so direction is a global concern.
            # `lesson_text` sits beside it for the same reason — it decides what of the
            # authored lesson text the Persian pages show (drop the English gloss, one
            # vocabulary item per line). Both are defined in config/templatetags/ and do
            # no database work.
            'builtins': [
                'config.templatetags.direction',
                'config.templatetags.lesson_text',
                'config.templatetags.jalali',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Shell-level data (brand + primary navigation).
                'config.context_processors.shell',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

# Every value comes from the environment, so no credential is written down here.
# The mirror copy (config/settings_mirror.py) reuses all of it and only swaps NAME.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "language_learning"),
        "USER": os.environ.get("DB_USER", "django_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

# The interface is Persian, so Django's own messages (the password validators, the
# admin) follow the same language. German content is marked lang="de" in templates.
LANGUAGE_CODE = 'fa'

# The learners are in Iran. With USE_TZ on, every timestamp is stored in UTC and shown
# in this zone, so existing rows keep their true value and only the display changes.
TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'

# Browsers ask for /favicon.ico by themselves, whether or not a page declares a favicon —
# so every visit logged a 404 for a file this project never had. The real icon is the SVG
# declared in templates/base.html; this name is pointed at that file rather than adding a
# second copy of the same picture that could fall out of date. A redirect, not a rewrite:
# the browser follows it once and then uses the SVG.
FAVICON_PATH = 'img/favicon.svg'

# Project-wide static assets, alongside each app's static/<app>/ folder.
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (uploaded/generated audio, images, ...)
# https://docs.djangoproject.com/en/6.1/topics/files/

MEDIA_URL = 'media/'

MEDIA_ROOT = BASE_DIR / 'media'

# Serve MEDIA_ROOT from Django itself. Off by default, because in a real deployment the
# web server in front of Django does this (and does it with caching and Range requests).
# It exists for the one case where there is no web server and DEBUG is off: running the
# project on a laptop for other people to try, with `runserver --insecure` covering
# /static/ and this covering /media/. See config/urls.py. Never turn it on in production.
SERVE_MEDIA = os.environ.get("DJANGO_SERVE_MEDIA", "False").lower() == "true"

# Who may put this site inside a frame. Django's own default is "DENY", which also refuses
# a page on this very site framing another one — and that is exactly what stops the layout
# being measured at a phone width: an iframe is the only way to get a 390px viewport, since
# a real browser window cannot be dragged narrower than about 500px. "SAMEORIGIN" keeps the
# protection that matters (no other site may frame the app) and unblocks the local harness.
# Set DJANGO_X_FRAME_OPTIONS=DENY to put the stricter one back.
X_FRAME_OPTIONS = os.environ.get("DJANGO_X_FRAME_OPTIONS", "SAMEORIGIN")

# Default primary key field type
# https://docs.djangoproject.com/en/6.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Authentication redirects (Django's built-in auth views read these).
# Learning content stays public: only /accounts/profile/ requires a login.

LOGIN_URL = 'accounts:login'

# The dashboard: a learner signs in to learn, not to edit settings. accounts/views.py
# sends them here for the same reason.
LOGIN_REDIRECT_URL = 'home'

LOGOUT_REDIRECT_URL = '/'


# The shortest username the sign-up form accepts. Django's own User model allows a
# one-character username, which is a name nobody can be recognised by; the sign-up form
# enforces this floor (accounts/forms.py). Only the form is guarded — existing accounts
# and the login form are left alone, so a short legacy username can still sign in.

USERNAME_MIN_LENGTH = 3


# Brand identity.
# Every place the product name is shown (sidebar, mobile bar, page titles, footer)
# reads from here, so renaming the product is a change to this dict and nothing else.
# The Persian name is one word and stays one word in the markup: splitting a wordmark
# into a bold part and a regular part puts a weight change inside the word, and in
# Persian script that reads as two separate words.

BRAND = {
    'name': 'ولینگو',
    'latin': 'Velingo',
    'tagline': 'آلمانی، با ولینگو',
    'footer_note': 'هر روز، یک گام به آلمانی نزدیک‌تر.',
}


# Logging.
# One console handler and one logger: Django's request logger, which reports the server
# errors (5xx) that would otherwise leave no trace in the terminal. Add a logger here
# when something needs one; a file-based setup would be noise while the project only
# runs locally.
#
# The level is ERROR on purpose. At WARNING the same logger also reports every 4xx —
# and a 404 is a normal answer, not a fault — so the test suite would fill the terminal
# with "Not Found" lines and tracebacks for the errors it deliberately provokes and
# asserts on. Raise it to "WARNING" or "INFO" if you want that traffic while debugging.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
