"""Shell-level template context: the brand and the primary navigation.

Both the desktop sidebar and the mobile bottom navigation render from
``NAV_ITEMS`` here, so adding a destination (or renaming one) is a single edit
and both navigation surfaces stay in sync. Items whose URL does not resolve yet
are skipped rather than rendered as a broken link.

An item marks itself active either by ``view_name`` (exact match, needed for the
dashboard which is routed at the project level) or by ``app_names``.
"""

from django.conf import settings
from django.urls import NoReverseMatch, reverse


NAV_ITEMS = [
    {
        "key": "dashboard",
        "label": "داشبورد",
        "url_name": "home",
        "view_name": "home",
        "icon": "home",
    },
    {
        "key": "lessons",
        "label": "درس‌ها",
        "url_name": "lessons:lesson-list",
        "app_names": ("lessons",),
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
        "url_name": "exercises:exercise-list",
        "app_names": ("exercises",),
        "icon": "practice",
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

    return {
        "brand": settings.BRAND,
        "nav_items": nav_items,
        "home_url": home_url,
    }