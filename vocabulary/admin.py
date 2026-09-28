from django.contrib import admin

from .models import Word, Grammar, Sentence, WordProgress


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("__str__", "word_type", "gender", "meaning_fa", "meanin_en_short", "level", "is_published")
    list_filter = ("word_type", "gender", "is_published", "level__level")
    search_fields = ("word", "meaning_fa", "meaning_en", "plural", "pronunciation")
    list_per_page = 40

    autocomplete_fields = ("level",)
    list_select_related = ("level",)

    fieldsets = (
        (None, {
            "fields": (
                ("word", "word_type"),
                ("article", "gender", "plural", "pronunciation"),
                "meaning_fa",
                "meaning_en",
                ("level", "is_published"),
            ),
        }),
        ("فایل صوتی", {"fields": ("audio",), "classes": ("collapse",)}),
    )

    @admin.display(description="انگلیسی")
    def meanin_en_short(self, obj):
        return obj.meaning_en[:40] if obj.meaning_en else ""


@admin.register(WordProgress)
class WordProgressAdmin(admin.ModelAdmin):
    """Read-mostly: moved by exercise submissions, one row per learner and word."""

    list_display = (
        "__str__",
        "user",
        "word",
        "attempt_count",
        "correct_count",
        "wrong_count",
        "last_attempted_at",
    )
    list_filter = ("word__word_type",)
    search_fields = ("user__username", "word__word")
    list_select_related = ("user", "word")
    list_per_page = 50


@admin.register(Grammar)
class GrammarAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "is_published")
    list_filter = ("level__level", "is_published")
    search_fields = ("title", "explanation", "level__title", "level__level")
    list_per_page = 30

    autocomplete_fields = ("level",)
    list_select_related = ("level",)

    fieldsets = (
        (None, {"fields": ("level", "title", "is_published")}),
        ("توضیح", {"fields": ("explanation",)}),
        ("فایل صوتی", {"fields": ("audio",), "classes": ("collapse",)}),
    )


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "level", "is_published", "text_short")
    list_filter = ("level__level", "is_published")
    search_fields = ("text", "translation_fa", "level__title", "level__level")
    list_per_page = 40

    autocomplete_fields = ("level",)
    list_select_related = ("level",)

    fieldsets = (
        (None, {
            "fields": ("level", "text", "translation_fa", "is_published"),
        }),
        ("فایل صوتی", {"fields": ("audio",), "classes": ("collapse",)}),
    )

    @admin.display(description="متن")
    def text_short(self, obj):
        return (obj.text[:60] + "…") if len(obj.text) > 60 else obj.text