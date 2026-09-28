from django.contrib import admin

from .models import (
    LanguageLevel,
    Course,
    Lesson,
    LessonContent,
    LessonWord,
    LessonGrammar,
    LessonSentence,
    LessonProgress,
)


@admin.register(LanguageLevel)
class LanguageLevelAdmin(admin.ModelAdmin):
    list_display = ("level", "title", "order")
    list_editable = ("order",)
    search_fields = ("level", "title")
    ordering = ("order",)
    list_per_page = 30

    fieldsets = (
        (None, {"fields": ("level", "title", "order")}),
    )


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    """Read-mostly: these rows are written by the lesson page as a learner moves."""

    list_display = (
        "__str__",
        "user",
        "lesson",
        "status",
        "current_step",
        "started_at",
        "completed_at",
        "last_activity_at",
    )
    list_filter = ("status", "current_step")
    search_fields = ("user__username", "lesson__title")
    list_select_related = ("user", "lesson")
    list_per_page = 50


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "language_level", "is_published")
    list_filter = ("is_published",)
    search_fields = ("title", "description", "language_level__level", "language_level__title")
    autocomplete_fields = ("language_level",)
    list_select_related = ("language_level",)
    list_per_page = 30

    fieldsets = (
        (None, {"fields": ("language_level", "title", "is_published")}),
        ("توضیح", {"fields": ("description",)}),
    )


class LessonContentInline(admin.StackedInline):
    model = LessonContent
    extra = 1
    fields = ("type", "title", "order", "body", "audio")
    ordering = ("order",)


class LessonWordInline(admin.TabularInline):
    model = LessonWord
    extra = 1
    fields = ("word", "role", "order")
    autocomplete_fields = ("word",)
    ordering = ("order",)


class LessonGrammarInline(admin.TabularInline):
    model = LessonGrammar
    extra = 1
    fields = ("grammar", "order")
    autocomplete_fields = ("grammar",)
    ordering = ("order",)


class LessonSentenceInline(admin.TabularInline):
    model = LessonSentence
    extra = 1
    fields = ("sentence", "role", "speaker", "order")
    autocomplete_fields = ("sentence",)
    ordering = ("order",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "is_published", "estimated_time")
    list_filter = ("is_published", "course__language_level__level", "course")
    search_fields = ("title", "description", "course__title", "course__language_level__level")
    list_select_related = ("course", "course__language_level")
    autocomplete_fields = ("course",)
    list_per_page = 30
    inlines = [LessonContentInline, LessonWordInline, LessonGrammarInline, LessonSentenceInline]

    fieldsets = (
        (None, {
            "fields": ("course", "title", "order", "is_published", "estimated_time"),
        }),
        ("توضیح", {"fields": ("description",)}),
    )


@admin.register(LessonContent)
class LessonContentAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "type", "order")
    list_filter = ("type", "lesson__course__language_level__level")
    search_fields = ("title", "body", "lesson__title")
    autocomplete_fields = ("lesson",)
    list_select_related = ("lesson",)
    list_per_page = 40

    fieldsets = (
        (None, {"fields": ("lesson", "type", "title", "order")}),
        ("متن", {"fields": ("body",)}),
        ("صدا", {"fields": ("audio",)}),
    )


@admin.register(LessonWord)
class LessonWordAdmin(admin.ModelAdmin):
    list_display = ("__str__", "lesson", "word", "role", "order")
    list_filter = ("role", "lesson__course__language_level__level")
    search_fields = ("word__word", "lesson__title", "lesson__course__title")
    autocomplete_fields = ("lesson", "word")
    list_select_related = ("lesson", "word")
    list_per_page = 50


@admin.register(LessonGrammar)
class LessonGrammarAdmin(admin.ModelAdmin):
    list_display = ("__str__", "lesson", "grammar", "order")
    list_filter = ("lesson__course__language_level__level",)
    search_fields = ("grammar__title", "lesson__title")
    autocomplete_fields = ("lesson", "grammar")
    list_select_related = ("lesson", "grammar")
    list_per_page = 40


@admin.register(LessonSentence)
class LessonSentenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "lesson", "sentence", "role", "speaker", "order")
    list_filter = ("role", "lesson__course__language_level__level")
    search_fields = ("sentence__text", "sentence__translation_fa", "lesson__title", "speaker")
    autocomplete_fields = ("lesson", "sentence")
    list_select_related = ("lesson", "sentence")
    list_per_page = 50