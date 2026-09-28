from django.contrib import admin

from .models import (
    Exercise,
    ExerciseAttempt,
    Question,
    QuestionTarget,
    Answer,
)


@admin.register(ExerciseAttempt)
class ExerciseAttemptAdmin(admin.ModelAdmin):
    """Read-mostly: one row per answer a learner has submitted."""

    list_display = (
        "__str__",
        "user",
        "question",
        "answer",
        "response_text",
        "is_correct",
        "response_time",
        "created_at",
    )
    list_filter = ("is_correct", "question__exercise__type")
    search_fields = ("user__username", "question__prompt", "answer__text", "response_text")
    list_select_related = ("user", "question", "answer")
    list_per_page = 50


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("__str__", "question", "is_correct", "match_type", "order")
    list_filter = ("is_correct", "match_type", "question__exercise__type")
    search_fields = ("text", "question__prompt")
    list_per_page = 40

    autocomplete_fields = ("question",)
    list_select_related = ("question", "question__exercise")

    fieldsets = (
        (None, {"fields": ("question", "order", "is_correct", "match_type")}),
        ("متن گزینه", {"fields": ("text",)}),
    )


class AnswerInline(admin.TabularInline):
    """Edit answers inline on the Question form."""
    model = Answer
    extra = 2
    fields = ("text", "is_correct", "match_type", "order")


class QuestionTargetInline(admin.StackedInline):
    """Edit question targets inline on the Question form."""
    model = QuestionTarget
    extra = 1
    autocomplete_fields = ("word", "grammar", "sentence")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "exercise", "order")
    list_filter = (
        "exercise__type",
        "exercise__difficulty",
        "exercise__lesson__course__language_level",
    )
    search_fields = ("prompt", "exercise__title", "exercise__lesson__title")
    list_per_page = 30

    autocomplete_fields = ("exercise",)
    list_select_related = ("exercise",)
    inlines = [QuestionTargetInline, AnswerInline]

    fieldsets = (
        (None, {"fields": ("exercise", "order")}),
        ("سؤال", {
            "fields": ("prompt", "audio", "image"),
            "classes": ("wide",),
        }),
        ("توضیح (اختیاری)", {"fields": ("explanation",), "classes": ("collapse",)}),
    )


@admin.register(QuestionTarget)
class QuestionTargetAdmin(admin.ModelAdmin):
    list_display = ("__str__", "question", "role", "word", "grammar", "sentence")
    list_filter = ("role", "word__word_type", "grammar", "sentence__level")
    search_fields = (
        "question__prompt",
        "question__exercise__title",
        "word__word",
        "grammar__title",
        "sentence__text",
    )
    list_select_related = ("question", "question__exercise", "word", "grammar", "sentence")
    autocomplete_fields = ("question", "word", "grammar", "sentence")


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "type", "difficulty", "order", "is_published")
    list_filter = ("type", "difficulty", "is_published", "lesson__course__language_level")
    search_fields = ("title", "instruction", "lesson__title", "lesson__course__language_level__level")
    list_per_page = 20

    autocomplete_fields = ("lesson",)
    list_select_related = ("lesson", "lesson__course__language_level")

    fieldsets = (
        (None, {
            "fields": ("lesson", "title", "type", "difficulty", "order", "is_published"),
        }),
        ("ورودی", {
            "fields": ("instruction",),
            "classes": ("wide",),
        }),
    )