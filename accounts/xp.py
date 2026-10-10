"""Points, level and streak — the feedback layer the practice path shows.

The product deliberately had none of this. ``lessons/today.py`` says out loud that
streaks and points are *not* part of «امروز», and ``AGENTS.md`` banned gamification
outright. The owner has since asked for a Duolingo-shaped path, so this module is where
that one decision lives — in a single file, so it can be read, changed or deleted
without touching the practice content itself.

Three facts are stored on ``UserProfile`` (``xp``, ``streak_days``,
``last_practice_date``) and everything else is arithmetic done at read time:

* **Levels are flat.** Every level costs the same ``XP_PER_LEVEL``, so a learner can
  check the number in their head and no curve has to be maintained.
* **The streak counts *days practised*, not days logged in.** It only moves when an
  answer is actually recorded, and it is forgiving: skipping a day resets it to 1
  rather than blocking anything, because the path has no locked content.
* **XP is only ever added.** Nothing is spent on anything, so this cannot turn into a
  currency; it is a progress read-out and nothing more.

Nothing here reads the database except ``award``, which must write, and ``award``
never invents a profile: a visitor without a ``UserProfile`` simply gets nothing back.
"""

from datetime import timedelta

#: What one level costs. Flat on purpose — see the module docstring.
XP_PER_LEVEL = 100

#: What one correct answer is worth. Wrong answers still count as practice for the
#: streak but earn nothing, so the number tracks learning rather than attendance.
XP_PER_CORRECT_ANSWER = 10

#: What finishing a milestone test is worth, pass or fail — the point is that turning
#: up and being measured is rewarded, so a bad score is not punished twice.
XP_FOR_TEST = 50


def level_of(xp):
    """The level a given amount of XP buys. Level 1 starts at zero."""
    return xp // XP_PER_LEVEL + 1


def xp_into_level(xp):
    """How much XP the learner has inside their current level."""
    return xp % XP_PER_LEVEL


def xp_percent(xp):
    """How full the level bar is, as a whole percentage from 0 to 100."""
    return round(xp_into_level(xp) * 100 / XP_PER_LEVEL)


def summary(profile):
    """The four numbers the path's header shows, or ``None`` without a profile.

    Returns a dict rather than a tuple so the template can name what it reads, and so a
    later field can be added without renumbering anything.
    """
    if profile is None:
        return None

    return {
        "xp": profile.xp,
        "level": level_of(profile.xp),
        "into_level": xp_into_level(profile.xp),
        "per_level": XP_PER_LEVEL,
        "percent": xp_percent(profile.xp),
        "streak_days": profile.streak_days,
    }


def award(profile, amount, today):
    """Add ``amount`` XP to ``profile`` and move their streak, returning the new summary.

    The profile is passed in rather than a user, so this module never touches the ORM and
    the caller decides who is being credited — that is also what keeps it free of a
    circular import with ``accounts/models.py``, which reads the level maths back.

    ``today`` is a date in the project's own timezone (``timezone.localdate()``), passed
    in rather than read here so a view and a test can agree on which day they mean — the
    same rule ``lessons/today.py`` follows.

    ``None`` comes back when there is no profile, which is how an anonymous visitor is
    told apart from a learner whose write just failed.
    """
    if profile is None:
        return None

    if amount > 0:
        profile.xp = profile.xp + amount

    # The streak moves once per day. Practising twice today does not count twice, and a
    # gap resets to one rather than breaking anything.
    yesterday = today - timedelta(days=1)

    if profile.last_practice_date == today:
        pass
    elif profile.last_practice_date == yesterday:
        profile.streak_days = profile.streak_days + 1
    else:
        profile.streak_days = 1

    profile.last_practice_date = today
    profile.save(update_fields=["xp", "streak_days", "last_practice_date"])

    return summary(profile)
