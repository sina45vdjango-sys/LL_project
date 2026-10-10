from django import views
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import GoalForm, LoginForm, SignUpForm
from .models import UserProfile
from . import xp
from .badges import badges_for


def _next_url(request):
    """Where the visitor was headed, or "" when the login page was opened directly.

    A link that stops at the login page links to `/accounts/login/?next=/somewhere/`,
    and the login form carries that value through the POST in a hidden field — so it
    is read from the POST first, then from the query string.
    """
    if "next" in request.POST:
        return request.POST["next"]
    if "next" in request.GET:
        return request.GET["next"]
    return ""


class LoginView(views.View):
    """The sign-in form, and where a learner lands after it.

    Both destinations are the dashboard. A learner signs in to learn, and the account
    page — which is where this used to send them — is a page of settings that answers
    none of the three questions the product is about (where am I, what is next, how do I
    continue). Any ``next`` a link supplied is still honoured; see ``post``.
    """

    template_name = "accounts/login.html"
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = LoginForm()
        return render(
            request,
            self.template_name,
            {"form": form, "next": _next_url(request)},
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)

            next_url = _next_url(request)

            # Only a `next` that points back at this site is followed. Without this
            # check, `/accounts/login/?next=https://evil.example` would turn the login
            # page into an open redirect that hands a freshly signed-in visitor to
            # another site.
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            # The dashboard, not the account page. A learner signs in to learn; landing on
            # a page of settings made the first post-login screen an administrative one.
            # The same reasoning as `SignUpView` sending a new account to its goal: the
            # destination should be the next thing to *do*. A `next` is still honoured
            # above, so every link that points at the login page keeps working.
            return redirect("home")
        return render(
            request,
            self.template_name,
            {"form": form, "next": _next_url(request)},
        )


class LogoutView(views.View):
    """Sign out, by POST only, because signing out changes state.

    The menu submits a real form (see templates/includes/account_menu.html), which is what
    keeps signing out safe from a link somebody could be tricked into opening. A ``GET``
    therefore used to answer 405 — and because Django has no default page for 405, that
    answer had an empty body: a learner who typed the address, or followed a stale link,
    saw a blank screen. It now redirects to the home page instead, which is where somebody
    who wants to sign out is about to want to be anyway, and it does not sign them out.
    """

    def get(self, request):
        return redirect("home")

    def post(self, request):
        logout(request)
        messages.success(
            request,
            "با موفقیت خارج شدید."
        )
        return redirect("accounts:login")


class SignUpView(views.View):
    template_name = "accounts/signup.html"
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = SignUpForm()
        return render(
            request,
            self.template_name,
            {"form": form},
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "حساب شما ساخته شد. خوش آمدید!"
            )
            # Straight to the goal, not to the account page. The goal is what switches the
            # product on — «امروز», the countdown and «آمادگی من» all read it — and it is the
            # one thing a brand-new learner cannot discover by looking around. The account
            # page is still where they end up, just after there is something to show on it.
            # `onboarding=1` is what marks the visit as part of the first-run flow, so the
            # goal page can explain itself and the step after it knows to keep going.
            return redirect(reverse("accounts:goal") + "?onboarding=1")
        return render(
            request,
            self.template_name,
            {"form": form},
        )


class ProfileView(views.View):
    template_name = "accounts/profile.html"
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        user_profile, _ = UserProfile.objects.get_or_create(
            user=request.user
        )

        # The three theme choices, in the order the page offers them. Built here rather
        # than written into the template so the radio values and their Persian labels
        # come from UserProfile.THEME_LABELS — the same dict ThemeView validates against.
        theme_options = []

        for value in UserProfile.THEME_LABELS:
            theme_options.append(
                {
                    "value": value,
                    "label": UserProfile.THEME_LABELS[value],
                }
            )

        # Whether a goal exists decides what this page is for. Without one, the page is
        # where a brand-new learner lands right after signing up, and the only thing that
        # matters is the one action that turns the product on: saying what they are working
        # towards. With one, the page is an account summary and the goal is a fact to read.
        has_goal = bool(
            user_profile.current_level
            or user_profile.target_level
            or user_profile.reason
            or user_profile.target_date
        )

        return render(
            request,
            self.template_name,
            {
                "profile": user_profile,
                "theme_options": theme_options,
                "has_goal": has_goal,
                "badges": badges_for(request.user, user_profile),
                "xp": xp.summary(user_profile),
            },
        )


class GoalView(views.View):
    """Where the learner says what they are working towards.

    Login-only, like the profile page: a goal belongs to a person. ``get`` shows the
    form already filled in with the current goal, ``post`` saves it and sends the
    learner to «آمادگی من» — the page whose answers change when a goal exists.

    ``?onboarding=1`` (set by ``SignUpView``) is carried through the whole first-run flow:
    it makes this page step one of two and tells ``post`` to hand the learner on to step
    two instead of dropping them somewhere with no next action.
    """

    template_name = "accounts/goal.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")

        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = GoalForm(
            initial={
                "current_level": user_profile.current_level,
                "target_level": user_profile.target_level,
                "reason": user_profile.reason,
                "target_date": user_profile.target_date,
            }
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "profile": user_profile,
                "onboarding": request.GET.get("onboarding") == "1",
            },
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")

        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = GoalForm(request.POST)

        if form.is_valid():
            form.save(user_profile)
            messages.success(
                request,
                "هدفت ذخیره شد."
            )
            # The learning plan is the destination either way — it is the page whose numbers
            # the goal just changed. During the first run the flag goes with it, which is what
            # turns that page into step two and gives the learner a way on to the dashboard.
            if request.POST.get("onboarding") == "1":
                return redirect(reverse("readiness") + "?onboarding=1")

            return redirect("readiness")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "profile": user_profile,
                "onboarding": request.POST.get("onboarding") == "1",
            },
        )


class ThemeView(views.View):
    """Where the learner picks the colour scheme.

    No form class: the page offers exactly three options, so the only thing that can be
    wrong is a value that is not one of them, and that is checked against
    ``UserProfile.THEME_LABELS``. The choice lives on the profile rather than in the
    browser, so it follows the learner to any device they sign in on.
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")

        if "theme" not in request.POST:
            return redirect("accounts:profile")

        chosen = request.POST["theme"]

        if chosen not in UserProfile.THEME_LABELS:
            messages.error(
                request,
                "پوستهٔ انتخاب‌شده معتبر نیست."
            )
            return redirect("accounts:profile")

        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_profile.theme = chosen
        user_profile.save()

        messages.success(
            request,
            "پوستهٔ نمایش ذخیره شد."
        )
        return redirect("accounts:profile")