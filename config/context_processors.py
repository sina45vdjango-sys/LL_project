"""Shell-level template context: the brand, the primary navigation and the theme.

Both the desktop sidebar and the mobile bottom navigation render from
``NAV_ITEMS`` here, so adding a destination (or renaming one) is a single edit
and both navigation surfaces stay in sync. Items whose URL does not resolve yet
are skipped rather than rendered as a broken link.

An item marks itself active either by ``view_name`` (exact match, needed for the
dashboard which is routed at the project level) or by ``app_names``.

The theme is here because it has to reach the ``<html>`` tag of every page: the
script in base.html reads it before the first paint, and that is what stops a
learner who chose dark from seeing a white flash on every navigation.

The due-word count is here for the same reason the navigation is: it has to be visible
on *every* page. ``vocabulary/schedule.py`` decides when a word comes back, but until
now nothing said so unless the learner opened «امروز» — the one nudge the product was
missing. It is one cheap count for a signed-in learner and nothing for a visitor.
"""

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from accounts.models import UserProfile


NAV_ITEMS = [
    {
        "key": "dashboard",
        "label": "داشبورد",
        "url_name": "home",
        "view_name": "home",
        "icon": "home",
    },
    {
        "key": "today",
        "label": "امروز",
        "url_name": "lessons:practice-path",
        "view_name": "lessons:practice-path",
        # The masthead destination for a learner: one node per skill, in place of the
        # lesson's exercise wall. Matched by exact view name rather than by app, because
        # the lesson pages are the same app and must not light both links at once.
        "icon": "today",
    },
    {
        "key": "lessons",
        "label": "درس‌ها",
        "url_name": "lessons:lesson-list",
        "app_names": ("lessons",),
        # The lessons link stays lit across its own app except on the Today page, which
        # has its own entry above; without this, arriving at /lessons/today/ would
        # highlight two navigation items at once.
        "exclude_view_names": ("lessons:practice-path",),
        "icon": "steps",
    },
    {
        "key": "vocabulary",
        "label": "واژه‌ها",
        "url_name": "vocabulary:word-list",
        "app_names": ("vocabulary",),
        "icon": "cards",
    },
    {
        "key": "exercises",
        "label": "تمرین‌ها",
        # The daily session is the exercises destination: it is the page a learner
        # actually practises on, while the old exercise list was a wall of every
        # exercise in the course. The app match still lights the link on any exercises
        # page, including that list, which stays reachable from the session.
        "url_name": "exercises:session",
        "app_names": ("exercises",),
        "icon": "practice",
    },
    {
        "key": "exam",
        "label": "آزمون",
        "url_name": "exams:exam-index",
        "app_names": ("exams",),
        "icon": "exam",
    },
]



def resolve(url_name):
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def is_active(item, request):
    match = request.resolver_match
    if match is None:
        return False

    # A page that belongs to an app but has its own navigation entry claims the highlight
    # alone; the app-wide match below is what would otherwise light the parent as well.
    if "exclude_view_names" in item:
        if match.view_name in item["exclude_view_names"]:
            return False

    if item.get("view_name") == match.view_name:
        return True
    if "app_names" in item:
        return match.app_name in item["app_names"]


def shell(request):
    nav_items = []

    for item in NAV_ITEMS:
        url = resolve(item["url_name"])

        if url is None:
            continue

        nav_items.append(
            {
                "key": item["key"],
                "label": item["label"],
                "url": url,
                "icon": item["icon"],
                "active": is_active(item, request),
            }
        )

    # Fall back to the lesson list, then to "/", so the shell always has a home link.
    home_url = resolve("home")
    if home_url is None:
        home_url = resolve("lessons:lesson-list")
    if home_url is None:
        home_url = "/"

    # "system" is the answer for a signed-out visitor and for a learner whose profile
    # row does not exist yet: the script in base.html reads that as "follow the
    # operating system". Don't get_or_create the profile here — loading any page would
    # start writing rows for people who only came to read.
    theme_mode = UserProfile.Theme.SYSTEM
    due_count = 0

    if request.user.is_authenticated:
        try:
            theme_mode = request.user.profile.theme
        except UserProfile.DoesNotExist:
            theme_mode = UserProfile.Theme.SYSTEM

        # Imported here rather than at the top: a context processor is imported while the
        # app registry is still being populated, and reaching for a model module then can
        # be too early (the same reason Django documents this import placement).
        from django.utils import timezone
        from vocabulary.models import WordProgress

        # One count, not the whole queue: the nudge only needs a number, and the page the
        # learner opens from it builds the real queue. A word with no due time was never
        # scheduled, so it cannot be due (vocabulary/schedule.py writes every due time).
        due_count = WordProgress.objects.filter(
            user=request.user,
            due_at__lte=timezone.now(),
            word__is_published=True,
        ).count()

    for item in nav_items:
        if item["key"] == "today":
            item["badge"] = due_count

    return {
        "brand": settings.BRAND,
        "nav_items": nav_items,
        "home_url": home_url,
        "theme_mode": theme_mode,
        "due_count": due_count,
    }