from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.utils import timezone

from lessons.models import LanguageLevel

from .jalali import (
    MONTHS,
    days_in_month,
    from_gregorian,
    persian_number,
    to_gregorian,
    year_choices,
)
from .models import UserProfile


class LoginForm(forms.Form):
    # ``autocomplete`` is what lets a browser offer to fill and save these two values. It
    # is a hint, not a rule: an old account with a username that predates the sign-up
    # regex still signs in here, because this form deliberately does not apply that rule.
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(
            attrs={"class": "field__input", "autocomplete": "username"}
        )
    )

    password = forms.CharField(
        label="گذرواژه",
        widget=forms.PasswordInput(
            attrs={"class": "field__input", "autocomplete": "current-password"}
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
        help_text=(
            f"حروف انگلیسی، رقم و نویسه‌های @ . + - _ · "
            f"حداکثر {settings.USERNAME_MAX_LENGTH} نویسه"
        ),
        # The help text is a promise, and this is what keeps it: only the characters it
        # names are accepted. Django's own ``User.username`` allows far more (spaces, any
        # script, any symbol), so without this a learner could sign up with «کاربر۱۲۳» —
        # or with markup — after being told exactly what is allowed. The value is escaped
        # either way; this is about the contract the form makes, not about safety.
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9@.+\-_]+$",
                message="نام کاربری فقط می‌تواند شامل حروف انگلیسی، رقم و نویسه‌های @ . + - _ باشد.",
            )
        ],
        widget=forms.TextInput(
            attrs={"class": "field__input", "autocomplete": "username"}
        )
    )

    email = forms.EmailField(
        label="ایمیل (اختیاری)",
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "field__input", "autocomplete": "email"}
        )
    )

    password1 = forms.CharField(
        label="گذرواژه",
        help_text="حداقل ۸ نویسه؛ نه بسیار ساده و نه فقط عدد.",
        widget=forms.PasswordInput(
            attrs={"class": "field__input", "autocomplete": "new-password"}
        )
    )

    password2 = forms.CharField(
        label="تکرار گذرواژه",
        widget=forms.PasswordInput(
            attrs={"class": "field__input", "autocomplete": "new-password"}
        )
    )

    def clean_username(self):
        username = self.cleaned_data["username"]

        if len(username) < settings.USERNAME_MIN_LENGTH:
            raise forms.ValidationError(
                f"نام کاربری باید حداقل {settings.USERNAME_MIN_LENGTH} نویسه باشد."
            )

        if len(username) > settings.USERNAME_MAX_LENGTH:
            raise forms.ValidationError(
                f"نام کاربری نباید بیشتر از {settings.USERNAME_MAX_LENGTH} نویسه باشد."
            )

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
        # A password that failed its own validation never reached ``cleaned_data``, so
        # there is nothing to compare it with. Comparing against the missing value used to
        # report «دو گذرواژه یکسان نیستند» on top of the real error — a second, false
        # complaint about a pair of boxes that did match. Only two passwords that both
        # survived field validation are compared.
        if "password1" not in self.cleaned_data:
            return self.cleaned_data["password2"]

        password1 = self.cleaned_data["password1"]
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


class GoalForm(forms.Form):
    """The learner's goal: where they are, where they are going, and by when.

    A plain ``forms.Form`` (like the two above it) rather than a ``ModelForm``, and every
    field is optional on purpose: a learner may set a target and nothing else, and a
    learner who already has a goal can change one part of it without filling in the rest.
    Submitting every field empty clears the goal, which is a legitimate answer.

    The level choices are the levels that exist in the database — i.e. the levels the
    product actually has content for. A learner cannot select a level that no content
    can measure yet, and the goal page says so.
    """

    current_level = forms.ModelChoiceField(
        label="سطح فعلی",
        queryset=LanguageLevel.objects.all(),
        required=False,
        empty_label="هنوز نمی‌دانم",
        widget=forms.Select(attrs={"class": "field__input"}),
    )

    target_level = forms.ModelChoiceField(
        label="سطح هدف",
        queryset=LanguageLevel.objects.all(),
        required=False,
        empty_label="فعلاً هدفی تعیین نکرده‌ام",
        widget=forms.Select(attrs={"class": "field__input"}),
    )

    reason = forms.ChoiceField(
        label="چرا آلمانی یاد می‌گیری؟",
        required=False,
        widget=forms.Select(attrs={"class": "field__input"}),
    )

    # The date is chosen from three Jalali menus rather than the browser's own date picker.
    # That picker is the one control in the product that speaks the browser's locale, so a
    # learner in Iran was shown a Gregorian calendar with English month names — the single
    # place the Persian interface stopped being Persian. Three ``ChoiceField``s need no
    # widget to keep in sync, and ``clean`` turns them into the same stored ``target_date``
    # the rest of the product already reads; ``accounts/jalali.py`` owns the conversion.
    target_year = forms.ChoiceField(
        label="سال",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "field__input"}),
    )

    target_month = forms.ChoiceField(
        label="ماه",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "field__input"}),
    )

    target_day = forms.ChoiceField(
        label="روز",
        required=False,
        choices=[],
        help_text="تاریخ‌ها به تقویم هجری شمسی‌اند. اگر تاریخی نداری هر سه را خالی بگذار؛ در آن صورت وقتی هم پیشنهاد نمی‌کنیم.",
        widget=forms.Select(attrs={"class": "field__input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The reason's Persian labels live on the model (``UserProfile.REASON_LABELS``),
        # exactly like ``Word.type_label`` and ``Exercise.type_label``, so the form, the
        # profile page and the readiness page cannot drift apart.
        choices = [("", "انتخاب نشده")]
        for value, english_label in UserProfile.Reason.choices:
            if value in UserProfile.REASON_LABELS:
                choices.append((value, UserProfile.REASON_LABELS[value]))
            else:
                choices.append((value, english_label))
        self.fields["reason"].choices = choices

        # The stored date is the one value the view hands over (``initial["target_date"]``),
        # so the three menus are filled from it here and nothing else has to know the
        # calendars differ. Without a stored date the menus simply open on «انتخاب نشده».
        stored_date = None
        if "target_date" in self.initial:
            stored_date = self.initial["target_date"]

        # Every menu starts with a real blank. Without it the browser simply selects the
        # first option of each, so an untouched form submitted «۱ فروردین ۱۴۰۵» — a past
        # date the learner never chose — while the page promises that everything empty
        # clears the goal. The blank is what makes that promise true.
        blank = ("", "انتخاب نشده")

        years = year_choices(timezone.localdate())
        stored_year = None
        stored_month = None
        stored_day = None

        if stored_date is not None:
            stored_year, stored_month, stored_day = from_gregorian(stored_date)

            # A target date in the past is a legitimate answer — «آمادگی من» has a whole
            # state for it — so its year must stay selectable. Drop it from the choices and
            # reopening the form would show an empty menu and saving would quietly lose the
            # date.
            if stored_year not in years:
                years.insert(0, stored_year)

        year_options = [blank]
        for year in years:
            year_options.append((str(year), persian_number(year)))
        self.fields["target_year"].choices = year_options

        month_options = [blank]
        for number in range(1, 13):
            month_options.append((str(number), MONTHS[number - 1]))
        self.fields["target_month"].choices = month_options

        # Every day up to 31 is offered, because the menus are plain server-rendered HTML and
        # a day menu cannot know which month was picked without JavaScript. ``clean`` rejects
        # the combinations that do not exist (31 آذر, 30 اسفند in a common year).
        day_options = [blank]
        for number in range(1, 32):
            day_options.append((str(number), persian_number(number)))
        self.fields["target_day"].choices = day_options

        if stored_year is not None:
            self.initial["target_year"] = str(stored_year)
            self.initial["target_month"] = str(stored_month)
            self.initial["target_day"] = str(stored_day)

    def clean(self):
        cleaned_data = super().clean()

        current_level = cleaned_data.get("current_level")
        target_level = cleaned_data.get("target_level")

        if current_level is not None and target_level is not None:
            if target_level.order < current_level.order:
                raise forms.ValidationError(
                    "سطح هدف نمی‌تواند پایین‌تر از سطح فعلی باشد."
                )

        # The three date menus become the one stored date. Empty means "I have no date",
        # which is a real answer and clears the goal, so only a *partial* date is an error.
        year = cleaned_data.get("target_year")
        month = cleaned_data.get("target_month")
        day = cleaned_data.get("target_day")

        if not year and not month and not day:
            cleaned_data["target_date"] = None
        elif not year or not month or not day:
            raise forms.ValidationError(
                "تاریخ هدف را کامل انتخاب کن: سال، ماه و روز."
            )
        else:
            if int(day) > days_in_month(int(year), int(month)):
                raise forms.ValidationError(
                    "این روز در این ماه وجود ندارد؛ لطفاً روز را دوباره انتخاب کن."
                )
            cleaned_data["target_date"] = to_gregorian(int(year), int(month), int(day))

        return cleaned_data

    def save(self, profile):
        """Write the goal onto the profile and save it."""
        profile.current_level = self.cleaned_data["current_level"]
        profile.target_level = self.cleaned_data["target_level"]
        profile.reason = self.cleaned_data["reason"]
        profile.target_date = self.cleaned_data["target_date"]
        profile.save()
        return profile
