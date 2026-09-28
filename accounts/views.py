from django import views
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import LoginForm, SignUpForm
from .models import UserProfile


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
    template_name = "accounts/login.html"
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        form = LoginForm()
        return render(
            request,
            self.template_name,
            {"form": form, "next": _next_url(request)},
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
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

            return redirect("accounts:profile")
        return render(
            request,
            self.template_name,
            {"form": form, "next": _next_url(request)},
        )


class LogoutView(views.View):
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
            return redirect("accounts:profile")
        form = SignUpForm()
        return render(
            request,
            self.template_name,
            {"form": form},
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "حساب شما ساخته شد. خوش آمدید!"
            )
            return redirect("accounts:profile")
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
        return render(
            request,
            self.template_name,
            {"profile": user_profile},
        )