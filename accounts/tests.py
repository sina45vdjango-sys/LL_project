"""Tests for the authentication surface.

Login/logout are Django's built-in views, so these tests focus on the wiring we
own: the URLs, the templates, the signup flow, profile access rules and the fact
that learning content stays public.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
        self.assertRedirects(response, reverse("accounts:profile"))
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

    def test_signed_in_user_is_sent_away_from_signup(self):
        user = User.objects.create_user(username="sina", password=PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), reverse("accounts:profile"))


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
        response = self.client.post(self.url, {"username": "sina", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_credentials_show_a_persian_error(self):
        response = self.client.post(self.url, {"username": "sina", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نام کاربری یا گذرواژه درست نیست.")
        self.assertNotIn("_auth_user_id", self.client.session)

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
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_signed_in_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class LogoutTests(TestCase):
    url = reverse("accounts:logout")

    def setUp(self):
        self.user = User.objects.create_user(username="sina", password=PASSWORD)
        self.client.force_login(self.user)

    def test_logout_requires_post(self):
        # Django 5+ removed GET logout; a link must not be able to sign you out.
        self.assertEqual(self.client.get(self.url).status_code, 405)

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


class AnonymousAccessTests(TestCase):
    """Anonymous-first: the learning content must stay public."""

    def test_public_pages_do_not_require_login(self):
        for name in ("lessons:lesson-list", "vocabulary:word-list", "exercises:exercise-list"):
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
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
