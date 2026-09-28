from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class LoginForm(forms.Form):
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(
            attrs={"class": "field__input"}
        )
    )

    password = forms.CharField(
        label="گذرواژه",
        widget=forms.PasswordInput(
            attrs={"class": "field__input"}
        )
    )

    def clean(self):
        cleaned_data = super().clean()

        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if not username or not password:
            return cleaned_data

        user = User.objects.filter(username=username).first()

        if user and not user.is_active:
            raise forms.ValidationError(
                "این حساب غیرفعال است."
            )

        user = authenticate(
            username=username,
            password=password
        )

        if user is None:
            raise forms.ValidationError(
                "نام کاربری یا گذرواژه درست نیست."
            )

        cleaned_data["user"] = user

        return cleaned_data


class SignUpForm(forms.Form):
    username = forms.CharField(
        label="نام کاربری",
        max_length=150,
        help_text="حروف انگلیسی، رقم و نویسه‌های @ . + - _",
        widget=forms.TextInput(
            attrs={"class": "field__input"}
        )
    )

    email = forms.EmailField(
        label="ایمیل (اختیاری)",
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "field__input"}
        )
    )

    password1 = forms.CharField(
        label="گذرواژه",
        help_text="حداقل ۸ نویسه؛ نه بسیار ساده و نه فقط عدد.",
        widget=forms.PasswordInput(
            attrs={"class": "field__input"}
        )
    )

    password2 = forms.CharField(
        label="تکرار گذرواژه",
        widget=forms.PasswordInput(
            attrs={"class": "field__input"}
        )
    )

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "این نام کاربری قبلاً استفاده شده است."
            )

        return username

    def clean_password1(self):
        password = self.cleaned_data["password1"]

        validate_password(password)

        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data["password2"]

        if password1 != password2:
            raise forms.ValidationError(
                "دو گذرواژه یکسان نیستند."
            )

        return password2

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"]
        )

        return user
