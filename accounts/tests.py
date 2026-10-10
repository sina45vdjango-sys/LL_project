"""Tests for the authentication surface.

Login/logout are Django's built-in views, so these tests focus on the wiring we
own: the URLs, the templates, the signup flow, profile access rules and the fact
that learning content stays public.

``GoalTests`` covers the learner's stated goal, which lives on ``UserProfile`` and is
what the readiness page reads to say how much time is left.

``ThemeTests`` covers the light/dark choice, which also lives on ``UserProfile`` but is
read on every page — it has to reach the ``<html>`` tag before the first paint, so it
comes in through the shell context processor rather than through a view context.
"""

from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone

from exercises.models import Exercise, ExerciseAttempt, Question
from lessons.models import Course, LanguageLevel, Lesson, LessonProgress

from . import xp
from .badges import badges_for
from .jalali import (
    days_in_month,
    format_date,
    from_gregorian,
    is_leap_year,
    persian_number,
    to_gregorian,
    year_choices,
)
from .models import UserProfile

PASSWORD = "SehrSicher123!"


class SignUpTests(TestCase):
    url = reverse("accounts:signup")

    def test_signup_page_renders_the_shell_and_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/signup.html")
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "field__input")

    def test_signup_creates_user_and_profile_then_logs_in(self):
        response = self.client.post(self.url, {
            "username": "sina",
            "email": "sina@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        # A brand-new account enters the first-run flow instead of landing on its own account
        # page. The goal is what «امروز», the countdown and «آمادگی من» read, and it is the one
        # thing a new learner cannot discover by browsing, so it is asked for first — with
        # `onboarding=1` marking the visit as part of that flow (see SignUpView).
        self.assertRedirects(response, reverse("accounts:goal") + "?onboarding=1")
        user = User.objects.get(username="sina")
        self.assertEqual(user.email, "sina@example.com")
        # The post_save receiver should have paired the account with a profile.
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(self.url, {
            "username": "sina",
            "password1": PASSWORD,
            "password2": PASSWORD + "x",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دو گذرواژه یکسان نیستند.")
        self.assertFalse(User.objects.filter(username="sina").exists())

    def test_signup_rejects_a_too_short_username(self):
        response = self.client.post(self.url, {
            "username": "ab",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نام کاربری باید حداقل")
        self.assertFalse(User.objects.filter(username="ab").exists())

    def test_signed_in_user_is_sent_away_from_signup(self):
        user = User.objects.create_user(username="sina", password=PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), reverse("home"))

    def test_the_username_help_text_states_the_maximum(self):
        # The help text is where a learner reads the rule before typing, so the length cap
        # has to be part of it rather than a surprise after submitting.
        response = self.client.get(self.url)
        self.assertContains(response, "حروف انگلیسی، رقم و نویسه‌های @ . + - _")
        self.assertContains(response, f"حداکثر {settings.USERNAME_MAX_LENGTH} نویسه")

    def test_signup_rejects_a_username_the_help_text_does_not_allow(self):
        # «حروف انگلیسی، رقم و نویسه‌های @ . + - _» is a promise the field keeps. Persian
        # digits are outside it, and the value used to be accepted and created.
        for username in ("کاربر۱۲۳", "sina#test", "sina test"):
            with self.subTest(username=username):
                response = self.client.post(self.url, {
                    "username": username,
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                })
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "نام کاربری فقط می‌تواند شامل حروف انگلیسی، رقم و نویسه‌های @ . + - _ باشد.",
                )
                self.assertFalse(User.objects.filter(username=username).exists())

    def test_signup_rejects_markup_in_the_username(self):
        # Not a security fix — the value is escaped wherever it is shown either way — but a
        # username made of markup is not one of the characters the form allows.
        response = self.client.post(self.url, {
            "username": "<script>alert(1)</script>",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نام کاربری فقط می‌تواند شامل")
        self.assertFalse(User.objects.filter(username__startswith="<script>").exists())

    def test_a_username_at_the_maximum_is_still_allowed(self):
        allowed = "u" * settings.USERNAME_MAX_LENGTH
        response = self.client.post(self.url, {
            "username": allowed,
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertRedirects(response, reverse("accounts:goal") + "?onboarding=1")
        self.assertTrue(User.objects.filter(username=allowed).exists())

    def test_signup_rejects_a_username_longer_than_the_maximum(self):
        response = self.client.post(self.url, {
            "username": "u" * (settings.USERNAME_MAX_LENGTH + 1),
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, f"نام کاربری نباید بیشتر از {settings.USERNAME_MAX_LENGTH} نویسه باشد."
        )
        self.assertEqual(User.objects.count(), 0)

    def test_a_short_password_is_reported_in_persian(self):
        # Django's own minimum-length sentence is not translated in its Persian catalog, so
        # the product states it (accounts/validators.py). Raw English in this form is the bug
        # this test pins down.
        response = self.client.post(self.url, {
            "username": "sina",
            "password1": "abc",
            "password2": "abc",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "گذرواژه باید حداقل ۸ نویسه باشد.")
        self.assertNotContains(response, "This password is too short")
        self.assertFalse(User.objects.filter(username="sina").exists())

    def test_a_password_that_fails_its_own_rule_is_not_also_called_mismatched(self):
        # The two boxes held the same text. Only the real problem is reported: the missing
        # password1 used to be compared against password2 and produce a second, false error.
        for password in ("abc", "12345678", "password"):
            with self.subTest(password=password):
                response = self.client.post(self.url, {
                    "username": "sina",
                    "password1": password,
                    "password2": password,
                })
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "دو گذرواژه یکسان نیستند.")
                self.assertTrue(response.context["form"].errors["password1"])

    def test_other_password_rules_are_still_reported(self):
        for password in ("12345678", "password"):
            with self.subTest(password=password):
                response = self.client.post(self.url, {
                    "username": "sina",
                    "password1": password,
                    "password2": password,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors["password1"])

    def test_the_credential_fields_ask_the_browser_to_fill_them(self):
        # Without these hints no password manager offers to fill or save the form.
        response = self.client.get(self.url)
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="email"')
        self.assertContains(response, 'autocomplete="new-password"')
        self.assertEqual(response.content.decode().count('autocomplete="new-password"'), 2)


class LoginTests(TestCase):
    url = reverse("accounts:login")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="sina", password=PASSWORD)

    def test_login_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, "نام کاربری")

    def test_valid_credentials_log_the_user_in(self):
        # The dashboard, not the account page: a learner signs in to learn, and the
        # first post-login screen used to be a page of settings.
        response = self.client.post(self.url, {"username": "sina", "password": PASSWORD})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_credentials_show_a_persian_error(self):
        response = self.client.post(self.url, {"username": "sina", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نام کاربری یا گذرواژه درست نیست.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_the_login_fields_ask_the_browser_to_fill_them(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')

    def test_login_page_carries_next_into_the_form(self):
        # The hidden field is what keeps `next` alive across the POST: the form posts
        # to /accounts/login/ with no query string on it.
        response = self.client.get(f"{self.url}?next=/lessons/")
        self.assertContains(response, '<input type="hidden" name="next" value="/lessons/">')

    def test_login_honours_a_next_parameter_in_the_query_string(self):
        response = self.client.post(
            f"{self.url}?next=/lessons/", {"username": "sina", "password": PASSWORD}
        )
        self.assertRedirects(response, "/lessons/")

    def test_login_honours_a_next_parameter_carried_by_the_form(self):
        response = self.client.post(
            self.url, {"username": "sina", "password": PASSWORD, "next": "/lessons/"}
        )
        self.assertRedirects(response, "/lessons/")

    def test_login_ignores_a_next_parameter_that_leaves_this_site(self):
        # Without this guard the login page would be an open redirect.
        response = self.client.post(
            f"{self.url}?next=https://evil.example/",
            {"username": "sina", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))

    def test_signed_in_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("home"))


class LogoutTests(TestCase):
    url = reverse("accounts:logout")

    def setUp(self):
        self.user = User.objects.create_user(username="sina", password=PASSWORD)
        self.client.force_login(self.user)

    def test_logout_still_requires_post(self):
        # Django 5+ removed GET logout; a link must not be able to sign you out. The GET
        # now answers with a redirect to the home page rather than an empty 405 body, but
        # it still does not sign anybody out — which is the part that matters.
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_post_logout_signs_the_user_out(self):
        response = self.client.post(self.url)
        # LogoutView sends the visitor to the login page, which is where the
        # "signed out" message is shown.
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class ProfileTests(TestCase):
    url = reverse("accounts:profile")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="sina", password=PASSWORD)

    def test_profile_requires_login(self):
        response = self.client.get(self.url)
        # ProfileView redirects to the login page without a `?next=` parameter.
        self.assertRedirects(response, reverse("accounts:login"))

    def test_profile_renders_account_details(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, "sina")
        self.assertContains(response, "زبان مادری")

    def test_profile_is_created_on_demand_for_older_accounts(self):
        UserProfile.objects.filter(user=self.user).delete()
        self.client.force_login(self.user)
        self.client.get(self.url)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())


class GoalTests(TestCase):
    """Where the learner says what they are working towards.

    All four fields are optional, and submitting them all empty is a legitimate way to
    clear a goal — so every test here is about either what gets stored, or what is
    allowed to be stored.
    """

    url = reverse("accounts:goal")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="sina", password=PASSWORD)
        cls.other = User.objects.create_user(username="andere", password=PASSWORD)
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.next_level = LanguageLevel.objects.create(level="A2", title="متوسط", order=2)

    def setUp(self):
        self.client.force_login(self.user)

    def profile(self, user=None):
        if user is None:
            user = self.user
        return UserProfile.objects.get(user=user)

    def test_the_page_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("accounts:login"))

    def test_an_anonymous_post_saves_nothing(self):
        self.client.logout()
        response = self.client.post(self.url, {"target_level": self.next_level.pk})
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertIsNone(self.profile().target_level)

    def test_the_page_renders_the_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/goal.html")
        self.assertContains(response, "سطح هدف")
        self.assertContains(response, "چرا آلمانی یاد می‌گیری؟")
        self.assertContains(response, "سال")
        self.assertContains(response, "ماه")
        self.assertContains(response, "روز")
        self.assertContains(response, "ذخیرهٔ هدف")

    def test_the_reasons_are_offered_in_persian(self):
        response = self.client.get(self.url)
        self.assertContains(response, "آوسبیلدونگ")
        self.assertContains(response, "مهاجرت")
        self.assertContains(response, "آلمانی عمومی")

    def test_the_onboarding_flag_frames_the_page_as_step_one(self):
        # The first run gets a framing that explains what the goal is for; a later visit does
        # not, because by then the learner has seen the pages it feeds.
        response = self.client.get(self.url + "?onboarding=1")
        self.assertContains(response, "قدم ۱ از ۲")
        self.assertContains(response, "ذخیره و دیدن برنامه")
        self.assertContains(response, 'name="onboarding" value="1"')

    def test_a_plain_visit_is_not_framed_as_onboarding(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "قدم ۱ از ۲")
        self.assertContains(response, "ذخیرهٔ هدف")

    def test_saving_during_onboarding_continues_to_the_learning_plan(self):
        # Step one hands the learner on to step two carrying the flag, instead of stopping at
        # a page with no next action.
        response = self.client.post(self.url, {
            "current_level": self.level.pk,
            "target_level": self.level.pk,
            "onboarding": "1",
        })
        self.assertRedirects(response, reverse("readiness") + "?onboarding=1")
        self.assertEqual(self.profile().target_level, self.level)

    def test_saving_a_goal_stores_every_part(self):
        # The date is chosen in the Jalali calendar (۱ دی ۱۴۰۵) and stored as the Gregorian
        # day the rest of the product counts with. The two must be the same day.
        response = self.client.post(self.url, {
            "current_level": self.level.pk,
            "target_level": self.next_level.pk,
            "reason": UserProfile.Reason.AUSBILDUNG,
            "target_year": "1405",
            "target_month": "10",
            "target_day": "1",
        })
        self.assertRedirects(response, reverse("readiness"))

        stored = self.profile()
        self.assertEqual(stored.current_level, self.level)
        self.assertEqual(stored.target_level, self.next_level)
        self.assertEqual(stored.reason, UserProfile.Reason.AUSBILDUNG)
        self.assertEqual(stored.target_date, date(2026, 12, 22))
        self.assertEqual(stored.reason_label, "آوسبیلدونگ")

    def test_saving_everything_empty_clears_the_goal(self):
        profile = self.profile()
        profile.target_level = self.next_level
        profile.reason = UserProfile.Reason.WORK
        profile.target_date = date(2026, 12, 22)
        profile.save()

        self.client.post(self.url, {
            "current_level": "",
            "target_level": "",
            "reason": "",
            "target_year": "",
            "target_month": "",
            "target_day": "",
        })

        stored = self.profile()
        self.assertIsNone(stored.target_level)
        self.assertEqual(stored.reason, "")
        self.assertIsNone(stored.target_date)

    def test_a_target_below_the_current_level_is_refused(self):
        response = self.client.post(self.url, {
            "current_level": self.next_level.pk,
            "target_level": self.level.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سطح هدف نمی‌تواند پایین‌تر از سطح فعلی باشد.")
        stored = self.profile()
        self.assertIsNone(stored.target_level)
        self.assertIsNone(stored.current_level)

    def test_a_target_equal_to_the_current_level_is_allowed(self):
        response = self.client.post(self.url, {
            "current_level": self.level.pk,
            "target_level": self.level.pk,
        })
        self.assertRedirects(response, reverse("readiness"))
        self.assertEqual(self.profile().target_level, self.level)

    def test_a_partial_date_is_refused(self):
        # Year alone is not a date. Nothing is stored and the learner is told what is missing.
        response = self.client.post(self.url, {"target_year": "1405"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تاریخ هدف را کامل انتخاب کن")
        self.assertIsNone(self.profile().target_date)

    def test_a_day_that_does_not_exist_in_the_month_is_refused(self):
        # Month 9 always has 30 days, so 31 is never a day in it. The menus offer 1..31 and
        # the server refuses the combinations that do not exist. The year is asked for rather
        # than written down, so this test does not stop being true next year.
        current_year = year_choices(timezone.localdate())[0]
        response = self.client.post(self.url, {
            "target_year": str(current_year),
            "target_month": "9",
            "target_day": "31",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این روز در این ماه وجود ندارد")
        self.assertIsNone(self.profile().target_date)

    def test_a_past_year_is_not_offered_but_a_stored_one_stays_selectable(self):
        # A target date can go past while it is stored (the readiness page has a whole state
        # for that), so its year has to remain an option — otherwise reopening the form would
        # show an empty menu and saving would quietly lose the date.
        current_year = year_choices(timezone.localdate())[0]

        profile = self.profile()
        profile.target_date = to_gregorian(current_year - 3, 1, 1)
        profile.save()

        response = self.client.get(self.url)
        self.assertEqual(response.context["form"].initial["target_year"], str(current_year - 3))

        # The year it stored is offered even though the menu starts at this year.
        self.assertContains(response, str(current_year - 3))

        # And the past date survives a save that does not touch it.
        self.client.post(self.url, {
            "current_level": self.level.pk,
            "target_year": str(current_year - 3),
            "target_month": "1",
            "target_day": "1",
        })
        self.assertEqual(self.profile().target_date, to_gregorian(current_year - 3, 1, 1))

    def test_the_page_shows_the_goal_already_set(self):
        profile = self.profile()
        profile.target_level = self.next_level
        profile.reason = UserProfile.Reason.UNIVERSITY
        profile.save()

        response = self.client.get(self.url)
        # The read-only summary is rendered only when there is something to summarise —
        # the form's own option list always mentions every level and reason.
        self.assertContains(response, 'aria-label="هدف فعلی"')
        self.assertEqual(response.context["form"].initial["target_level"], self.next_level)
        self.assertEqual(response.context["form"].initial["reason"], UserProfile.Reason.UNIVERSITY)

    def test_the_date_menus_offer_a_blank_and_no_date_is_assumed(self):
        # The form's own hint says every field is optional, and the browser can only leave a
        # <select> empty if there is an empty <option> to select. Without it, an untouched
        # form submitted the first year instead — a past date nobody chose.
        response = self.client.get(self.url)
        form = response.context["form"]

        for field_name in ("target_year", "target_month", "target_day"):
            with self.subTest(field=field_name):
                self.assertEqual(form.fields[field_name].choices[0], ("", "انتخاب نشده"))

        # What a browser sends for that untouched form stores no date at all.
        self.client.post(self.url, {
            "current_level": "",
            "target_level": "",
            "reason": "",
            "target_year": "",
            "target_month": "",
            "target_day": "",
        })
        self.assertIsNone(self.profile().target_date)

    def test_a_learner_with_no_goal_gets_no_summary(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'aria-label="هدف فعلی"')
        self.assertIsNone(response.context["form"].initial["target_level"])

    def test_another_learners_goal_is_neither_shown_nor_overwritten(self):
        their_profile = UserProfile.objects.get(user=self.other)
        their_profile.target_level = self.next_level
        their_profile.reason = UserProfile.Reason.MIGRATION
        their_profile.save()

        response = self.client.get(self.url)
        self.assertEqual(response.context["profile"].user, self.user)
        self.assertIsNone(response.context["form"].initial["target_level"])
        self.assertEqual(response.context["form"].initial["reason"], "")

        self.client.post(self.url, {"reason": UserProfile.Reason.WORK})
        self.assertEqual(self.profile().reason, UserProfile.Reason.WORK)
        self.assertEqual(self.profile(self.other).reason, UserProfile.Reason.MIGRATION)

    def test_the_profile_page_links_to_the_goal_and_to_readiness(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, reverse("accounts:goal"))
        self.assertContains(response, reverse("readiness"))

    def test_a_blank_reason_has_no_label(self):
        self.assertEqual(self.profile().reason_label, "")


class AnonymousAccessTests(TestCase):
    """Anonymous-first: the learning content must stay public."""

    def test_public_pages_do_not_require_login(self):
        for name in ("lessons:lesson-list", "vocabulary:word-list", "exercises:exercise-list"):
            with self.subTest(url=name):
                # `exercises:exercise-list` now redirects to the practice path, so follow
                # it: the point here is that no login wall appears, not the status code.
                response = self.client.get(reverse(name), follow=True)
                self.assertEqual(response.status_code, 200)

    def test_home_is_the_dashboard_and_is_reachable_without_login(self):
        # Phase 3 turned the placeholder redirect into the real product home.
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard.html")

    def test_anonymous_navigation_offers_login_and_signup(self):
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertContains(response, reverse("accounts:login"))
        self.assertContains(response, reverse("accounts:signup"))

    def test_authenticated_navigation_offers_profile_and_logout(self):
        user = User.objects.create_user(username="sina", password=PASSWORD)
        self.client.force_login(user)
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertContains(response, reverse("accounts:profile"))
        self.assertContains(response, reverse("accounts:logout"))


class ThemeTests(TestCase):
    """The colour scheme: chosen on the profile page, read on every page."""

    def setUp(self):
        self.user = User.objects.create_user(username="sina", password=PASSWORD)
        self.other = User.objects.create_user(username="ali", password=PASSWORD)
        self.url = reverse("accounts:theme")

    def profile(self, user=None):
        if user is None:
            user = self.user
        return UserProfile.objects.get(user=user)

    def test_a_new_profile_follows_the_system(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(self.profile().theme, UserProfile.Theme.SYSTEM)
        self.assertEqual(response.context["profile"].theme_label, "سیستم")

    def test_the_saved_choice_reaches_the_html_tag(self):
        profile = self.profile()
        profile.theme = UserProfile.Theme.DARK
        profile.save()

        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertContains(response, 'data-theme-mode="dark"')

    def test_a_visitor_follows_the_system(self):
        # No profile to read, so the page must not claim a theme of its own.
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertContains(response, 'data-theme-mode="system"')

    def test_choosing_a_theme_saves_it(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"theme": UserProfile.Theme.LIGHT})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(self.profile().theme, UserProfile.Theme.LIGHT)

    def test_the_three_choices_are_offered_with_the_current_one_selected(self):
        profile = self.profile()
        profile.theme = UserProfile.Theme.DARK
        profile.save()

        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, 'value="dark" checked')
        self.assertContains(response, "روشن")
        self.assertContains(response, "سیستم")

    def test_an_unknown_theme_is_refused(self):
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.post(self.url, {"theme": "neon"}),
            reverse("accounts:profile"),
        )
        self.assertEqual(self.profile().theme, UserProfile.Theme.SYSTEM)

    def test_one_learners_choice_does_not_touch_another(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"theme": UserProfile.Theme.DARK})
        self.assertEqual(self.profile(self.other).theme, UserProfile.Theme.SYSTEM)

    def test_choosing_a_theme_requires_login(self):
        self.assertRedirects(
            self.client.post(self.url, {"theme": UserProfile.Theme.DARK}),
            reverse("accounts:login"),
        )


class XpTests(TestCase):
    """Points, level and the streak (``accounts/xp.py``).

    The arithmetic is deliberately flat and the streak deliberately forgiving, so these
    tests pin down exactly those two decisions: a level always costs the same, and a
    missed day resets the count instead of breaking anything.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="practiser", password=PASSWORD)
        # A profile row is created with the user (accounts/signals.py), so it is read
        # here rather than made again — the OneToOne would refuse a second one.
        self.profile = self.user.profile
        self.today = date(2026, 10, 4)

    def test_a_level_always_costs_the_same(self):
        self.assertEqual(xp.level_of(0), 1)
        self.assertEqual(xp.level_of(99), 1)
        self.assertEqual(xp.level_of(100), 2)
        self.assertEqual(xp.level_of(350), 4)

    def test_the_bar_measures_the_current_level_only(self):
        self.assertEqual(xp.xp_percent(0), 0)
        self.assertEqual(xp.xp_percent(50), 50)
        # 150 is level 2 with 50 in, so the bar is half full rather than 150% full.
        self.assertEqual(xp.xp_percent(150), 50)

    def test_a_visitor_without_a_profile_has_no_summary(self):
        self.assertIsNone(xp.summary(None))
        self.assertIsNone(xp.award(None, 10, self.today))

    def test_a_correct_answer_adds_points_and_starts_a_streak(self):
        summary = xp.award(self.profile, xp.XP_PER_CORRECT_ANSWER, self.today)
        self.assertEqual(summary["xp"], 10)
        self.assertEqual(summary["streak_days"], 1)

    def test_practising_twice_in_one_day_counts_the_day_once(self):
        xp.award(self.profile, 10, self.today)
        summary = xp.award(self.profile, 10, self.today)
        self.assertEqual(summary["xp"], 20)
        self.assertEqual(summary["streak_days"], 1)

    def test_a_second_day_in_a_row_lengthens_the_streak(self):
        xp.award(self.profile, 10, self.today)
        summary = xp.award(self.profile, 10, self.today + timedelta(days=1))
        self.assertEqual(summary["streak_days"], 2)

    def test_a_missed_day_resets_the_streak_rather_than_blocking_anything(self):
        xp.award(self.profile, 10, self.today)
        xp.award(self.profile, 10, self.today + timedelta(days=1))
        summary = xp.award(self.profile, 10, self.today + timedelta(days=5))
        self.assertEqual(summary["streak_days"], 1)

    def test_a_wrong_answer_earns_nothing_but_still_counts_as_showing_up(self):
        """The streak is about turning up; points are about getting it right."""
        summary = xp.award(self.profile, 0, self.today)
        self.assertEqual(summary["xp"], 0)
        self.assertEqual(summary["streak_days"], 1)

    def test_the_level_property_on_the_profile_agrees_with_the_module(self):
        self.profile.xp = 250
        self.assertEqual(self.profile.level, xp.level_of(250))
        self.assertEqual(self.profile.xp_percent, xp.xp_percent(250))


class BadgeTests(TestCase):
    """Badges are earned from rows that already exist — nothing is stored for them.

    ``accounts/badges.py`` reads the learner's own answers, lesson completions and streak,
    so these tests pin the two properties that make them honest: a learner with nothing has
    none, and a badge appears only when the underlying row really says so.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        cls.exercise = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.question = Question.objects.create(
            exercise=cls.exercise, prompt="پرسش", order=1
        )
        cls.user = User.objects.create_user(
            username="badge-learner", password="a-strong-password"
        )

    def keys(self, profile=None):
        return [badge["key"] for badge in badges_for(self.user, profile)]

    def answer(self, count):
        for _ in range(count):
            ExerciseAttempt.objects.create(
                user=self.user,
                exercise=self.exercise,
                question=self.question,
                is_correct=True,
            )

    def test_a_learner_with_nothing_has_no_badges(self):
        self.assertEqual(self.keys(), [])

    def test_the_first_answer_earns_the_first_badge(self):
        self.answer(1)
        self.assertEqual(self.keys(), ["first-answer"])

    def test_the_answer_milestones_stack_and_are_ordered(self):
        self.answer(100)
        self.assertEqual(self.keys(), ["first-answer", "answers-100"])

    def test_the_streak_badges_read_the_profile(self):
        # The profile row already exists (accounts/signals.py makes it with the user),
        # so it is read here rather than made again — the OneToOne would refuse a second.
        profile = self.user.profile
        profile.streak_days = 7
        profile.save()
        self.answer(1)

        self.assertEqual(self.keys(profile), ["first-answer", "streak-3", "streak-7"])

    def test_a_missing_profile_only_costs_the_streak_badges(self):
        self.answer(1)

        self.assertEqual(self.keys(None), ["first-answer"])

    def test_finishing_the_only_published_lesson_earns_both_lesson_badges(self):
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )

        keys = self.keys()
        self.assertIn("first-lesson", keys)
        self.assertIn("whole-course", keys)


class JalaliCalendarTests(SimpleTestCase):
    """``accounts.jalali``: the Persian calendar, and the one date the product shows.

    The conversion is checked against dates that are known independently of this code — the
    Jalali new year, which is 21 March in the years these tests use — and then against
    itself, by round-tripping every day of a long stretch. A wrong leap year shows up in
    either check, which is what makes the menus trustworthy.
    """

    def test_the_new_year_is_the_day_the_calendar_says(self):
        self.assertEqual(to_gregorian(1400, 1, 1), date(2021, 3, 21))
        self.assertEqual(to_gregorian(1405, 1, 1), date(2026, 3, 21))

    def test_every_day_converts_back_to_itself(self):
        # Every day from 1990 to 2050: the two directions must agree everywhere, not only on
        # the dates someone thought to write down.
        day = date(1990, 1, 1)

        while day < date(2050, 1, 1):
            year, month, day_number = from_gregorian(day)
            self.assertEqual(to_gregorian(year, month, day_number), day)
            day = day + timedelta(days=1)

    def test_the_known_leap_years_are_leap(self):
        self.assertTrue(is_leap_year(1403))
        self.assertTrue(is_leap_year(1408))
        self.assertFalse(is_leap_year(1404))
        self.assertFalse(is_leap_year(1409))

    def test_the_month_lengths_are_the_calendar_lengths(self):
        for month in range(1, 7):
            self.assertEqual(days_in_month(1405, month), 31)

        for month in range(7, 12):
            self.assertEqual(days_in_month(1405, month), 30)

        # Esfand is 29 days, or 30 in a leap year.
        self.assertEqual(days_in_month(1405, 12), 29)
        self.assertEqual(days_in_month(1403, 12), 30)

    def test_a_date_is_written_the_way_it_is_read(self):
        self.assertEqual(format_date(date(2026, 12, 22)), "۱ دی ۱۴۰۵")
        self.assertEqual(format_date(date(2026, 3, 21)), "۱ فروردین ۱۴۰۵")

    def test_numbers_are_written_in_persian_digits(self):
        self.assertEqual(persian_number(1405), "۱۴۰۵")
        self.assertEqual(persian_number("12"), "۱۲")

    def test_the_year_menu_starts_at_this_year(self):
        years = year_choices(date(2026, 10, 5))
        self.assertEqual(years[0], 1405)
        self.assertEqual(len(years), 5)

    def test_the_filter_writes_a_stored_date_and_skips_an_empty_one(self):
        rendered = Template("{{ value|jalali }}").render(Context({"value": date(2026, 12, 22)}))
        self.assertEqual(rendered, "۱ دی ۱۴۰۵")

        empty = Template("{{ value|jalali }}").render(Context({"value": None}))
        self.assertEqual(empty, "")
