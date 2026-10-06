"""Admin for the exam module.

The exams app has no authored content — a run is something a learner did, not something
somebody writes — so this is the read-mostly side of the admin: a sitting with its score,
and the questions it asked as an inline. It is here for the same reason the other apps have
an admin: to look at real rows while developing instead of guessing from the code.
"""

from django.contrib import admin

from .models import ExamRun, ExamRunQuestion


class ExamRunQuestionInline(admin.TabularInline):
    model = ExamRunQuestion
    extra = 0
    autocomplete_fields = ("question",)
    readonly_fields = ("section", "order", "is_correct")


@admin.register(ExamRun)
class ExamRunAdmin(admin.ModelAdmin):
    list_display = ("user", "started_at", "finished_at", "question_total")
    list_filter = ("finished_at", "started_at")
    search_fields = ("user__username",)
    date_hierarchy = "started_at"
    list_select_related = ("user",)
    inlines = [ExamRunQuestionInline]

    @admin.display(description="پرسش‌ها")
    def question_total(self, run):
        return run.questions.count()


@admin.register(ExamRunQuestion)
class ExamRunQuestionAdmin(admin.ModelAdmin):
    list_display = ("run", "order", "section", "question", "is_correct")
    list_filter = ("section", "is_correct")
    search_fields = ("run__user__username", "question__prompt")
    list_select_related = ("run", "question")
    autocomplete_fields = ("question", "run")
