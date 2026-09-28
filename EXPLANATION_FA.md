<div dir="rtl">

<style>
pre, code { direction: ltr; text-align: left; unicode-bidi: embed; }
blockquote { border-right: 4px solid #4a90d9; padding-right: 10px; }
</style>

# راهنمای درک پروژه — اپ به اپ، خط به خط

این فایل برای این نوشته شده که پروژهٔ خودت را بفهمی و بتوانی در مصاحبهٔ Ausbildung از آن دفاع کنی. برای هر اپ سه چیز را می‌گوید:

1. **چرا هست؟** — این اپ چه مسئولیتی دارد و اگر نباشد چه می‌شود.
2. **خط به خط** — کد واقعی فایل با توضیح هر تکه.
3. **چطور توضیح بدهی؟** — جمله‌ای که می‌توانی در مصاحبه بگویی.

> **نکته:** دستورها و خروجی ترمینال را همیشه انگلیسی نگه دار. برای خواندن این فایل، در PyCharm یا VS Code با پیش‌نمایش مارک‌داون بازش کن تا راست‌به‌چپ درست نمایش داده شود.

---

## ۰. تصویر بزرگ: یک درخواست چطور حرکت می‌کند

هر صفحه در جنگو از همین پنج مرحله رد می‌شود:

```
مرورگر → config/urls.py → <app>/urls.py → یک View → مدل‌ها + یک تمپلیت → HTML
```

پس کل پروژه را این‌طور توضیح بده: **«`config` همه‌چیز را به هم وصل می‌کند، و چهار اپ هر کدام یک تکه از دامنهٔ مسئله را مالک هستند.»**

اپ‌ها:

| اپ | مسئولیت |
|---|---|
| `config` | تنظیمات، URL اصلی، context processor |
| `accounts` | کاربر، ورود، ثبت‌نام، پروفایل |
| `lessons` | ساختار دوره و مسیر یادگیری |
| `vocabulary` | کتابخانهٔ مشترک واژه/گرامر/جمله |
| `exercises` | سؤال، تمرین، تصحیح، تاریخچهٔ تلاش |
| `tests` | بررسی‌های سراسری پروژه (تست جنگو، نه تمرین) |

---

## ۱. `config/` — سیم‌کشی پروژه

این پوشه یک اپ نیست؛ بستهٔ پروژه است و هیچ منطق دامنه‌ای نباید داخلش باشد.

### `config/settings.py`

**چرا هست؟** جنگو بدون این فایل نمی‌داند چه اپی نصب است، به کدام دیتابیس وصل شود، و فایل‌های استاتیک کجا هستند.

```python
BASE_DIR = Path(__file__).resolve().parent.parent
```
مسیر ریشهٔ پروژه. `__file__` مسیر همین فایل است؛ دو بار `parent` می‌گیریم تا از `config/` به ریشه برسیم.

```python
SECRET_KEY = 'django-insecure-...'
DEBUG = True
ALLOWED_HOSTS = []
```
- `SECRET_KEY` برای امضای session و CSRF است. **الان داخل کد نوشته شده — این یک مشکل امنیتی است** (پایین‌تر توضیح داده شده).
- `DEBUG = True` فقط برای توسعه. در پروداکشن باید `False` باشد، وگرنه جزئیات خطا به کاربر نشان داده می‌شود.
- `ALLOWED_HOSTS` لیست دامنه‌هایی است که سرور به آن‌ها پاسخ می‌دهد. خالی یعنی فقط `localhost`.

```python
INSTALLED_APPS = [
    ...شش اپ داخلی جنگو...,
    'accounts', 'lessons', 'vocabulary', 'exercises', 'tests',
]
```
هر اپی که اینجا باشد، مدل‌هایش migrate می‌شوند و تمپلیت‌هایش پیدا می‌شوند. آن شش تای اول خود جنگو هستند: ادمین، احراز هویت، contenttypes، sessions، messages، staticfiles.

```python
MIDDLEWARE = [...]
```
لایه‌هایی که روی هر درخواست/پاسخ اجرا می‌شوند. مهم‌ترین‌ها:
- `SessionMiddleware` — کوکی session.
- `CsrfMiddleware` — محافظت CSRF روی فرم‌ها.
- `AuthenticationMiddleware` — `request.user` را پر می‌کند.

```python
TEMPLATES = [{
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [..., 'config.context_processors.shell']},
}]
```
- `DIRS` تمپلیت‌های سراسری در ریشهٔ پروژه.
- `APP_DIRS=True` یعنی هر اپ می‌تواند `templates/<app>/` خودش را داشته باشد.
- `shell` همان context processor است که برند و منو را به همهٔ صفحات می‌دهد.

```python
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", ...}}
```
اتصال به PostgreSQL. **پسورد هم داخل کد نوشته شده — همان مشکل امنیتی.**

```python
AUTH_PASSWORD_VALIDATORS = [...]
```
چهار اعتبارسنج رمز جنگو: شباهت به نام کاربری، حداقل طول، رمزهای رایج، فقط عدد نبودن.

```python
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
```
`en-us` است چون متن رابط کاربری را خودت در تمپلیت‌ها و فرم‌ها فارسی نوشته‌ای، نه با سیستم ترجمهٔ جنگو. `USE_TZ=True` یعنی همهٔ زمان‌ها timezone-aware هستند.

```python
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```
- `STATIC` فایل‌های خودِ پروژه است (CSS، JS، آیکون).
- `MEDIA` فایل‌هایی که **در زمان اجرا** ساخته/آپلود می‌شوند — یعنی همین فایل‌های صوتی درس‌ها (`audio` در مدل‌ها).

```python
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profile'
LOGOUT_REDIRECT_URL = '/'
```
مقصدهای پیش‌فرض احراز هویت. نکتهٔ مهم: محتوای آموزشی **عمومی** است؛ فقط `/accounts/profile/` ورود می‌خواهد.

```python
BRAND = {'name': 'گام‌به‌گام', 'name_lead': 'گام', ...}
```
نام محصول در یک جا. هر جا در سایت نام برند دیده می‌شود از این دیکشنری می‌آید، پس تغییر نام محصول = ویرایش همین دیکشنری.

**چطور توضیح بدهی:**
> «`settings.py` پیکربندی است: اپ‌های نصب‌شده، دیتابیس PostgreSQL، اعتبارسنج‌های رمز، مسیر static و media، و redirectهای ورود/خروج. عمداً هیچ منطق دامنه‌ای داخلش نیست.»

---

### `config/urls.py`

```python
urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('lessons/', include('lessons.urls')),
    path('vocabulary/', include('vocabulary.urls')),
    path('exercises/', include('exercises.urls')),
    path('tests/', include('tests.urls')),
]
```
- خط اول صفحهٔ خانه را مستقیم به `DashboardView` می‌بندد (چون URL آن خالی است، داخل هیچ اپی نمی‌گنجد).
- بقیه هر اپ را زیر یک پیشوند `include` می‌کنند. این یعنی جدول URL هر اپ در فایل خودش است، نه اینجا — یک‌جایی می‌شود ۵۰ خط.

```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```
در حالت توسعه، جنگو خودش فایل‌های media را سرو می‌کند. در پروداکشن این کار را وب‌سرور (nginx) انجام می‌دهد، پس مشروط به `DEBUG` است.

**چطور توضیح بدهی:**
> «`config/urls.py` دروازهٔ ورودی است: خانه را به داشبورد می‌بندد و بعد URL هر اپ را با `include` وصل می‌کند، پس هر اپ جدول URL خودش را دارد.»

---

### `config/context_processors.py`

**چرا هست؟** منوی سایت در **دو جا** رندر می‌شود: سایدبار دسکتاپ و نوار پایین موبایل. اگر لینک‌ها را در HTML هاردکد کنی، باید دو جا نگه‌داری کنی.

```python
NAV_ITEMS = [
    {"key": "dashboard", "label": "داشبورد", "url_name": "home",
     "view_name": "home", "icon": "home"},
    {"key": "lessons", "label": "درس‌ها", "url_name": "lessons:lesson-list",
     "app_names": ("lessons",), "icon": "steps"},
    ...
]
```
- `url_name` نام URL است؛ با `reverse()` به مسیر واقعی تبدیل می‌شود.
- `view_name` / `app_names` برای تشخیص «کدام آیتم فعال است».
- `icon` نام آیکون است، پس تمپلیت خودش تصمیم نمی‌گیرد.

```python
def resolve(url_name):
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None
```
نام URL را به مسیر تبدیل می‌کند. اگر آن URL هنوز وجود نداشته باشد، `None` می‌دهد.

```python
def is_active(item, request):
    match = request.resolver_match
    if match is None:
        return False
    if item.get("view_name") == match.view_name:
        return True
    if "app_names" in item:
        return match.app_name in item["app_names"]
```
تشخیص می‌دهد کاربر داخل کدام بخش است. دو حالت لازم است چون داشبورد در سطح پروژه روت شده (`view_name` دقیق) و بقیه در سطح اپ (`app_name`).

```python
def shell(request):
    nav_items = []
    for item in NAV_ITEMS:
        url = resolve(item["url_name"])
        if url is None:
            continue
        nav_items.append({..., "url": url, "active": is_active(item, request)})
```
ورودی‌ها را به شکل آمادهٔ رندر تبدیل می‌کند. `if url is None: continue` یعنی اگر اپی ساخته نشده باشد، لینک شکسته رندر نمی‌شود.

```python
    home_url = resolve("home")
    if home_url is None:
        home_url = resolve("lessons:lesson-list")
    if home_url is None:
        home_url = "/"
```
لینک خانه همیشه وجود دارد؛ اگر `home` نبود به لیست درس‌ها و در نهایت به `/` برمی‌گردد.

**چطور توضیح بدهی:**
> «منو در دو جا رندر می‌شود — سایدبار دسکتاپ و نوار موبایل — هر دو از یک فایل پارشال. به‌جای دو بار نوشتن لینک‌ها، یک لیست `NAV_ITEMS` دارم. context processor نام URL را با `reverse()` به مسیر تبدیل می‌کند، آیتم فعال را از `request.resolver_match` حساب می‌کند، و هر آیتمی که URL‌اش وجود ندارد را رد می‌کند تا لینک شکسته نباشد.»

---

## ۲. `accounts/` — کاربران

**چرا هست؟** احراز هویت و یک پروفایل کوچک. این اپ **الگوی سبک کدنویسی** کل پروژه است.

### `accounts/models.py`

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
```
- `OneToOneField` یعنی هر کاربر **دقیقاً یک** پروفایل دارد. این همان الگوی کلاسیک «گسترش مدل User» است.
- `on_delete=CASCADE` یعنی اگر کاربر حذف شود، پروفایل هم می‌رود.
- `related_name="profile"` یعنی از سمت کاربر می‌شود `user.profile` نوشت.

```python
    current_level = models.ForeignKey("lessons.LanguageLevel", on_delete=models.SET_NULL,
                                      related_name="user_profiles", blank=True, null=True)
```
- `"lessons.LanguageLevel"` به‌صورت رشته نوشته شده تا circular import نشود.
- `on_delete=SET_NULL` یعنی اگر سطح زبانی حذف شود، کاربر حذف نمی‌شود؛ فقط مقدارش `NULL` می‌شود. این انتخاب عمدی است.
- `blank=True, null=True` یعنی اختیاری.

```python
    native_language = models.CharField(max_length=10, default="fa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Profile of {self.user.username}"
```
- `auto_now_add=True` یعنی موقع ساخت خودکار پر می‌شود و دیگر تغییر نمی‌کند.
- `ordering` پیش‌فرض کوئری‌ها را جدیدترین‌اول می‌کند.
- `__str__` همان چیزی است که در `/admin/` دیده می‌شود.

### `accounts/signals.py`

```python
@receiver(post_save, sender=User, dispatch_uid="accounts.create_user_profile")
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
```
- `post_save` بعد از ذخیرهٔ `User` اجرا می‌شود.
- `created=True` یعنی همین حالا ساخته شده (نه ویرایش شده) — پس فقط موقع ساخت پروفایل می‌سازیم.
- `get_or_create` یعنی اگر از قبل بود، خطا نمی‌دهد.
- `dispatch_uid` جلوی ثبت دوبارهٔ سیگنال را می‌گیرد.

**چرا هست؟** تا هیچ ویویی مجبور نباشد یادش باشد پروفایل بسازد.

### `accounts/forms.py`

```python
class LoginForm(forms.Form):
    username = forms.CharField(label="نام کاربری", widget=forms.TextInput(attrs={"class": "field__input"}))
    password = forms.CharField(label="گذرواژه", widget=forms.PasswordInput(attrs={"class": "field__input"}))
```
برچسب‌ها فارسی‌اند و کلاس CSS از طریق `attrs` تزریق می‌شود تا تمپلیت تمیز بماند.

```python
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        if not username or not password:
            return cleaned_data
```
`clean` اعتبارسنجی سطح-فرم است. اینجا `get` استفاده شده چون ممکن است یکی از فیلدها اصلاً معتبر نبوده و در `cleaned_data` نباشد.

```python
        user = User.objects.filter(username=username).first()
        if user and not user.is_active:
            raise forms.ValidationError("این حساب غیرفعال است.")

        user = authenticate(username=username, password=password)
        if user is None:
            raise forms.ValidationError("نام کاربری یا گذرواژه درست نیست.")

        cleaned_data["user"] = user
        return cleaned_data
```
- اول بررسی حساب غیرفعال، بعد `authenticate` که رمز را چک می‌کند.
- پیام خطا عمداً کلی است تا معلوم نشود کدام‌یک غلط بوده (امنیت).
- کاربر تأییدشده در `cleaned_data["user"]` گذاشته می‌شود تا ویو فقط `login()` صدا بزند.

```python
class SignUpForm(forms.Form):
    username = forms.CharField(...)
    email = forms.EmailField(label="ایمیل (اختیاری)", required=False, ...)
    password1 = forms.CharField(...)
    password2 = forms.CharField(...)
```
`required=False` یعنی ایمیل اختیاری است.

```python
    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("این نام کاربری قبلاً استفاده شده است.")
        return username
```
`clean_<field>` منحصراً همان فیلد را اعتبارسنجی می‌کند. اینجا تکراری بودن نام کاربری.

```python
    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password
```
رمز را به اعتبارسنج‌های خود جنگو (همان چهارتای `settings.py`) می‌دهد.

```python
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError("دو گذرواژه یکسان نیستند.")
        return password2
```
اینجا `get` استفاده شده چون اگر `password1` خطا داشته باشد ممکن است وجود نداشته باشد.

```python
    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )
        return user
```
`create_user` خودش رمز را **هش** می‌کند. هرچند `User.objects.create(...)` رمز را خام ذخیره می‌کرد — این تفاوت امنیتی مهم است.

### `accounts/views.py`

```python
class LoginView(views.View):
    template_name = "accounts/login.html"
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        form = LoginForm()
        return render(request, self.template_name, {"form": form, "next": _next_url(request)})
```
- از `django.views.View` ارث می‌برد و `get`/`post` را صریح می‌نویسد (به‌جای `FormView` که رفتار پنهان دارد).
- اگر کاربر قبلاً وارد شده باشد، دوباره فرم نمی‌بیند.

```python
def _next_url(request):
    if "next" in request.POST:
        return request.POST["next"]
    if "next" in request.GET:
        return request.GET["next"]
    return ""
```
`?next=` یعنی «کاربر از کجا آمده». چون فرم مقدارش را در یک input مخفی نگه می‌دارد، اول از POST خوانده می‌شود.

```python
    def post(self, request):
        ...
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            next_url = _next_url(request)
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("accounts:profile")
```
- `login()` session را می‌سازد.
- **`url_has_allowed_host_and_scheme` حیاتی است.** بدون آن، `?next=https://evil.example` صفحهٔ ورود را به یک open redirect تبدیل می‌کند که کاربر تازه‌وارد‌شده را به سایت مهاجم می‌فرستد. این خط را در مصاحبه حتماً نام ببر.

```python
class LogoutView(views.View):
    def post(self, request):
        logout(request)
        messages.success(request, "با موفقیت خارج شدید.")
        return redirect("accounts:login")
```
فقط `post` دارد، پس خروج با یک لینک GET انجام نمی‌شود (که یک ضعف امنیتی رایج است).

```python
class SignUpView(views.View):
    def post(self, request):
        ...
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "حساب شما ساخته شد. خوش آمدید!")
            return redirect("accounts:profile")
```
بعد از ثبت‌نام خودکار وارد می‌شود تا کاربر لازم نباشد دو بار فرم پر کند.

```python
class ProfileView(views.View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return render(request, self.template_name, {"profile": user_profile})
```
تنها صفحه‌ای که ورود می‌خواهد. `get_or_create` یعنی حتی اگر سیگنال پروفایل را نساخته باشد، صفحه کار می‌کند.

### `accounts/urls.py`

```python
app_name = "accounts"
urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
```
`app_name` فضای نام می‌سازد، پس همه‌جای پروژه می‌نویسی `reverse("accounts:login")` و نام‌ها با اپ‌های دیگر تصادم نمی‌کنند.

### `accounts/admin.py`

```python
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0

class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = (*BaseUserAdmin.list_display, "date_joined")

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
```
- Inline یعنی پروفایل داخل همان صفحهٔ کاربر ادمین ویرایش می‌شود.
- `can_delete = False` چون پروفایل نباید جدا از کاربر حذف شود.
- `unregister`/`register` یعنی ادمین پیش‌فرض جنگو را با نسخهٔ خودمان عوض می‌کنیم.

**چطور توضیح بدهی:**
> «`accounts` مالک هویت است. مدل `User` جنگو را برای احراز هویت نگه داشتم و `UserProfile` را برای داده‌های اختصاصی اپ اضافه کردم که با یک سیگنال `post_save` ساخته می‌شود. ورود هم `?next=` را رعایت می‌کند، ولی فقط بعد از بررسی `url_has_allowed_host_and_scheme` تا open redirect نشود.»

---

## ۳. `lessons/` — ساختار دوره و مسیر یادگیری

**چرا هست؟** ستون فقرات محصول. همه‌چیز از یک `Lesson` آویزان است.

### `lessons/models.py`

```python
class LanguageLevel(models.Model):
    level = models.CharField(max_length=2, unique=True)
    title = models.CharField(max_length=40)
    order = models.PositiveIntegerField(unique=True)
    class Meta:
        ordering = ["order"]
```
سطح‌های A1 تا C2. `unique=True` جلوی تکرار را می‌گیرد، `order` ترتیب نمایش را تعیین می‌کند.

```python
class Course(models.Model):
    language_level = models.OneToOneField(LanguageLevel, on_delete=models.CASCADE, related_name="course")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
```
`OneToOneField` یعنی هر سطح دقیقاً یک دوره دارد. `is_published` همان الگوی «پیش‌نویس دیده نشود» است که در کل پروژه تکرار می‌شود.

```python
class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    estimated_time = models.PositiveIntegerField()

    class Meta:
        ordering = ["course", "order"]
        constraints = [
            models.UniqueConstraint(fields=["course", "order"], name="unique_lesson_order_per_course")
        ]
```
`UniqueConstraint` یعنی در سطح **دیتابیس** نمی‌شود دو درس با شمارهٔ یکسان در یک دوره داشت. این را در مصاحبه برجسته کن: «ترتیب را در کد تضمین نکردم، در دیتابیس تضمین کردم.»

```python
class LessonContent(models.Model):
    class ContentType(models.TextChoices):
        EXPLANATION = "EXPLANATION", "Explanation"
        VOCABULARY = "VOCABULARY", "Vocabulary"
        GRAMMAR = "GRAMMAR", "Grammar"
        EXAMPLE = "EXAMPLE", "Example"
        DIALOGUE = "DIALOGUE", "Dialogue"
        NOTE = "NOTE", "Note"
```
`TextChoices` مقادیر مجاز را به‌صورت کلاس تعریف می‌کند؛ هم اعتبارسنجی می‌دهد، هم خوانا است.

```python
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="contents")
    type = models.CharField(max_length=20, choices=ContentType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    audio = models.FileField(upload_to="contents/audio/", blank=True, null=True)
    order = models.PositiveIntegerField()
```
**چرا این مدل هست؟** به‌جای یک فیلد متن غول‌آسا در `Lesson`، درس به بلوک‌های مرتب و نوع‌دار تقسیم شده. پس می‌شود یک درس را از قطعات مختلف ساخت.

```python
class LessonWord(models.Model):
    class Role(models.TextChoices):
        NEW = "NEW", "New"
        REVIEW = "REVIEW", "Review"
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_words")
    word = models.ForeignKey("vocabulary.Word", on_delete=models.CASCADE, related_name="lesson_links")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.NEW)
    order = models.PositiveIntegerField()
```
**مهم‌ترین ایدهٔ این فایل:** `LessonWord` یک جدول واسط با ویژگی است. یک واژه داخل درس «زندگی» نمی‌کند؛ همان واژه می‌تواند در درس ۳ با نقش `NEW` و در درس ۹ با نقش `REVIEW` بیاید. قید `UniqueConstraint(lesson, word)` یعنی در یک درس تکراری نباشد ولی در درس‌های مختلف آزاد باشد.

`LessonGrammar` و `LessonSentence` هم دقیقاً همین الگو هستند: واسط بین درس و محتوای مشترک.

```python
class LessonProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    class Step(models.TextChoices):
        INTRO = "intro", "Introduction"
        EXPLANATION = "explanation", "Explanation"
        ... (ده گام)
```
- `Status` وضعیت درس برای یک کاربر است.
- `Step` نام گام‌ها؛ همان ده نامی که `journey.py` می‌سازد. تست‌ها بررسی می‌کنند این دو از هم جدا نیفتند.

```python
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="user_progress")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    current_step = models.CharField(max_length=20, choices=Step.choices, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "lesson"], name="unique_user_lesson_progress")]
```
`settings.AUTH_USER_MODEL` به‌جای `User` مستقیم — روش درست در جنگو، چون اگر بعداً مدل کاربر عوض شود کد نمی‌شکند. قید یکتا یعنی برای هر (کاربر، درس) فقط یک ردیف پیشرفت وجود دارد.

### `lessons/journey.py` — خط به خط

**چرا هست؟** درس نباید گام گرامر خالی نشان دهد فقط چون نویسنده گرامری وصل نکرده. این فایل تصمیم می‌گیرد چه گام‌هایی **وجود دارند**، و هیچ‌وقت در دیتابیس نمی‌نویسد.

```python
from collections import defaultdict
from .models import LessonContent, LessonSentence
```
`defaultdict(list)` دیکشنری‌ای است که کلید نداشته، خودکار یک لیست خالی می‌شود.

```python
_BLOCK_STEP = {
    LessonContent.ContentType.EXPLANATION: "explanation",
    LessonContent.ContentType.NOTE: "explanation",
    LessonContent.ContentType.GRAMMAR: "grammar",
    LessonContent.ContentType.VOCABULARY: "vocabulary",
    LessonContent.ContentType.EXAMPLE: "examples",
    LessonContent.ContentType.DIALOGUE: "dialogue",
}
```
نقشهٔ «نوع بلوک ← کدام گام». `NOTE` عمداً با `EXPLANATION` یکی شده چون هر دو متن پیوسته‌اند.

```python
_SENTENCE_STEPS = (
    ("examples", LessonSentence.Role.EXAMPLE),
    ("dialogue", LessonSentence.Role.DIALOGUE),
    ("reading",  LessonSentence.Role.READING),
    ("listening",LessonSentence.Role.LISTENING),
)
```
چهار جفت `(کلید گام، نقش جمله)`. به‌صورت داده نوشته شده تا در `build_journey` یک حلقه کافی باشد و ترتیب نمایش هم یک‌جا دیده شود.

```python
_STEP_SPEC = {
    "intro": {"label": "آغاز", "title": "نقشهٔ این درس", "hint": "...", "unit": "", "template": "lessons/steps/_intro.html"},
    ...
}
```
تنها تعریف برچسب، عنوان، راهنما، واحد شمارش و **تمپلیت جزئی** هر گام. چون `template` داده است، `lesson_detail.html` فقط حلقه می‌زند و `{% include %}` می‌کند، به‌جای ده بخش تکراری.

```python
def _step(key, count, **extra):
    step = {"key": key, "count": count}
    step.update(_STEP_SPEC[key])
    step.update(extra)
    return step
```
یک گام می‌سازد: کلید و شمارش، بعد مشخصات، بعد هر چیز اضافه‌ای که صداکننده داده (`blocks=`، `sentences=`). اگر کلید غلط باشد `KeyError` می‌دهد — خطای بلند که خوب است.

```python
def build_journey(*, blocks, grammar_links, sentence_links, word_page, exercises):
```
`*` همهٔ پارامترها را **keyword-only** می‌کند، پس صداکننده باید `build_journey(blocks=...)` بنویسد. جلوی این باگ را می‌گیرد که دو لیست جای هم داده شوند.

```python
    blocks_by_step = defaultdict(list)
    for block in blocks:
        blocks_by_step[_BLOCK_STEP.get(block.type, "explanation")].append(block)

    sentences_by_role = defaultdict(list)
    for link in sentence_links:
        sentences_by_role[link.role].append(link)

    word_total = word_page.paginator.count
```
- بلوک‌ها بر اساس گامشان گروه‌بندی می‌شوند. `get(..., "explanation")` یعنی نوع ناشناخته به گام توضیح می‌رود، نه کرش.
- جمله‌ها بر اساس نقش.
- `word_page.paginator.count` تعداد **کل** واژه‌هاست، نه فقط واژه‌های صفحهٔ جاری — پس گام می‌تواند «۵۰ واژه» نشان دهد در حالی که ۲۴ تا روی صفحه است.

```python
    steps = [_step("intro", 0)]
```
گام آغاز همیشه هست.

```python
    if blocks_by_step["explanation"]:
        steps.append(_step("explanation", len(blocks_by_step["explanation"]), blocks=blocks_by_step["explanation"]))
```
این `if` تمام نکته است: بلوک توضیح نباشد، گام توضیح هم نیست.

```python
    if word_total:
        steps.append(_step("vocabulary", word_total, blocks=blocks_by_step["vocabulary"],
                           words=list(word_page), word_page=word_page))
    if grammar_links:
        steps.append(_step("grammar", len(grammar_links), blocks=blocks_by_step["grammar"], grammar=grammar_links))
```
گام واژگان فقط با واژه، گام گرامر فقط با گرامر.

```python
    for key, role in _SENTENCE_STEPS:
        sentences = sentences_by_role.get(role, [])
        if sentences or blocks_by_step[key]:
            steps.append(_step(key, len(sentences), blocks=blocks_by_step[key], sentences=sentences))
```
یک حلقه برای چهار گام جمله‌ای. شرط نشان می‌دهد گام هست اگر جمله داشته باشد **یا** بلوک متنی دربارهٔ آن — تا صفحهٔ خالی نمایش داده نشود.

```python
    if exercises:
        steps.append(_step("practice", len(exercises), exercises=exercises))

    steps.append(_step("finish", 0))
    return steps
```
تمرین فقط با تمرین؛ پایان همیشه آخر.

```python
def content_step_count(steps):
    total = 0
    for step in steps:
        if step["key"] not in ("intro", "finish"):
            total += 1
    return total
```
تعداد گام‌های **دارای محتوا** — بدون آغاز و پایان — تا «گام ۱ از ۷» بامعنا باشد.

### `lessons/progress.py` — خط به خط

**چرا هست؟** تنها جایی که `LessonProgress` خوانده و نوشته می‌شود. پس قواعد دقیقاً یک بار نوشته شده‌اند.

```python
BROWSER_STATUS = {
    LessonProgress.Status.IN_PROGRESS: "started",
    LessonProgress.Status.COMPLETED: "completed",
}
```
وضعیت دیتابیس را به دو کلمه‌ای که JS می‌فهمد ترجمه می‌کند. `NOT_STARTED` عمداً **نیست**: درسی که باز نشده، هیچ ورودی ندارد — پس «شروع‌نشده» یک واقعیت است، نه کلمهٔ سوم.

```python
def _iso(value):
    if value is None:
        return None
    return value.isoformat()
```
تاریخ → رشتهٔ ISO. مرورگر خودش قالب‌بندی می‌کند.

```python
def _row(user, lesson, step):
    now = timezone.now()
    row, _ = LessonProgress.objects.get_or_create(
        user=user, lesson=lesson,
        defaults={"status": LessonProgress.Status.IN_PROGRESS, "current_step": step,
                  "started_at": now, "last_activity_at": now},
    )
    return row
```
مهم‌ترین هلپر:
- `get_or_create` دو مقدار برمی‌گرداند؛ `_` یعنی `created` را لازم نداریم.
- `defaults` **فقط موقع ساخت** استفاده می‌شود. پس در بازدید دوم، ردیف موجود دست‌نخورده برمی‌گردد — این‌طور `started_at` هرگز جابه‌جا نمی‌شود.
- ردیف از همان ابتدا `IN_PROGRESS` ساخته می‌شود، پس مسیر جدا برای «شروع درس» لازم نیست.

```python
def record_step(user, lesson, step):
    row = _row(user, lesson, step)
    row.current_step = step
    row.last_activity_at = timezone.now()
    if row.status != LessonProgress.Status.COMPLETED:
        row.status = LessonProgress.Status.IN_PROGRESS
    row.save()
    return row
```
- گام جاری و زمان فعالیت به‌روز می‌شود.
- `if` ظریف و عمدی: **مرور دوبارهٔ درس تمام‌شده، آن را «تمام‌نشده» نمی‌کند.** بدون این خط، گشتن در درس تکمیل‌شده وضعیت را برمی‌گرداند.

```python
def complete_lesson(user, lesson, step):
    row = _row(user, lesson, step)
    now = timezone.now()
    row.status = LessonProgress.Status.COMPLETED
    if row.completed_at is None:
        row.completed_at = now
    row.last_activity_at = now
    if step:
        row.current_step = step
    row.save()
    return row
```
- وضعیت همیشه `COMPLETED` می‌شود.
- `if row.completed_at is None` یعنی **اولین اتمام برنده است.** اتمام دوباره، زمان را صفر نمی‌کند، پس `completed_at - started_at` همان مدت واقعی درس می‌ماند.
- `if step:` فقط اگر گام معتبری فرستاده شده باشد.

```python
def progress_dict(row):
    return {"status": row.status, "current_step": row.current_step,
            "started_at": _iso(row.started_at), "last_activity_at": _iso(row.last_activity_at),
            "completed_at": _iso(row.completed_at)}
```
پیشرفت **یک درس** — همان JSON که endpoint پست برمی‌گرداند.

```python
def progress_state(user):
    rows = LessonProgress.objects.filter(user=user).order_by("-last_activity_at")
    lessons = {}
    last_lesson_id = None
    for row in rows:
        if row.status == LessonProgress.Status.NOT_STARTED:
            continue
        lessons[row.lesson_id] = {"status": BROWSER_STATUS[row.status], "updatedAt": _iso(row.last_activity_at)}
        if last_lesson_id is None and row.last_activity_at is not None:
            last_lesson_id = row.lesson_id
    return {"source": "server", "lessons": lessons, "lastLessonId": last_lesson_id}
```
- `-last_activity_at` یعنی جدیدترین فعالیت اول.
- ردیف‌های `NOT_STARTED` رد می‌شوند، پس `BROWSER_STATUS[row.status]` هیچ‌وقت `KeyError` نمی‌دهد.
- حلقهٔ آخر «آخرین درس لمس‌شده» را پیدا می‌کند؛ چون ردیف‌ها جدیدترین‌اول هستند، اولین ردیف قابل استفاده خودش همان است.
- **تفاوت کلیدی:** `progress_state` = همهٔ درس‌ها (برای داشبورد/مسیر)، `progress_dict` = یک درس (برای پاسخ پست).

### `lessons/views.py` — خط به خط

```python
WORDS_PER_STEP = 24
```
یک ثابت نام‌دار به‌جای عدد جادویی. درس‌ها تا ~۱۷۰ واژه دارند، پس گام واژگان صفحه‌بندی می‌شود.

```python
def _lesson_payload(lessons):
    return [
        {"id": lesson.pk, "order": lesson.order, "title": lesson.title,
         "minutes": lesson.estimated_time,
         "url": reverse("lessons:lesson-detail", args=[lesson.pk])}
        for lesson in lessons
    ]
```
کمینهٔ اطلاعاتی که مرورگر لازم دارد تا یک id ذخیره‌شده را به عنوان و لینک تبدیل کند. `reverse` مسیر را از نام می‌سازد، پس هیچ‌جا مسیر دستی تایپ نمی‌شود.

```python
def _published_courses():
    return (Course.objects.filter(is_published=True, lessons__is_published=True)
            .select_related("language_level").distinct().order_by("language_level__order", "pk"))
```
- `lessons__is_published=True` یعنی دوره‌ای که درس منتشرشده ندارد حساب نمی‌شود.
- این join ممکن است هر دوره را به‌تعداد درس‌هایش برگرداند، پس `.distinct()` تکراری‌ها را حذف می‌کند.
- `select_related` سطح را در **همان کوئری** می‌آورد — جلوی N+1 را می‌گیرد.

```python
def _path_context(course, groups, lessons, user):
    total_minutes = 0
    for lesson in lessons:
        total_minutes += lesson.estimated_time
    return {"course": course, "courses": list(_published_courses()), "groups": groups,
            "first_lesson": lessons[0] if lessons else None, "lesson_total": len(lessons),
            "hours_total": round(total_minutes / 60), "lessons_payload": _lesson_payload(lessons),
            "progress_state": progress_state(user) if user.is_authenticated else None}
```
سازندهٔ context مشترک دو صفحهٔ «مسیر». `lessons[0] if lessons else None` حالت خالی را می‌گیرد. خط آخر قانون «اول مهمان» است: فقط کاربر وارد‌شده پیشرفت سروری می‌گیرد، بقیه `None` و از `localStorage` استفاده می‌کنند.

```python
class DashboardView(View):
    def get(self, request, *args, **kwargs):
        course = (Course.objects.filter(is_published=True).select_related("language_level")
                  .order_by("language_level__order", "pk").first())
        lessons = []
        if course is not None:
            lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))
```
اولین دورهٔ منتشرشده در ترتیب سطح. پیش‌فرض لیست خالی، بعد پر می‌شود — پس دیتابیس خالی هم صفحه را می‌شکند نه.

```python
        return render(request, "dashboard.html", {
            ..., "word_total": Word.objects.filter(is_published=True).count(),
            "grammar_total": Grammar.objects.filter(is_published=True).count(),
            "exercise_total": Exercise.objects.filter(is_published=True).count(),
            "progress_state": progress_state(request.user) if request.user.is_authenticated else None,
        })
```
اعداد واقعی از دیتابیس، نه عدد ثابت در تمپلیت.

**چرا `DashboardView` داخل `lessons` است نه `config`؟** چون به `Course`، `Lesson`، `Word`، `Grammar` و `Exercise` نیاز دارد — یک ویوی محصولی است و `config` باید فقط سیم‌کشی بماند.

```python
class CourseDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        course = get_object_or_404(Course.objects.select_related("language_level"), pk=pk, is_published=True)
        lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))
        groups = [{"course": course, "level": course.language_level, "lessons": lessons}]
        return render(request, "lessons/course_detail.html", _path_context(course, groups, lessons, request.user))
```
`get_object_or_404` برای دورهٔ ناموجود یا منتشرنشده ۴۰۴ می‌دهد. `groups` یک لیست **یک‌عضوی** است تا تمپلیت همان حلقهٔ صفحهٔ چنددوره‌ای را دوباره استفاده کند.

```python
class LessonDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course__language_level"),
            pk=pk, is_published=True, course__is_published=True)
```
`course__is_published=True` یعنی درس داخل دورهٔ منتشرنشده ۴۰۴ است — با حدس زدن id نمی‌شود به محتوای مخفی رسید.

```python
        blocks = list(lesson.contents.order_by("order", "pk"))
        grammar_links = list(lesson.lesson_grammars.filter(grammar__is_published=True)
                             .select_related("grammar").order_by("order", "pk"))
        sentence_links = list(lesson.lesson_sentences.filter(sentence__is_published=True)
                              .select_related("sentence").order_by("order", "pk"))
        word_links = (lesson.lesson_words.filter(word__is_published=True)
                      .select_related("word").order_by("order", "pk"))
```
چهار کوئری، هر کدام مرتب و با `select_related`. `list(...)` باعث می‌شود کوئری همین‌جا یک بار اجرا شود، نه داخل حلقهٔ تمپلیت.

```python
        word_page = Paginator(word_links, WORDS_PER_STEP).get_page(request.GET.get("words_page"))
```
صفحه‌بندی واژه‌ها. `get_page` با `?words_page=` نامعتبر یا غایب، بی‌خطا به صفحهٔ اول می‌رود.

```python
        exercises = list(lesson.exercises.filter(is_published=True)
                         .annotate(question_count=Count("questions")).order_by("order", "pk"))
```
`annotate` تعداد سؤال‌ها را در همان کوئری اضافه می‌کند، پس تمپلیت «۵ سؤال» را بدون کوئری جدا نشان می‌دهد.

```python
        steps = build_journey(blocks=blocks, grammar_links=grammar_links,
                              sentence_links=sentence_links, word_page=word_page, exercises=exercises)
```
جان مطلب: ویو داده را جمع می‌کند، **`journey.py` شکل را تعیین می‌کند.** ویو نمی‌داند چه گام‌هایی وجود دارد.

```python
        lesson_progress = None
        resume_step = None
        if request.user.is_authenticated:
            lesson_progress = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
            if lesson_progress:
                for position, step in enumerate(steps):
                    if step["key"] == lesson_progress.current_step:
                        resume_step = position
                        break
```
فقط برای کاربر وارد‌شده. حلقه می‌فهمد کاربر کجا مانده و **موقعیت** را نگه می‌دارد. اگر درس عوض شده و آن گام دیگر نیست، حلقه تمام می‌شود و `resume_step` برابر `None` می‌ماند — خراب نمی‌شود، فقط ادامه نمی‌دهد.

```python
        siblings = lesson.course.lessons.filter(is_published=True).order_by("order", "pk")
        return render(request, "lessons/lesson_detail.html", {
            ..., "previous_lesson": siblings.filter(order__lt=lesson.order).last(),
            "next_lesson": siblings.filter(order__gt=lesson.order).first(),
            "resume_step": resume_step,
            "progress_state": progress_state(request.user) if request.user.is_authenticated else None,
        })
```
`order__lt` و `order__gt` درس قبلی/بعدی را بر اساس **موقعیت** پیدا می‌کنند، نه id. همهٔ گام‌ها کامل رندر می‌شوند و فقط JS تصمیم می‌گیرد کدام دیده شود — پس درس بدون جاوااسکریپت هم خواندنی است.

```python
class LessonProgressView(LoginRequiredMixin, View):
    raise_exception = True

    def post(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(Lesson, pk=pk, is_published=True)

        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        step = payload.get("step", "")
        if step not in LessonProgress.Step.values:
            return JsonResponse({"error": "unknown step"}, status=400)

        if payload.get("complete") is True:
            row = complete_lesson(request.user, lesson, step)
        else:
            row = record_step(request.user, lesson, step)

        return JsonResponse(progress_dict(row))
```
- `raise_exception = True` یعنی کاربر مهمان **۴۰۳** می‌گیرد، نه redirect به صفحهٔ ورود — چون redirect پاسخ بی‌معنی‌ای به یک `fetch()` است.
- `request.body or "{}"` بدنهٔ خالی را می‌گیرد؛ `json.loads` روی رشتهٔ خالی خطا می‌داد.
- گام با `LessonProgress.Step.values` اعتبارسنجی می‌شود — دیتابیس منبع حقیقت است.
- `is True` (نه فقط truthy) تا فقط مقدار بولی واقعی قبول شود.
- **چرا POST و نه GET؟** چون GET باید فقط خواندن باشد. با باز شدن صفحه هیچ‌چیز نوشته نمی‌شود و برای مهمان هم چیزی ذخیره نمی‌شود.

```python
class LessonListView(View):
    def get(self, request, *args, **kwargs):
        groups, lessons = [], []
        for course in _published_courses():
            course_lessons = list(course.lessons.filter(is_published=True).order_by("order", "pk"))
            lessons.extend(course_lessons)
            groups.append({"course": course, "level": course.language_level, "lessons": course_lessons})
        return render(request, "lessons/lesson_list.html", _path_context(None, groups, lessons, request.user))
```
یک حلقه هم نمای گروهی و هم لیست تخت را می‌سازد. **عمداً صفحه‌بندی نشده:** مسیری که بین صفحات بشکند دیگر مسیر نیست.

**چطور توضیح بدهی:**
> «ویوهای `lessons` منطق کسب‌وکار ندارند. `journey.py` یک تابع خالص است که محتوای درس را به فهرست مرتب گام‌ها تبدیل می‌کند و گام فقط وقتی ساخته می‌شود که محتوایی برای نمایش باشد. `progress.py` تنها ماژولی است که `LessonProgress` را می‌نویسد، پس قواعد یک بار نوشته شده‌اند: `started_at` یک بار، `completed_at` یک بار، و مرور درس تمام‌شده آن را تمام‌نشده نمی‌کند.»

---

## ۴. `vocabulary/` — کتابخانهٔ محتوای مشترک

**چرا هست؟** استخر مشترک واژه، گرامر و جمله که هم `lessons` و هم `exercises` از آن استفاده می‌کنند. جدا کردنش مانع تکرار محتوا می‌شود.

### `vocabulary/models.py`

```python
class Word(models.Model):
    class WordType(models.TextChoices):
        NOUN = "NOUN", "Noun"
        ... (VERB, ADJECTIVE, ADVERB, PREPOSITION, PRONOUN, OTHER)

    class Gender(models.TextChoices):
        MASCULINE = "M", "Masculine (der)"
        FEMININE = "F", "Feminine (die)"
        NEUTER = "N", "Neuter (das)"

    class PerfectAuxiliary(models.TextChoices):
        HABEN = "HABEN", "Haben"
        SEIN = "SEIN", "Sein"
```
سه مجموعه مقدار ثابت: نوع کلمه، جنسیت (فقط آلمانی، برای اسم‌ها)، و فعل کمکی حال کامل (haben/sein). این‌ها همان دانش زبان آلمانی‌اند که در مدل کدگذاری شده‌اند.

```python
    word = models.CharField(max_length=200, help_text="The German word in its basic form.")
    word_type = models.CharField(max_length=20, choices=WordType.choices, default=WordType.OTHER)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True, null=True, help_text="Only used for nouns.")
    article = models.CharField(max_length=3, blank=True, help_text="der, die, or das")
    plural = models.CharField(max_length=200, blank=True, null=True, ...)
    meaning_fa = models.CharField(max_length=500)
    meaning_en = models.CharField(max_length=500, blank=True)
    pronunciation = models.CharField(max_length=200, blank=True)
    is_separable = models.BooleanField(default=False)
    perfect_auxiliary = models.CharField(max_length=5, choices=PerfectAuxiliary.choices, blank=True, null=True)
    level = models.ForeignKey("lessons.LanguageLevel", on_delete=models.PROTECT, related_name="words")
    audio = models.FileField(upload_to="words/audio/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
```
- `gender` فقط برای اسم‌ها پر می‌شود، پس `null=True` دارد.
- `on_delete=models.PROTECT` یعنی اگر کسی بخواهد سطح زبانی را حذف کند و واژه‌ای به آن وصل باشد، **جلوگیری می‌شود.** اینجا برخلاف `accounts`، عمداً محافظه‌کارانه‌تر است چون واژه بدون سطح بی‌معناست.
- **جهت وابستگی:** `vocabulary` به `lessons.LanguageLevel` اشاره می‌کند، پس وابستگی یک‌طرفه است: vocabulary → lessons.

```python
    class Meta:
        ordering = ["word"]
        constraints = [models.UniqueConstraint(fields=["word", "word_type", "gender"], name="unique_word_type_gender")]
```
یکتا بودن سه‌گانه: `Bank` به‌عنوان اسم با `Bank` به‌عنوان فعل قاطی نمی‌شود.

```python
    TYPE_LABELS = {WordType.NOUN: "اسم", WordType.VERB: "فعل", ...}
    GENDER_LABELS = {Gender.MASCULINE: "مذکر", ...}

    @property
    def type_label(self):
        if self.word_type in self.TYPE_LABELS:
            return self.TYPE_LABELS[self.word_type]
        return self.get_word_type_display()
```
- برچسب‌های فارسی برای **صفحه‌های دانش‌آموز**؛ ولی `get_word_type_display()` انگلیسی می‌ماند چون ادمین از آن استفاده می‌کند.
- چون `property` است نه فیلد، هیچ migration لازم ندارد.
- همین یک تعریف در لیست واژه، صفحهٔ واژه، کارت‌های واژهٔ درس و پاپ‌آور lookup استفاده می‌شود.

```python
    def __str__(self):
        if self.article:
            return f"{self.article} {self.word} ({self.word_type})"
        return f"{self.word} ({self.word_type})"
```
حرف تعریف فقط وقتی وجود دارد چاپ می‌شود.

```python
class Grammar(models.Model):
    title = models.CharField(max_length=200)
    explanation = models.TextField()
    level = models.ForeignKey("lessons.LanguageLevel", on_delete=models.PROTECT, related_name="grammars")
    audio = models.FileField(upload_to="grammars/audio/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
    class Meta:
        ordering = ["level__order", "title"]
```
قاعدهٔ گرامری با متن توضیح. مثال‌ها داخل `Sentence` هستند و از طریق `LessonSentence` وصل می‌شوند، نه در همین متن.

```python
class Sentence(models.Model):
    text = models.TextField()
    translation_fa = models.TextField()
    level = models.ForeignKey("lessons.LanguageLevel", on_delete=models.PROTECT, related_name="sentences")
    audio = models.FileField(upload_to="sentences/audio/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
```
**قابل استفاده در چند جا:** در درس، به‌عنوان مثال گرامر، برای شنیدن، و به‌عنوان متن سؤال. یک جمله = یک ردیف، هرچند جاها استفاده شود.

```python
class WordProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="word_progress")
    word = models.ForeignKey("Word", on_delete=models.CASCADE, related_name="user_progress")
    attempt_count = models.PositiveIntegerField(default=0, ...)
    correct_count = models.PositiveIntegerField(default=0, ...)
    wrong_count = models.PositiveIntegerField(default=0, ...)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    last_correct_at = models.DateTimeField(null=True, blank=True)
    last_wrong_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "word"], name="unique_user_word_progress")]
```
آمار شخصی هر واژه. نگه‌داشتن **درست و غلط جداگانه** (نه فقط یک جمع) باعث می‌شود بعداً بشود پرسید «این واژه چند بار غلط زده شد؟» بدون migration.

### `vocabulary/views.py`

```python
WORDS_PER_PAGE = 24

def _published_words():
    return Word.objects.filter(is_published=True).select_related("level")

def _levels_with_counts():
    return LanguageLevel.objects.annotate(
        word_count=Count("words", filter=Q(words__is_published=True))
    ).order_by("order")
```
- `_published_words` یک قاعدهٔ واحد: هر لیست واژه فقط منتشرشده‌ها.
- `word_count` تعداد واژه‌های منتشرشدهٔ هر سطح را در **همان کوئری** حساب می‌کند (تب‌های سطح با عددشان).
- `order_by("order")` صریح است چون اضافه کردن aggregate باعث می‌شود جنگو ترتیب `Meta` را از SQL حذف کند — همین باعث شده بود تب‌ها جابه‌جا شوند (A2 قبل از A1). این نکتهٔ خوبی برای مصاحبه است.

```python
def _level_context(levels, **extra):
    levels = list(levels)
    word_total = 0
    for level in levels:
        word_total += level.word_count
    context = {"levels": levels, "word_total": word_total}
    context.update(extra)
    return context
```
تب‌های سطح به‌علاوهٔ جمع کل برای تب «همهٔ سطح‌ها».

```python
class WordListView(View):
    template_name = "vocabulary/word_list.html"
    def get(self, request, *args, **kwargs):
        words = _published_words().order_by("word", "pk")
        words = Paginator(words, WORDS_PER_PAGE).get_page(request.GET.get("page"))
        return render(request, self.template_name, _level_context(_levels_with_counts(), words=words))
```

```python
class WordLevelListView(WordListView):
    template_name = "vocabulary/word_level_list.html"
    def get(self, request, level_code, *args, **kwargs):
        level = get_object_or_404(_levels_with_counts(), level__iexact=level_code)
        words = _published_words().filter(level=level).order_by("word", "pk")
        ...
```
- **ارث‌بری:** همان ویو، فقط فیلترشده بر اساس کد سطح.
- `level__iexact` یعنی `a1` و `A1` هر دو کار می‌کنند.
- سطح از queryset آنوتیک‌شده گرفته می‌شود تا تب جاری خودش شمارشش را داشته باشد.

```python
class WordDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        word = get_object_or_404(Word.objects.select_related("level"), pk=pk)
        lesson_links = (LessonWord.objects.filter(word=word, lesson__is_published=True)
                        .select_related("lesson", "lesson__course__language_level")
                        .order_by("lesson__course__language_level__order", "lesson__order"))
```
«این واژه کجا تدریس شده» — همهٔ درس‌های منتشرشده‌ای که به آن وصل‌اند.

```python
        exercise_ids = (QuestionTarget.objects.filter(word=word, role=QuestionTarget.Role.TESTED_ITEM)
                        .values_list("question__exercise_id", flat=True).distinct())
        exercises = (Exercise.objects.filter(pk__in=list(exercise_ids), is_published=True)
                     .select_related("lesson").annotate(question_count=Count("questions"))
                     .order_by(...))
```
**چرا دو کوئری؟** اگر `Exercise` را مستقیم با `questions__targets__word` فیلتر کنی، ردیف‌ها تکثیر می‌شوند و هم تعداد و هم `annotate` غلط می‌شود. اول id تمرین‌ها را می‌گیریم، بعد تمرین‌ها را.

```python
        return render(request, self.template_name, {
            "word": word, "lesson_links": lesson_links, "exercises": exercises})
```
هیچ‌چیز ساخته نمی‌شود: بلوک دستوری فقط فیلدهایی را نشان می‌دهد که واژه واقعاً دارد.

```python
class WordLookupView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse({"error": "missing query parameter"}, status=400)
        parts = query.split()
        word_value = parts[-1]
        words = list(Word.objects.select_related("level")
                     .filter(Q(word__iexact=word_value) & Q(is_published=True))[:5])
        if not words:
            return JsonResponse({"results": []})
        results = []
        for word in words:
            results.append({"word": word.word, "article": word.article, "meaning_fa": word.meaning_fa,
                            "word_type": word.type_label, "plural": word.plural,
                            "pronunciation": word.pronunciation, "meaning_en": word.meaning_en,
                            "audio": word.audio.url if word.audio else "",
                            "url": reverse("vocabulary:word-detail", kwargs={"pk": word.pk})})
        return JsonResponse({"results": results})
```
- endpoint ای‌جکس برای پاپ‌آور «کلیک روی واژه» در صفحهٔ درس.
- `parts[-1]` یعنی اگر کاربر «der Haus» بفرستد، فقط «Haus» جست‌وجو می‌شود.
- `[:5]` سقف نتایج را می‌بندد.
- `word.audio.url if word.audio else ""` جلوی خطای فایل نداشتن را می‌گیرد.
- `word_type` برچسب **فارسی** است چون رابط کاربری فارسی است.

### `vocabulary/progress.py`

```python
def tested_word(question):
    target = (QuestionTarget.objects.filter(question=question, role=QuestionTarget.Role.TESTED_ITEM,
                                            word__isnull=False)
              .select_related("word").first())
    if target is None:
        return None
    return target.word
```
واژه‌ای که سؤال **واقعاً روی آن آزمایش می‌کند**. سؤال می‌تواند واژه، گرامر یا جمله را بسنجد، پس نبودِ واژه طبیعی است نه خطا.

```python
def record_word_progress(user, question, is_correct):
    word = tested_word(question)
    if word is None:
        return None
    now = timezone.now()
    progress, _ = WordProgress.objects.get_or_create(user=user, word=word)
    progress.attempt_count += 1
    progress.last_attempted_at = now
    if is_correct:
        progress.correct_count += 1
        progress.last_correct_at = now
    else:
        progress.wrong_count += 1
        progress.last_wrong_at = now
    progress.save()
    return progress
```
**قاعدهٔ مهم فایل:** فقط زمانی که کاربر واقعاً روی یک واژه آزمایش می‌شود شمارنده‌ها حرکت می‌کنند. یک سؤال، واژه‌هایش را از طریق `QuestionTarget` می‌گیرد و **فقط** هدف `TESTED_ITEM` همان واژهٔ آزمون‌شده است؛ اهداف `CONTEXT` فقط در سؤال ظاهر شده‌اند. پاسخ درست به سؤالی دربارهٔ `bestellen` هیچ چیزی دربارهٔ `kaufen` یا `Geld` نمی‌گوید، پس آن‌ها دست‌نخورده می‌مانند.

**چطور توضیح بدهی:**
> «`vocabulary` کتابخانهٔ محتوای مشترک است. واژه، گرامر و جمله یک بار اینجا زندگی می‌کنند و از درس و تمرین با کلید خارجی ارجاع داده می‌شوند، پس هیچ محتوایی تکرار نمی‌شود. `WordProgress` ثبت می‌کند کاربر روی هر واژه چطور عمل کرده، و آن هم فقط از طریق همان واژه‌ای که سؤال واقعاً می‌سنجد.»

---

## ۵. `exercises/` — سؤال، تمرین و تصحیح

### `exercises/models.py`

```python
class Exercise(models.Model):
    class ExerciseType(models.TextChoices):
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
        TRANSLATION = "TRANSLATION", "Translation"
        FILL_BLANK = "FILL_BLANK", "Fill in the Blank"
        LISTENING = "LISTENING", "Listening"
        READING = "READING", "Reading"
        TRUE_FALSE = "TRUE_FALSE", "True / False"
        SPEAKING = "SPEAKING", "Speaking"
        WRITING = "WRITING", "Writing"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    lesson = models.ForeignKey("lessons.Lesson", on_delete=models.CASCADE, related_name="exercises")
    title = models.CharField(max_length=200)
    instruction = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=ExerciseType.choices)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.EASY)
    order = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    class Meta:
        ordering = ["lesson_id", "order"]
        constraints = [models.UniqueConstraint(fields=["lesson", "order"], name="unique_exercise_order_per_lesson")]
```
- هشت نوع تمرین پوشش داده شده — از چندگزینه‌ای تا نوشتن.
- `lesson` به `lessons.Lesson` وصل است، پس تمرین تنها زندگی نمی‌کند.
- همان الگوی ترتیب: قید یکتا در سطح دیتابیس.

```python
    TYPE_LABELS = {ExerciseType.MULTIPLE_CHOICE: "چندگزینه‌ای", ExerciseType.TRANSLATION: "ترجمه", ...}
    DIFFICULTY_LABELS = {Difficulty.EASY: "آسان", ...}

    @property
    def type_label(self):
        if self.type in self.TYPE_LABELS:
            return self.TYPE_LABELS[self.type]
        return self.get_type_display()
```
همان الگوی `Word`: برچسب فارسی برای دانش‌آموز، `get_type_display()` انگلیسی برای ادمین، `property` بدون migration.

```python
class Question(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    audio = models.FileField(upload_to="questions/audio/", blank=True)
    image = models.FileField(upload_to="questions/images/", blank=True)
    order = models.PositiveIntegerField()
    explanation = models.TextField(blank=True)
```
سؤال + رسانهٔ اختیاری + توضیحی که بعد از پاسخ نشان داده می‌شود.

```python
class QuestionTarget(models.Model):
    class Role(models.TextChoices):
        TESTED_ITEM = "TESTED_ITEM", "Tested Item"
        CONTEXT = "CONTEXT", "Context"
        PROMPT = "PROMPT", "Prompt"

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="targets")
    word = models.ForeignKey("vocabulary.Word", ..., blank=True, null=True)
    grammar = models.ForeignKey("vocabulary.Grammar", ..., blank=True, null=True)
    sentence = models.ForeignKey("vocabulary.Sentence", ..., blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TESTED_ITEM)
```
**هوشمندانه‌ترین مدل پروژه.** یک سؤال می‌تواند دربارهٔ واژه، گرامر یا جمله باشد. سه کلید خارجی nullable دارد و `role` می‌گوید کدام‌یک «آزمون‌شده» است.

```python
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(word__isnull=False, grammar__isnull=True, sentence__isnull=True)
                           | models.Q(word__isnull=True, grammar__isnull=False, sentence__isnull=True)
                           | models.Q(word__isnull=True, grammar__isnull=True, sentence__isnull=False)),
                name="questiontarget_exactly_one_target"),
            models.UniqueConstraint(fields=["question", "role"],
                                    condition=models.Q(role="TESTED_ITEM"),
                                    name="unique_tested_item_per_question"),
        ]
```
- `CheckConstraint` اول تضمین می‌کند **دقیقاً یکی** از سه هدف پر باشد — نه صفر، نه دو.
- `UniqueConstraint` شرطی می‌گوید هر سؤال حداکثر **یک** `TESTED_ITEM` دارد.
- این‌ها در سطح دیتابیس اجرا می‌شوند، پس دادهٔ خراب حتی از ادمین یا اسکریپت هم رد نمی‌شود. **این را در مصاحبه حتماً بگو.**

```python
    def __str__(self):
        if self.word:
            target = self.word
        elif self.grammar:
            target = self.grammar
        else:
            target = self.sentence
        return f"{self.question} → {self.role}: {target}"
```
چون قید بالا تضمین می‌کند دقیقاً یکی پر است، این `if/elif/else` کامل و درست است.

```python
class Answer(models.Model):
    class MatchType(models.TextChoices):
        EXACT = "EXACT", "Exact"
        ANY_OF = "ANY_OF", "Any of"
        CONTAINS = "CONTAINS", "Contains"

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    match_type = models.CharField(max_length=10, choices=MatchType.choices, default=MatchType.EXACT)
    order = models.PositiveIntegerField()
```
گزینه‌ها. `match_type` نوع تطبیق را مشخص می‌کند؛ امروز همهٔ ردیف‌های واقعی `EXACT` هستند، ولی مدل آمادهٔ گسترش است.

```python
class ExerciseAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, ..., related_name="exercise_attempts")
    exercise = models.ForeignKey(Exercise, ..., related_name="attempts")
    question = models.ForeignKey(Question, ..., related_name="attempts")
    answer = models.ForeignKey(Answer, ..., blank=True, null=True)
    response_text = models.CharField(max_length=500, blank=True, ...)
    is_correct = models.BooleanField()
    response_time = models.FloatField(blank=True, null=True, help_text="Response time in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
```
- **هر ارسال یک ردیف جدید** — تاریخچه هیچ‌وقت بازنویسی نمی‌شود.
- `answer` برای سؤال‌هایی که با انتخاب گزینه پاسخ داده می‌شوند (چندگزینه‌ای، درست/غلط، خواندن، جای‌خالی با گزینه).
- `response_text` برای سؤال‌هایی که با تایپ جواب داده می‌شوند. **دلیلش:** آن سؤال‌ها فقط یک ردیف `Answer` دارند (همان جواب درست)، پس پاسخ غلط تایپ‌شده ردیفی ندارد که به آن اشاره کند و متن همین‌جا نگه داشته می‌شود.
- `created_at` با `auto_now_add` زمان ثبت را می‌گذارد.

### `exercises/grading.py`

**چرا هست؟** قبلاً صفحهٔ تمرین در مرورگر تصحیح می‌کرد: گزینهٔ درست یک `data-correct` داشت و جواب درست در یک بلوک مخفی بود. هر کسی سورس را می‌دید جواب‌ها را می‌خواند. الان تصحیح اینجاست، از روی ردیف‌های واقعی `Answer`.

```python
TRAILING_PUNCTUATION = re.compile(r"[.!?,;:،؛«»\"']+$")
MAX_RESPONSE_LENGTH = 500
```
- الگوی نشانه‌گذاری انتهایی که دانش‌آموز ممکن است اضافه کند.
- طول فیلد `response_text` در دیتابیس؛ پاسخ تایپ‌شده **بریده** می‌شود، رد نمی‌شود.

```python
def normalize(text):
    collapsed = " ".join(str(text).split())
    without_punctuation = TRAILING_PUNCTUATION.sub("", collapsed)
    return without_punctuation.lower()
```
یک شکل استاندارد برای مقایسه:
- `split()` روی هر فاصله/تب/خط جدید می‌شکند و `" ".join` دوباره با یک فاصله می‌چسباند → چند فاصله = یک فاصله.
- نشانه‌گذاری انتهایی حذف می‌شود، پس `gute Nacht!` با `gute Nacht` می‌خواند.
- حروف کوچک می‌شوند.

```python
def grade(question, answer_id, response_text):
    answers = list(question.answers.all())
    correct_answers = []
    for answer in answers:
        if answer.is_correct:
            correct_answers.append(answer)
    if not correct_answers:
        return None
```
اگر هیچ جواب درستی تعریف نشده باشد، حکمی **ساخته نمی‌شود** — `None` برمی‌گردد. این اصل مهم فایل است: هیچ‌وقت حکم الکی نساز.

```python
    chosen = None
    if answer_id is not None:
        for answer in answers:
            if answer.pk == answer_id:
                chosen = answer
                break
        if chosen is None:
            return None
        is_correct = chosen.is_correct
        typed = ""
```
اگر کاربر گزینه انتخاب کرده: حکم همان `is_correct` ردیف انتخابی است. اگر `answer_id` گزینهٔ همین سؤال نباشد، `None` (دادهٔ نامعتبر).

```python
    else:
        typed = str(response_text or "").strip()[:MAX_RESPONSE_LENGTH]
        is_correct = False
        for answer in correct_answers:
            if normalize(answer.text) == normalize(typed):
                is_correct = True
                break
```
اگر تایپ کرده: آنچه کاربر **واقعاً نوشته** ذخیره می‌شود و `normalize` فقط برای مقایسه است. تطبیق باید **کل پاسخ** باشد، نه بخشی از آن.

```python
    return {"is_correct": is_correct, "answer": chosen, "response_text": typed,
            "correct_answer_id": correct_answers[0].pk,
            "expected": [answer.text for answer in correct_answers]}
```
خروجی: حکم، ردیفی که تلاش با آن ذخیره می‌شود، گزینه‌ای که صفحه باید علامت بزند، و جواب‌هایی که باید نشان داده شوند.

### `exercises/runner.py`

**چرا هست؟** صفحهٔ تمرین سؤال‌ها را یکی‌یکی نشان می‌دهد، پس باید بداند هر سؤال **چطور** پاسخ داده می‌شود. این تصمیم اینجاست، از روی ردیف‌های واقعی، نه پخش‌شده بین تمپلیت و JS.

```python
CHOICE = "choice"
TEXT = "text"
UNCHECKED = "none"
```
سه حالت. تصمیم فقط بر اساس تعداد ردیف‌های `Answer`:
- `choice` — بیش از یک ردیف: یکی از گزینه‌های رندرشده انتخاب می‌شود (همهٔ چندگزینه‌ای/درست‌غلط/خواندن، و جای‌خالی‌هایی که با گزینه ساخته شده‌اند).
- `text` — دقیقاً یک ردیف: تایپ می‌شود (همهٔ ترجمه‌ها و جای‌خالی‌های بدون گزینه).
- `none` — هیچ ردیفی: چیزی برای تصحیح نیست. سؤال نشان داده می‌شود ولی از امتیاز بیرون می‌ماند.

```python
def _passage(question):
    for target in question.targets.all():
        if target.sentence_id and target.sentence:
            return target.sentence.text
    return ""
```
متن آلمانی که سؤال رویش ساخته شده. فقط سؤال‌های READING آن را دارند: هدف `CONTEXT` آن‌ها به یک `Sentence` واقعی اشاره می‌کند.

```python
def build_runner(exercise):
    questions = []
    for position, question in enumerate(exercise.questions.all(), start=1):
        answers = list(question.answers.all())
        correct = [answer for answer in answers if answer.is_correct]
        if not answers or not correct:
            kind = UNCHECKED
        elif len(answers) > 1:
            kind = CHOICE
        else:
            kind = TEXT
```
`enumerate(..., start=1)` یعنی شمارهٔ نمایشی از ۱ شروع شود. شرط‌ها دقیقاً همان سه حالت را می‌سازند.

```python
        questions.append({
            "id": question.pk,
            "number": position,          # شمارهٔ نمایشی، نه Question.order
            "kind": kind,
            "prompt": question.prompt,
            "passage": _passage(question),
            "options": answers if kind == CHOICE else [],
            "audio": question.audio,
            "image": question.image,
        })
    return questions
```
- `number` شمارهٔ **نمایشی** است چون `Question.order` در کل درس شمرده می‌شود (تمرین درست/غلط یک درس واقعاً از سؤال ۱۲ شروع می‌شود) و نمی‌شود آن را «سؤال ۱ از ۲» خواند.
- `options` فقط برای حالت choice پر می‌شود.

```python
def scoreable_count(questions):
    total = 0
    for question in questions:
        if question["kind"] != UNCHECKED:
            total += 1
    return total
```
تعداد سؤال‌هایی که واقعاً قابل امتیازدهی هستند.

### `exercises/views.py`

```python
MAX_RESPONSE_TIME = 3600

def _response_time(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds < 0 or seconds > MAX_RESPONSE_TIME:
        return None
    return round(seconds, 1)
```
زمان پاسخ فقط **آنالیتیکس** است، نه کنترل امنیتی. پس مقدار غیرقابل‌استفاده حذف می‌شود اما ارسال رد نمی‌شود. یک ساعت روی یک سؤال یعنی تب باز مانده، نه اینکه کاربر فکر می‌کرده.

```python
class ExerciseListView(View):
    def get(self, request, *args, **kwargs):
        exercises = (Exercise.objects.filter(is_published=True, lesson__is_published=True,
                                             lesson__course__is_published=True)
                     .select_related("lesson", "lesson__course")
                     .annotate(question_count=Count("questions"))
                     .order_by("lesson__course__language_level__order", "lesson__order", "order"))
        lesson_pk = request.GET.get("lesson")
        if lesson_pk:
            lesson = get_object_or_404(Lesson, pk=lesson_pk, is_published=True)
            exercises = exercises.filter(lesson=lesson)
        exercises = list(exercises)
        question_total = 0
        lesson_ids = set()
        for exercise in exercises:
            question_total += exercise.question_count
            lesson_ids.add(exercise.lesson_id)
```
- همان قاعدهٔ «فقط منتشرشده» در سه سطح: تمرین، درس، دوره.
- `?lesson=` صفحه را به یک درس محدود می‌کند.
- `list(...)` اجباری است چون تمپلیت ردیف‌ها را می‌شمارد و `{% regroup %}` یک پاس نیاز دارد.
- `lesson_ids` یک **مجموعه** است، پس تعداد درس‌های یکتا را می‌دهد نه تعداد تمرین‌ها.

```python
class ExerciseDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise.objects.select_related("lesson")
            .prefetch_related("questions__answers", "questions__targets__sentence", "questions__targets__word"),
            pk=pk)
        questions = build_runner(exercise)
        siblings = list(Exercise.objects.filter(lesson=exercise.lesson, is_published=True).order_by("order"))
        next_exercise = None
        for sibling in siblings:
            if sibling.order > exercise.order:
                next_exercise = sibling
                break
        ...
```
- `prefetch_related` سؤال‌ها، گزینه‌ها و هدف‌ها را در چند کوئری می‌آورد (به‌جای صدها کوئری).
- **جواب‌های درست عمداً رندر نمی‌شوند.** کاربر ارسال می‌کند و حکم از سرور برمی‌گردد.
- حلقهٔ `next_exercise` اولین تمرین با ترتیب بزرگ‌تر را پیدا می‌کند.

```python
class ExerciseSubmitView(View):
    def post(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=pk)
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        question = exercise.questions.filter(pk=payload.get("question")).first()
        if question is None:
            return JsonResponse({"error": "unknown question"}, status=400)

        verdict = grade(question, payload.get("answer"), payload.get("response_text"))
        if verdict is None:
            return JsonResponse({"error": "question cannot be graded"}, status=400)
```
- سؤال از میان سؤال‌های **همین تمرین** جست‌وجو می‌شود، پس نمی‌شود سؤال تمرین دیگری را فرستاد.
- حکم همیشه از سرور می‌آید.

```python
        recorded = False
        if request.user.is_authenticated:
            ExerciseAttempt.objects.create(
                user=request.user, exercise=exercise, question=question,
                answer=verdict["answer"], response_text=verdict["response_text"],
                is_correct=verdict["is_correct"],
                response_time=_response_time(payload.get("response_time")))
            record_word_progress(request.user, question, verdict["is_correct"])
            recorded = True

        return JsonResponse({"correct": verdict["is_correct"],
                             "correct_answer": verdict["correct_answer_id"],
                             "expected": verdict["expected"],
                             "explanation": question.explanation,
                             "recorded": recorded})
```
- یک ردیف جدید هر بار، **عمداً**: پاسخ‌های کاربر تاریخچه‌اند نه یک شمارنده، تا بعداً بتوان دید کجا را غلط زده.
- مهمان هم تصحیح می‌شود ولی ذخیره نمی‌شود، چون `ExerciseAttempt` به کاربر نیاز دارد.
- `record_word_progress` اینجاست که شمارندهٔ واژه را حرکت می‌دهد.

### `exercises/admin.py`

```python
@admin.register(ExerciseAttempt)
class ExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ("__str__", "user", "question", "answer", "response_text", "is_correct", "response_time", "created_at")
    list_filter = ("is_correct", "question__exercise__type")
    search_fields = ("user__username", "question__prompt", "answer__text", "response_text")
    list_select_related = ("user", "question", "answer")
    list_per_page = 50
```
- `list_select_related` جلوی N+1 در صفحهٔ لیست ادمین را می‌گیرد.
- `list_filter` و `search_fields` صفحهٔ ادمین را قابل استفاده می‌کنند.

```python
class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionTargetInline, AnswerInline]
    ...
    fieldsets = (
        (None, {"fields": ("exercise", "order")}),
        ("سؤال", {"fields": ("prompt", "audio", "image"), "classes": ("wide",)}),
        ("توضیح (اختیاری)", {"fields": ("explanation",), "classes": ("collapse",)}),
    )
```
- `inlines` یعنی هدف‌ها و گزینه‌ها **داخل همان فرم سؤال** ویرایش می‌شوند.
- `fieldsets` فرم ادمین را گروه‌بندی می‌کند و برچسب‌ها فارسی‌اند.
- `autocomplete_fields` در فرم‌های بزرگ جلوی منوی کشویی غول‌آسا را می‌گیرد.

**چطور توضیح بدهی:**
> «`exercises` مالک تمرین است. تصحیح در ماژول خودش به‌صورت توابع خالص است تا تست‌شدنی باشد، و هر ارسال یک ردیف `ExerciseAttempt` جدید می‌سازد تا تاریخچه از دست نرود. `QuestionTarget` سؤال را به همان یک آیتم واژگانی که می‌سنجد وصل می‌کند و دیتابیس با `CheckConstraint` تضمین می‌کند دقیقاً یکی از واژه/گرامر/جمله پر باشد.»

---

## ۶. `tests/` — تور ایمنی سراسری پروژه

**نامش گمراه‌کننده است:** این اپ **تست جنگو** است، نه تمرین‌های دانش‌آموز. مدل و ویو ندارد (`urls.py` خالی و `views.py` اسکلت است).
```python
MULTILINE_INLINE_COMMENT = re.compile(r"\{#[^#{}]*\n[^#]*?#\}")
```
الگویی که کامنت اینلاین **چندخطی** را پیدا می‌کند. `{# #}` در جنگو فقط **تک‌خطی** است؛ نسخهٔ چندخطی کامنت نیست و به‌عنوان متن واقعی به مرورگر می‌رود.

```python
class TemplateCommentTests(SimpleTestCase):
    def test_no_template_contains_a_multiline_inline_comment(self):
        offenders = []
        for path in template_paths():
            text = path.read_text(encoding="utf-8")
            for match in MULTILINE_INLINE_COMMENT.finditer(text):
                line = text[: match.start()].count("\n") + 1
                first = match.group(0).splitlines()[0][:70]
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{line}  {first}")

        self.assertEqual(offenders, [], "These multi-line {# #} comments ...")
```
- `template_paths()` همهٔ تمپلیت‌های پروژه و اپ‌ها را برمی‌گرداند.
- برای هر تطبیق، شمارهٔ خط و متن آن حساب می‌شود.
- `assertEqual(offenders, [])` یعنی اگر چیزی پیدا شود، تست با **همان لیست** می‌شکند و مسیر و شمارهٔ خط را نشان می‌دهد.
- **چرا این تست هست؟** این باگ یک بار ۱۱۰ بار در یک صفحهٔ درس ظاهر شده بود و یکی از بلوک‌ها `<audio>` داشت، پس مرورگر یک المان مدیا غلط ساخت و دکمه‌های پخش واقعی از کار افتادند. بازگشتش آسان است، پس تست می‌شود.

```python
class ErrorPageTests(SimpleTestCase):
    def test_not_found_page_renders(self):
        html = render_to_string("404.html")
        self.assertIn("error-page", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)

    def test_server_error_page_renders_without_a_context(self):
        html = render_to_string("500.html")
        ...
```
- این دو صفحه فقط وقتی `DEBUG=False` باشد دیده می‌شوند، پس سرور توسعه هیچ‌وقت نشانشان نمی‌دهد — یعنی خرابشان را کسی متوجه نمی‌شود.
- صفحهٔ ۵۰۰ را جنگو **کاملاً بدون context** رندر می‌کند، پس تست هم همان‌طور (بدون context) انجام می‌شود.
- `assertNotIn("{{")` و `assertNotIn("{%")` بررسی می‌کند تمپلیت متغیر رندر‌نشده جا نگذاشته باشد.

**چطور توضیح بدهی:**
> «اپ `tests` جای بررسی‌هایی است که به کل پروژه تعلق دارند، نه به یک اپ — بهداشت تمپلیت‌ها و صفحات خطا. هر اپ ویژگی هم تست‌های خودش را دارد.»

---

## ۷. ادمین — کلاس‌های مهم و چرا

**چرا هست؟** ادمین، پشت‌صحنهٔ مدیریت محتواست. همهٔ محتوای A1 بدون نوشتن فرم یا ویو از همین‌جا مدیریت می‌شود.

### الگوی مشترک همهٔ `ModelAdmin` ها

```python
@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("__str__", "word_type", "gender", "meaning_fa", ...)
    list_filter = ("word_type", "gender", "is_published", "level__level")
    search_fields = ("word", "meaning_fa", ...)
    list_select_related = ("level",)
    list_per_page = 40
```

- `list_display` ستون‌های صفحهٔ لیست.
- `list_filter` فیلترهای کنار صفحه — با مسیر روابط مثل `level__level` می‌شود روی سطح هم فیلتر کرد.
- `search_fields` کادر جست‌وجو — جست‌وجوی SQL روی این ستون‌ها.
- `list_select_related` **نکتهٔ مهم برای مصاحبه:** در صفحهٔ لیست ادمین، هر ردیف برای کشیدن `word.level` یک کوئری می‌زند. با این خط، همهٔ ردیف‌ها با یک کوئری می‌آیند — همان مشکل N+1 که در ویوها هم دیدیم.

### Inline — ویرایش فرزند داخل فرم پدر

```python
class LessonWordInline(admin.TabularInline):
    model = LessonWord
    extra = 1
    fields = ("word", "role", "order")
    autocomplete_fields = ("word",)
```

داخل صفحهٔ هر `Lesson`، چهار inline هست: محتوا، واژه، گرامر، جمله. یعنی یک درس با همهٔ اجزایش در یک صفحه ویرایش می‌شود، بدون رفت‌وآمد بین صفحات.

### `autocomplete_fields` — چرا

```python
autocomplete_fields = ("lesson", "word")
```
وقتی ده‌ها هزار واژه داری، dropdown ساده مرورگر را می‌کُشد. autocomplete جست‌وجوی سروری می‌دهد. برای این کار باید `search_fields` روی ادمین آن مدل تعریف شده باشد — به همین دلیل `WordAdmin` و بقیه `search_fields` دارند.

### `fieldsets` — گروه‌بندی فرم

```python
fieldsets = (
    (None, {"fields": (("word", "word_type"), ...)}),
    ("فایل صوتی", {"fields": ("audio",), "classes": ("collapse",)}),
)
```

برچسب‌ها فارسی‌اند چون کاربر ادمین فارسی‌زبان است. `collapse` یعنی بخش صوتی تا کلیک بسته بماند. تاپل درون تاپل مثل `("word", "word_type")` یعنی آن دو فیلد در یک سطر.

### `UserAdmin` و unregister/register

```python
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
```

ادمین پیش‌فرض جنگو برای `User` را بردار و نسخهٔ خودت را بگذار که inline پروفایل و ستون `date_joined` دارد. این الگوی استاندارد سفارشی‌سازی ادمین کاربر است.

### ادمین‌های read-mostly

`ExerciseAttemptAdmin` و `LessonProgressAdmin` و `WordProgressAdmin` «read-mostly» ثبت شده‌اند — ردیف‌هایشان را صفحهٔ کاربر می‌نویسد و ادمین فقط می‌بیند. جالب اینکه فرمی برای ویرایش تعریف نشده؛ فقط list/list_filter/search دارند.

### دو helper کوچک در ادمین واژه و جمله

```python
@admin.display(description="انگلیسی")
def meanin_en_short(self, obj):
    return obj.meaning_en[:40] if obj.meaning_en else ""
```

ستون محاسبه‌شده: اولین ۴۰ حرف معنی انگلیسی. با `@admin.display` برچسب فارسی هم می‌گیرد. همین الگو برای `text_short` در `SentenceAdmin` با ۶۰ حرف.

جملهٔ آماده: «ادمین را کامل کردم — inline ها، autocomplete ها، فیلترها — تا مدیریت محتوای فارسی بدون کدنویسی ممکن باشد؛ و `list_select_related` را همه‌جا گذاشتم تا صفحه‌های لیست N+1 نگیرند.»

---

## ۸. فایل‌های کوچک — یک‌جا

این‌ها کوتاه‌اند ولی در مصاحبه ممکن است درباره‌شان سؤال شود. هر یک را با یک خط توضیح بده.

### `manage.py`

```python
def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django...") from exc
    execute_from_command_line(sys.argv)
```
قبل از هر چیز می‌گوید «تنظیمات از `config.settings` بیا»، بعد دستور را به جنگو می‌دهد. پیام ImportError هم یادآوری venv است. همین.

### `config/wsgi.py` و `config/asgi.py`

دو ورودی برای سرور پروداکشن:
- **WSGI** مدل قدیمی: یک درخواست → یک پاسخ. `application = get_wsgi_application()` همان نقطهٔ ورود است که gunicorn/uwsgi صدا می‌زند.
- **ASGI** مدل جدید ناهمگام: همان نقطهٔ ورود برای daphne/uvicorn. این پروژه از ASGI استفاده نمی‌کند ولی فایلش استاندارد است.

در مصاحبه اگر پرسیدند «پروژه‌ات چطور deploy می‌شود؟»: «با WSGI — gunicorn پشت nginx؛ فایل asgi هم هست ولی به کار نمی‌آید چون websocket ندارم.»

### `apps.py` در هر اپ — مهم‌ترینش `accounts`

```python
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from . import signals
```

`ready()` وقتی اپ لود شد اجرا می‌شود. اینجا سیگنال import می‌شود تا receiver ثبت شود. **بدون این خط، سیگنال هرگز فعال نمی‌شد و پروفایل ساخته نمی‌شد.** اپ‌های دیگر همین کلاس را بدون `ready()` دارند.

### فایل‌های خالی `forms.py` / `models.py` / `views.py` در `tests`

اپ `tests` مدل و فرم و ویو ندارد؛ این فایل‌ها فقط ساختار استاندارد اپ جنگو را کامل می‌کنند. حذفشان ضرورتی ندارد.

### `requirements.txt`

```
Django==6.1.1
edge-tts==7.2.8
```
فقط دو وابستگی. `edge-tts` برای تولید صوت در دستورهای مدیریتی است. هیچ DRF، هیچ celery، هیچ چیزی که لازمش نداری.

### مهاجرت‌ها — الگوی آن‌ها

مثلاً `exercises/0003`:

```python
class Migration(migrations.Migration):
    dependencies = [('exercises', '0002_exerciseattempt')]
    operations = [
        migrations.AddField(...),
        ...
    ]
```
دو کلید در فایل مهاجرت: `dependencies` (ترتیب اجرا) و `operations` (چه اتفاقی بیفتد). از تاریخچه مهاجرت‌ها می‌شود پروژه را از صفر بازسازی کرد.

### دیتای درس (`lessons/data/`)

چهار فایل پایتون که **محتوا** هستند، نه کد منطقی:
- `a1_lessons_a.py` / `a1_lessons_b.py` — ۲۴ درس به‌صورت لیست دیکشنری (`LESSONS.append({...})`)، هر کدام با `order`، `title`، `contents` (تاپل‌های نوع/عنوان/متن)، `words_new`، `words_review`، `grammar`، `sentences`.
- `a1_grammar.py` / `a1_grammar_b.py` — دیکشنری `GRAMMAR` از عنوان به متن توضیح.

متن‌ها برای یادگیرندهٔ فارسی‌زبان نوشته شده‌اند و هر بخش یک gloss انگلیسی با پیشوند `English:` دارد که `validate_a1_content` چک می‌کند. جملهٔ آماده: «محتوای آموزشی را در ماژول پایتون گذاشتم، نه در دیتابیس، تا قابل بازبینی با git باشد و seed تکراری‌پذیر.»

---

## ۹. قاعده‌های سبک کدنویسی (قانون §7)

این‌ها قواعد آگاهانه‌ای هستند که برای این پروژه انتخاب شده‌ای تا بتوانی هر خط را در مصاحبه توضیح بدهی. اگر پرسیدند «چرا این را ساده نوشتی؟»، همین‌ها را بگو.

### کدام قواعد؟

- **بدون type hints و بدون `getattr`/`setattr`.** هر چیز پنهان، حذف شده تا کد خوانا بماند.
- **بدون `.get(key, default)` وقتی جای آن `if` است.** اگر کلید ممکن است نباشد، اول `if key in dict:` و بعد دسترسی مستقیم:

```python
if key in LABELS:
    return LABELS[key]
return fallback
```
- **بدون `or`-chain، ternary، `next((...), None)`، `any(...)`، `sum(1 for ...)`.** همه با حلقه و `if` معمولی:

```python
# به جای: total = sum(1 for q in questions if q["kind"] != UNCHECKED)
total = 0
for question in questions:
    if question["kind"] != UNCHECKED:
        total += 1
```
- **import ها همه بالای فایل.** هیچ import داخل تابع نیست.
- **چند خط تکراری بهتر از یک انتزاع هوشمند.** اگر دو جا یک حلقه مشابه داریم، حلقه دوم را نوشتیم؛ تابع تکی‌use نساختیم.
- **docstring های ماژول حفظ شده‌اند** چون می‌گویند فایل چیست.
- فقط یک lambda مجاز است: `lessons.sort(key=lambda item: item["order"])` در seed چون کلید sort واقعی است، نه چیز دیگر.

### قاعدهٔ ویژهٔ `grade()` — چرا حلقه به جای `next()`؟

```python
chosen = None
for answer in answers:
    if answer.pk == answer_id:
        chosen = answer
        break
if chosen is None:
    return None
```

همان کار `next((a for a in answers if a.pk == answer_id), None)` را می‌کند، ولی خط‌به‌خط خواندنی است. اگر مصاحبه‌گر بگوید «چرا next()؟»، جواب این است: «برای خوانایی انتخاب کردم؛ هدف این پروژه این بود که هر خط را بتوانم توضیح بدهم.»

### نتیجه

- `accounts` به‌عنوان مرجع سبک شناخته می‌شود؛ بقیهٔ اپ‌ها با همان قواعد بازنویسی شدند.
- هیچ رفتاری عوض نشده؛ ۱۷۷ تست قبل و بعد یک نتیجه دادند.
- JS/CSS/HTML دست نخورد؛ فقط پایتون ساده شد.

---

## ۱۰. دستورهای مدیریتی — یکی‌یکی

**چرا هست؟** محتوای A1 (دوره، واژه، گرامر، جمله، صوت) با این دستورها وارد دیتابیس می‌شود، نه دستی در ادمین. هر دستور یک‌کاری را می‌کند و قابل بازخوانی است.

### `lessons/management/commands/seed_a1_course.py`

دادهٔ درس‌ها را از `lessons/data/` می‌خواند و دوره را می‌سازد. چهار حالت دارد:

```
python manage.py seed_a1_course             # ساختن هر چه نیست
python manage.py seed_a1_course --check     # فقط اعتبارسنجی، بدون نوشتن
python manage.py seed_a1_course --dry-run   # همه چیز را در transaction می‌نویسد و rollback می‌کند
python manage.py seed_a1_course --update    # متن ردیف‌های موجود را refresh می‌کند
```

نکته‌های مهم برای توضیح:
- **هیچ چیز را حذف نمی‌کند.** ردیف موجود با `get_or_create` پیدا می‌شود و بدون `--update` دست‌نخورده می‌ماند.
- `--dry-run` از `transaction.set_rollback(True)` استفاده می‌کند: همه چیز واقعاً در دیتابیس اجرا می‌شود و بعد برمی‌گردد. این یعنی «dry run واقعی»، نه شبیه‌سازی ناقص.
- `validate()` قبل از نوشتن، کل داده را چک می‌کند: ترتیب درس‌ها پیوسته باشد، واژه تکراری NEW/REVIEW نباشد، عنوان گرامر در `a1_grammar` وجود داشته باشد، نقش جمله معتبر باشد. روی اولین خطا `sys.exit(1)` و هیچ چیز نوشته نمی‌شود.
- واژه‌ها فقط **link** می‌شوند (`LessonWord`)، فیلدهایشان هرگز بازنویسی نمی‌شود.

### `lessons/management/commands/validate_a1_content.py`

برعکس seed: به جای چک دادهٔ ورودی، دیتابیس واقعی را چک می‌کند. فقط می‌خواند و اگر مشکلی باشد exit code 1 می‌دهد. همان قواعد تست‌های `lessons` را روی دیتای واقعی اجرا می‌کند، برای وقتی که کاربر دیتابیس اجازه ساخت test database ندارد.

### `lessons/management/commands/export_a1_content.py`

محتوای دوره را به ۶ فایل CSV می‌ریزد برای بازبینی ترجمه. نکتهٔ خوب برای مصاحبه:

```python
encoding="utf-8-sig"
```
یعنی UTF-8 با BOM — تا Excel در ویندوز فارسی را درست نشان دهد. یک تصمیم ریز اما واقعی.

### `vocabulary/management/commands/import_a1_words.py`

واژه‌ها را از JSON می‌خواند و برای هر واژه فایل صوتی می‌سازد:
- `update_or_create` یعنی واژه موجود refresh می‌شود، تکراری ساخته نمی‌شود.
- برای هر متن متمایز یک فایل صوتی می‌سازد (نه برای هر ردیف)؛ اسم فایل از slug + hash می‌آید تا یکتا باشد.
- با `edge-tts` صوت می‌سازد، سه بار retry با backoff، و اگر خالی بود فایل را پاک می‌کند.

### سه دستور صوتی دیگر (`generate_*_audio`)

هر سه یک الگو دارند: ردیف‌های منتشرشدهٔ بدون صوت را پیدا می‌کنند، با `edge-tts` MP3 می‌سازند، با `ffmpeg` درستی فایل را چک می‌کنند، و بعد با `update()` صوت را به ردیف می‌بندند. سه نکته:
- اول فایل temp ساخته می‌شود، بعد صوت در آن، بعد چک با ffmpeg، بعد bind. اگر وسطش شکست بخورد فایل پاک می‌شود.
- `publish()` با `update()` و شرط «هنوز صوت ندارد» کار می‌کند، پس دو worker همزمان نمی‌توانند دو بار بنویسند.
- threading فقط برای کار شبکه/فایل است؛ نوشتن دیتابیس روی thread اصلی می‌ماند.

**نکتهٔ مهم:** دو تا از این دستورها الان کار نمی‌کنند — بخش ۱۳ را ببین.

### مهاجرت‌ها (`migrations/`)

هیچ وقت دستی editشان نکن. هر فایل یک تغییر schema است. مثلاً `lessons/0005_lessonprogress.py` ساخت جدول `LessonProgress` با `UniqueConstraint('user', 'lesson')` را ثبت می‌کند. `accounts/0001_initial.py` هم `UserProfile` با `on_delete=SET_NULL` روی سطح زبانی.

جملهٔ آماده: «محتوا با دستورهای مدیریتی seed می‌شود که قبل از نوشتن اعتبارسنجی می‌کنند، dry-run واقعی با transaction دارند، و هیچ چیز را حذف نمی‌کنند.»

---

## ۱۱. تست‌ها — خط به خط کلاس‌های مهم

**چرا هست؟** جواب این سؤال در مصاحبه نصف امتیاز است: تست‌ها **رفتار کاربر** را می‌سنجند، نه خطوط اجرا شده. کلاس‌های viewport ،cursor و page object چیزهای دکوری را نمی‌سنجند؛ می‌سنجند که «صفحه چه وعده‌ای به کاربر می‌دهد».

### الگوی مشترک همهٔ فایل‌های تست

```python
@classmethod
def setUpTestData(cls):
    ...
```
`setUpTestData` یک بار برای کل کلاس اجرا می‌شود، نه برای هر تست. این یعنی سریع‌تر است. با `setUp` مقایسه کن که قبل از هر تست اجرا می‌شود و برای چیزی است که هر تست باید از نو بسازد.

```python
class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.credentials = dict(username="test", password="Un\u0627s-1-Pass")
        cls.user = User.objects.create_user(**cls.credentials)
```
و بعد داخل هر تست:

```python
self.client.login(**self.credentials)
response = self.client.get("/accounts/profile/")
self.assertEqual(response.status_code, 200)
```
پس «مهمان ۳۰۲ به لاگین می‌گیرد، وارد‌شده ۲۰۰».

الگوی رایج دیگر، `subTest`:

```python
for url in (...):
    with self.subTest(url=url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
```
با `subTest` اگر یکی از URLها شکست بخورد، بقیه هم اجرا می‌شوند و همهٔ شکست‌ها را یک‌جا می‌بینی.

### `accounts/tests.py` — چهار کلاس

- **SignUpTests**: صفحه رندر می‌شود، ثبت‌نام کاربر + پروفایل می‌سازد و وارد می‌کند، رمزهای ناهماهنگ رد می‌شوند، کاربر وارد‌شده از صفحهٔ ثبت‌نام به پروفایل می‌رود.
- **LoginTests**: مهم‌ترین، تست‌های `?next=`:

```python
def test_login_ignores_a_next_parameter_that_leaves_this_site(self):
    response = self.client.post(
        reverse("accounts:login"),
        {"username": "test", "password": "...", "next": "https://evil.example"},
    )
    self.assertRedirects(response, reverse("accounts:profile"))
```
یعنی: «تلاش برای بردن کاربر تازه‌وارد به سایت خارجی، به‌جایش او را به پروفایل می‌فرستد.» این همان تضمین `url_has_allowed_host_and_scheme` است.

- **LogoutTests**: `assertEqual(response.status_code, 405)` — خروج فقط با POST، نه لینک GET.
- **ProfileTests**: صفحه ورود می‌خواهد، جزئیات حساب را نشان می‌دهد، و برای حساب‌های قدیمی که سیگنال را ندیده‌اند، پروفایل را همان‌جا می‌سازد.

### `exercises/tests.py` — سه خوشه

- **ExerciseIntegrityTest**: درستیِ داده — «هر سؤال دقیقاً یک جواب درست دارد»، «هدف‌ها به هم exclusive‌اند»، «ترتیب تمرین‌ها در هر درس یکتاست».
- **ExerciseRunnerTests**: صفحهٔ تمرین — گزینه‌ها رندر می‌شوند ولی «جواب درست در صفحه نیست» (`assertNotContains(response, "data-correct")`)، سؤال بدون جواب `data-kind="none"` می‌گیرد و از امتیاز بیرون می‌ماند، مهمان می‌بیند که چیزی ذخیره نمی‌شود.
- **ExerciseSubmissionTests**: رفتار endpoint — مهمان حکم می‌گیرد ولی ردیفی ساخته نمی‌شود؛ کاربر وارد‌شده یک `ExerciseAttempt` می‌سازد؛ ارسال دوباره = دو ردیف (تاریخچه بازنویسی نمی‌شود)؛ سؤال از تمرین دیگر ۴۰۰ می‌گیرد؛ متن تایپ‌شده دقیقاً همان‌طور که تایپ شده ذخیره می‌شود.

### `vocabulary/tests.py` — سه کلاس

- **WordListPageTests**: لیست واژه ردیفی است نه کارت‌گرید؛ تب‌های سطح شمارش واقعی دارند؛ واژهٔ منتشرنشده لیست نمی‌شود؛ سطح با واژهٔ صفر state خالی می‌دهد.
- **WordDetailPageTests**: عنوان صفحه خودِ واژهٔ آلمانی است؛ ردیف‌های دستوری فقط برای فیلدهایی که واژه واقعاً دارد می‌آیند (`assertContains(response, "Genus")` برای اسم، `assertNotContains` برای فعل)؛ لینک به درس‌ها و تمرین‌های واقعی.
- **WordLabelTests**: برچسب فارسی نوع و جنسیت، و اینکه `lookup` برچسب فارسی برمی‌گرداند.

### `lessons/tests.py` — هشت کلاس

- **پنج کلاس داده‌ای** (CourseStructure، LessonWordLink، GrammarAndSentence، WordData، SeedCommand) همان قواعد اعتبارسنجی را روی دیتابیس تست‌شده اجرا می‌کنند: ترتیب پیوسته، REVIEW بعد از NEW، اسم‌ها با حرف بزرگ، فعل‌ها با haben/sein، و اینکه re-seed تکراری نمی‌سازد.
- **DashboardTests، LearningPathTests، LessonJourneyTests، LessonProgressTests، LessonProgressEndpointTests**: رفتار صفحات — داشبورد برای مهمان و کاربر، مسیر صفحه‌بندی‌نشده، سفر درس بدون گام خالی، و endpoint پیشرفت با تمام قواعد (گام ناشناس ۴۰۰، GET نویسنده نیست، درس منتشرنشده قابل ثبت نیست، resume-step).

جملهٔ آماده: «۱۷۷ تست سبز، توزیع‌شده روی درستی داده، رفتار صفحه، و endpointهای JSON؛ و صفحه بدون JS هم تست می‌شود.»

---

## ۱۲. جاوااسکریپت — دو قاعدهٔ کلیدی

گفتی فرانت را با AI ساخته‌ای و فقط بک‌اند را می‌خواهی بفهمی و توضیح بدهی. پس لازم نیست خط‌به‌خط JS را حفظ کنی؛ فقط این دو قاعده را بلد باش، چون **مستقیماً به بک‌اند‌ی که نوشتی وصل‌اند**:

### قاعدهٔ ۱: سرور همه‌چیز را رندر می‌کند؛ JS فقط بهبود است

در `lessons/static/lessons/js/lesson_steps.js` نوشته شده که همهٔ گام‌ها از قبل کامل در DOM هستند و اسکریپت فقط نمایش یکی در میان را اضافه می‌کند. اگر JS اجرا نشود، کلاس `js` روی `<html>` نمی‌آید، CSS هیچ گامی را مخفی نمی‌کند، و درس به‌صورت یک سند پیوسته خواندنی می‌ماند.

همین قاعده در `static/js/path.js` و `static/js/dashboard.js` هم هست: سرور کل مسیر را با عنوان و مدت و لینک واقعی رندر کرده، و اسکریپت فقط چیزی را رنگ می‌زند که **فقط مرورگر می‌داند** — کدام گام انجام شده و کدام بعدی است.

جملهٔ آماده: «صفحه بدون جاوااسکریپت کامل و قابل استفاده است؛ JS فقط وضعیت شخصی را اضافه می‌کند. این را با تست هم تضمین کرده‌ام.»

### قاعدهٔ ۲: حکم از سرور می‌آید، نه از مرورگر

`exercises/static/exercises/js/exercise_runner.js` خودش تصمیم نمی‌گیرد جواب درست چیست. هر ارسال به `exercises:exercise-submit` می‌رود، سرور با `grade()` حکم می‌دهد، و JS فقط همان پاسخ را نشان می‌دهد. جواب‌های درست اصلاً داخل صفحه نیستند.

جملهٔ آماده: «گزینهٔ درست در سورس صفحه نیست؛ تصحیح سمت سرور با توابع خالص انجام می‌شود و مرورگر فقط نتیجه را نمایش می‌دهد.»

### نقشهٔ کوتاه بقیهٔ فایل‌ها

| فایل | کار در یک جمله |
|---|---|
| `static/js/progress.js` | لایهٔ پیشرفت: از `progress-state` سرور برای کاربر وارد‌شده، وگرنه از `localStorage` — بقیهٔ صفحه تفاوتی نمی‌فهمد |
| `static/js/lesson_status.js` | دسته‌بندی وضعیت هر درس (completed / current / started / upcoming / available) — یک جا برای داشبورد و مسیر |
| `static/js/lesson_visit.js` | یک کار: با `markVisited` ثبت می‌کند درس باز شده |
| `static/js/audio.js` | یک رفتار پخش صدا برای کل محصول؛ پخش هر فایل بقیه را متوقف می‌کند |
| `lessons/.../lesson_reader.js` | پاپ‌آور واژه: واژه‌های آلمانی در متن را clickable می‌کند و از `vocabulary:word-lookup` JSON می‌گیرد |
| `lessons/.../lesson_steps.js` | استپر: نمایش گام‌به‌گام + یک POST کوچک به `lessons:lesson-progress` برای کاربر وارد‌شده |

نکتهٔ ریز برای بک‌اند: `progress.js` وقتی وضعیت سروری دارد، **نمی‌نویسد** — ذخیره کار صفحهٔ درس است که هر گام را POST می‌کند. «یک نویسنده برای هر واقعیت» تا دو منبع با هم نپرد.

---

## ۱۳. مسائل شناخته‌شدهٔ پروژه

این‌ها باگ‌هایی هستند که موقع بررسی پیدا شده‌اند ولی **اصلاح نشده‌اند** چون خارج از درخواست بوده‌اند. در مصاحبه اگر پرسیدند «چه مشکلی را می‌دانی که رفع نکرده‌ای؟»، همین‌ها جواب‌های صادقانه‌ای هستند.

### ۱) ماژول گمشدهٔ `vocabulary/german_text.py`

دو دستور صوتی این خط را در بالای فایل دارند:

```python
from vocabulary.german_text import spoken_text
```

ولی چنین فایلی وجود ندارد. یعنی هر بار که `generate_lesson_content_audio` یا `generate_grammar_audio` اجرا یا حتی import شود، `ModuleNotFoundError` می‌گیریم. پنج دستور دیگر سالم‌اند. توضیح: «صادقانه می‌گویم دو دستور صوتی به یک ماژول استخراج متن آلمانی وابسته‌اند که در مخزن وجود ندارد — احتمالاً در `.gitignore` مانده یا هرگز commit نشده. اثرش این است که تولید صوت بلوک‌های درس و گرامر الان کار نمی‌کند؛ صوت واژه‌ها و جمله‌ها سالم است.»

### ۲) چهار خطای داده در `seed_a1_course --check`

خروجی `--check` چهار خطا می‌دهد:

- `entschuldigung` (با حروف کوچک) در `a1_lessons_a.py:130` و `a1_lessons_b.py:678,1679` — در دیتابیس `Entschuldigung` (نوع OTHER) ثبت شده.
- `gern haben` در `a1_lessons_a.py:1140` — در دیتابیس `gernhaben` (نوع VERB) ثبت شده.

این‌ها خطاهای داده‌اند نه کد؛ seed با `sys.exit(1)` تمام می‌شود و چیزی نمی‌نویسد، پس محافظت کار می‌کند. توضیح: «دستور seed قبل از نوشتن، داده را اعتبارسنجی می‌کند و روی خطا exit code می‌دهد — این خطاها را عمداً نگه داشته‌ام تا نشان بدهم محافظ کار می‌کند.»

### ۳) اجرای تست‌های `lessons` به‌صورت کلاس‌به‌کلاس

`manage.py test lessons` به‌خاطر کلاس seed که `setUpTestData` دارد و `sys.exit(1)` صدا می‌زند، بی‌صدا متوقف می‌شود. پنج کلاس دیگر را باید جدا اجرا کنی: `DashboardTests`، `LearningPathTests`، `LessonJourneyTests`، `LessonProgressTests`، `LessonProgressEndpointTests`.

### ۴) `SECRET_KEY` و پسورد دیتابیس داخل `settings.py`

در بخش ۱۷ کامل توضیح داده شده.

### ۵) فایل کهن `guide.py`

در ریشهٔ مخزن است، gitignore شده، هیچ‌جا import نمی‌شود و به مدل `lessons.Level` که وجود ندارد اشاره می‌کند. کد مرده است — لمسش نکن، فقط بدان چیست.

### ۶) ناسازگاری نسخه در مستندات

`AGENTS.md` می‌گوید Django 4.2 ولی محیط واقعاً **Django 6.1.1** دارد و `requirements.txt` هم `Django==6.1.1` را می‌خواهد. در مصاحبه همیشه عدد `requirements.txt` را بگو.

---

## ۱۴. نقشهٔ ارتباط اپ‌ها

```
                       accounts.UserProfile ──┐
                                              │ (current_level)
                              lessons.LanguageLevel
                                    │                 ▲
                    ┌───────────────┼─────────────┐   │
                    ▼               ▼             ▼   │
              vocabulary.Word  vocabulary.Grammar  vocabulary.Sentence
                    ▲               ▲             ▲
                    │               │             │
                LessonWord      LessonGrammar   LessonSentence   ← مالکیت: lessons
                    │               │             │
                    └──────────── lessons.Lesson ┘
                                     │
                                     ▼
                              exercises.Exercise → Question → QuestionTarget
                                                                   │
                                          exercises.Answer, exercises.ExerciseAttempt
                                     ▲
                                     │
                          vocabulary.WordProgress / lessons.LessonProgress
```

قواعدی که باید بگویی:
1. **`lessons` قطب است.** `vocabulary` به `lessons.LanguageLevel` اشاره می‌کند؛ `exercises` به `lessons.Lesson`.
2. **`vocabulary` محتوای مشترک است** و از دو طرف ارجاع داده می‌شود: جدول‌های واسط درس و اهداف سؤال.
3. **سه جدول پیشرفت** (`LessonProgress`، `WordProgress`، `ExerciseAttempt`) با کاربر کلید خورده‌اند و همین‌ها اپ را «شخصی‌سازی‌شده» می‌کنند.
4. **هر اپ `urls.py` خودش را با `app_name` دارد**، پس نام‌ها تصادم نمی‌کنند (`accounts:login` در برابر `lessons:lesson-detail`).

---

## ۱۵. جدول: این تکه را چطور توضیح بدهی

| تکهٔ کد | جملهٔ آماده برای مصاحبه |
|---|---|
| `settings.py` | «پیکربندی: اپ‌ها، دیتابیس، static/media، و redirectهای احراز هویت. بدون منطق دامنه.» |
| `config/urls.py` | «دروازهٔ ورودی: خانه به داشبورد، و URL هر اپ با `include`.» |
| `context_processors.py` | «یک لیست منو که در دو نوار رندر می‌شود؛ نام URL با `reverse` مسیر می‌شود و آیتم فعال از `resolver_match` حساب می‌شود.» |
| `accounts/signals.py` | «سیگنال `post_save` پروفایل را خودکار می‌سازد تا هیچ ویویی یادش نرود.» |
| `accounts/views.py` | «CBV ساده با `get`/`post` صریح؛ `?next=` با `url_has_allowed_host_and_scheme` محافظت شده.» |
| `Lesson` + `UniqueConstraint` | «ترتیب درس‌ها را در دیتابیس تضمین کردم، نه فقط در کد.» |
| `LessonWord` | «جدول واسط با ویژگی: همان واژه در یک درس `NEW` و در درس دیگر `REVIEW` است.» |
| `LessonContent` | «درس یک فهرست بلوک نوع‌دار و مرتب است، نه یک فیلد متن غول‌آسا.» |
| `journey.py` | «تابع خالص که محتوا را به گام‌ها تبدیل می‌کند؛ گام فقط با محتوای موجود ساخته می‌شود.» |
| `progress.py` | «تنها نویسندهٔ `LessonProgress`؛ قواعد یک بار نوشته شده‌اند.» |
| `LessonProgressView` | «POST-only و JSON، با `raise_exception` تا مهمان ۴۰۳ بگیرد نه redirect.» |
| `Paginator(...)` در گام واژگان | «درس تا ۱۷۰ واژه دارد، پس گام صفحه‌بندی می‌شود.» |
| `Word.TYPE_LABELS` | «برچسب فارسی برای دانش‌آموز و انگلیسی برای ادمین؛ `property` است پس migration لازم ندارد.» |
| `WordLookupView` | «endpoint ای‌جکس برای پاپ‌آور واژه در صفحهٔ درس.» |
| `word__word_type` در `Word.Meta` | «یکتایی واژه + نوع + جنسیت، تا اسم و فعل قاطی نشوند.» |
| `QuestionTarget` + `CheckConstraint` | «دقیقاً یکی از واژه/گرامر/جمله، و حداکثر یک هدف آزمون‌شده — تضمین‌شده در دیتابیس.» |
| `grading.py` | «تصحیح سمت سرور با توابع خالص؛ قبلاً در مرورگر بود و جواب‌ها لو می‌رفت.» |
| `normalize()` | «فاصله‌های تکراری یکی می‌شوند، نشانه‌گذاری انتهایی و بزرگی/کوچکی حروف نادیده گرفته می‌شود.» |
| `runner.py` | «شکل صفحه: choice / text / unchecked، از روی تعداد ردیف‌های `Answer`.» |
| `ExerciseAttempt` | «هر ارسال یک ردیف جدید؛ تاریخچه بازنویسی نمی‌شود.» |
| `vocabulary/progress.py` | «فقط واژهٔ `TESTED_ITEM` شمارنده‌اش حرکت می‌کند؛ `CONTEXT` دست‌نخورده می‌ماند.» |
| `tests/tests.py` | «بررسی‌های سراسری: کامنت چنده‌خطی در تمپلیت و رندر صفحات ۴۰۴/۵۰۰.» |
| `select_related` / `prefetch_related` | «برای جلوگیری از N+1؛ سطح، درس و گزینه‌ها در همان چند کوئری می‌آیند.» |
| `annotate(Count(...))` | «شمارش را در همان کوئری می‌گیرم، نه با یک کوئری برای هر ردیف.» |

---

## ۱۶. سؤال‌های احتمالی مصاحبه و پاسخ

**۱) چرا CBV و نه FBV؟**
> «`View` را با `get`/`post` صریح استفاده کردم. صریح بودن مهم بود: هر ویو رفتاری را نشان می‌دهد که خودم نوشتم، نه چیزی که از `FormView` یا `DetailView` ارث رسیده و باید در کد منبع جنگو دنبالش کنی.»

**۲) چرا منطق را از ویو جدا کردی؟**
> «چون تصحیح، ساخت گام‌ها و قواعد پیشرفت همان بخش‌هایی هستند که بیشترین احتمال باگ دارند. وقتی توابع خالص و ماژول‌های جدا باشند، بدون HTTP قابل تست‌اند.»

**۳) چرا `OneToOneField` برای پروفایل و `OneToOneField` برای دوره؟**
> «چون رابطه واقعاً یک-به-یک است. دیتابیس هم آن را تضمین می‌کند، نه فقط کد.»

**۴) چرا `PROTECT` در `vocabulary` ولی `CASCADE` در `accounts`؟**
> «واژه بدون سطح زبانی بی‌معناست، پس حذف سطح باید جلوی گرفته شود. اما اگر حساب کاربری حذف شود، پروفایلش هم باید برود.»

**۵) چرا ترتیب در `UniqueConstraint` تضمین شده؟**
> «چون ترتیب بخشی از درستی داده است. اگر فقط در پایتون مرتب کنم، یک اسکریپت یا ادمین می‌تواند دادهٔ خراب جا بگذارد.»

**۶) چطور جلوی N+1 را گرفتی؟**
> «با `select_related` برای کلیدهای خارجی و `prefetch_related` برای رابطه‌های چند‌به‌چند و برعکس؛ و `annotate` برای شمارش‌ها.»

**۷) چرا تصحیح را از مرورگر به سرور آوردی؟**
> «قبلاً جواب درست در سورس صفحه بود؛ هر کسی می‌توانست بخواند. الان حکم از ردیف‌های واقعی `Answer` روی سرور ساخته می‌شود و به مرورگر گفته می‌شود.»

**۸) چرا برای مهمان‌ها هم کار می‌کند؟**
> «محتوای آموزشی عمومی است. مهمان تمرین را می‌بیند و حکم می‌گیرد، ولی چون `ExerciseAttempt` به کاربر نیاز دارد، چیزی ذخیره نمی‌شود. پیشرفت مهمان در `localStorage` مرورگر می‌ماند و وقتی وارد شود، شکل دادهٔ سرور و مرورگر یکی است.»

**۹) چرا `?next=` را محدود کردی؟**
> «بدون بررسی میزبان، `?next=https://evil.example` صفحهٔ ورود را به یک open redirect تبدیل می‌کند. `url_has_allowed_host_and_scheme` تضمین می‌کند مقصد روی همین سایت است.»

---

## ۱۷. یک نکتهٔ امنیتی که باید بدانی (هنوز اصلاح نشده)

در `config/settings.py` هم `SECRET_KEY` و هم پسورد PostgreSQL **مستقیم داخل کد** نوشته شده‌اند. برای توسعهٔ محلی اشکالی ندارد، ولی:

- لحظه‌ای که پروژه را روی GitHub بگذاری یا روی سرور ببری، این یک مشکل واقعی است.
- `SECRET_KEY` لو برود، session و توکن CSRF قابل جعل می‌شوند.
- پسورد دیتابیس لو برود، یعنی دسترسی کامل به داده.

راه‌حل استاندارد: خواندن هر دو از متغیر محیطی (`os.environ`) و گذاشتن یک فایل نمونهٔ `.env` بدون مقدار واقعی، و اضافه کردن `.env` به `.gitignore`.

> من این را **خودسرانه تغییر ندادم** چون خارج از این درخواست بود. اگر بگویی، انجامش می‌دهم — ولی قبلش permission لازم است.

---

## ۱۸. جملهٔ آخر برای مصاحبه

> «یک اپ جنگو ۶.۱ برای یادگیری آلمانی از A1 است. `lessons` برنامهٔ درسی را به‌صورت بلوک‌های محتوایی مرتب مدل می‌کند؛ `vocabulary` واژه و گرامر و جملهٔ قابل‌استفادهٔ مجدد را نگه می‌دارد؛ `exercises` از کاربر تمرین می‌گیرد، پاسخ‌ها را در ماژول جدا تصحیح می‌کند و هر تلاش را ذخیره می‌کند؛ `accounts` هویت را با یک سیگنال پروفایل مدیریت می‌کند؛ و `config` همه‌چیز را به هم وصل می‌کند. پیشرفت کاربر در سه جدول نگه داشته می‌شود و رابط کاربری دانش‌آموز فارسی است.»

</div>
