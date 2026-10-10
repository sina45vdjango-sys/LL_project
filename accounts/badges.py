"""Badges — the few things a learner has provably done.

Nothing is stored for a badge and no row is written when one is earned. Every badge is
decided, at read time, from rows this product already keeps: the answers the learner
submitted, the lessons they finished, the mock exams they completed, and the streak
``accounts/xp.py`` maintains. So a badge cannot be bought, cannot be lost, and cannot
disagree with the number the rest of the product shows for the same fact.

They are deliberately few and none of them happens by accident. The page shows only the
ones actually earned, because a badge that is merely possible is a promise nobody made —
and a wall of grey locks is exactly the "not-X-but-Y" pressure this product avoids.
"""

from exams.models import ExamRun
from exercises.models import ExerciseAttempt
from lessons.models import Lesson, LessonProgress


def _badge(key, label, hint):
    """One earned badge. A helper because a badge has the same three fields every time."""
    return {"key": key, "label": label, "hint": hint}


def badges_for(user, profile):
    """The badges this learner has earned, in the order the levels are meant to be read.

    ``profile`` may be ``None`` — a signed-in learner without a profile has no streak —
    and only the streak badges read it. Everything else is counted from the learner's own
    rows, so a learner with no profile still gets the ones they really earned.
    """
    answers = ExerciseAttempt.objects.filter(user=user).count()
    lessons_done = LessonProgress.objects.filter(
        user=user, status=LessonProgress.Status.COMPLETED
    ).count()
    lessons_total = Lesson.objects.filter(is_published=True).count()
    exams_done = ExamRun.objects.filter(user=user, finished_at__isnull=False).count()

    streak = 0
    if profile is not None:
        streak = profile.streak_days

    earned = []

    if answers >= 1:
        earned.append(_badge("first-answer", "اولین قدم", "اولین پاسخ را ثبت کردی."))
    if answers >= 100:
        earned.append(_badge("answers-100", "۱۰۰ پاسخ", "صد پرسش را پاسخ داده‌ای."))
    if answers >= 500:
        earned.append(_badge("answers-500", "۵۰۰ پاسخ", "پانصد پرسش را پاسخ داده‌ای."))
    if answers >= 1000:
        earned.append(_badge("answers-1000", "۱۰۰۰ پاسخ", "هزار پرسش را پاسخ داده‌ای."))

    if lessons_done >= 1:
        earned.append(_badge("first-lesson", "اولین درس", "اولین درس را تمام کردی."))
    if lessons_total > 0 and lessons_done >= lessons_total:
        earned.append(_badge("whole-course", "دورهٔ کامل", "همهٔ درس‌های منتشرشده را تمام کردی."))

    if streak >= 3:
        earned.append(_badge("streak-3", "سه روز پشت‌سرهم", "سه روز پیاپی تمرین کرده‌ای."))
    if streak >= 7:
        earned.append(_badge("streak-7", "یک هفته پشت‌سرهم", "هفت روز پیاپی تمرین کرده‌ای."))
    if streak >= 30:
        earned.append(_badge("streak-30", "یک ماه پشت‌سرهم", "سی روز پیاپی تمرین کرده‌ای."))

    if exams_done >= 1:
        earned.append(_badge("first-exam", "اولین آزمون", "یک آزمون آزمایشی را کامل نشستی."))

    return earned
