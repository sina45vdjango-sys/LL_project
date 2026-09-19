from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views import View
from .models import Course, Lesson


class CourseDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        course = get_object_or_404(Course.objects.select_related("language_level"), pk=pk, is_published=True)
        queryset = course.lessons.filter(is_published=True).select_related("course__language_level").order_by("order", "pk")
        return render(request, "lessons/course_detail.html", {
            "course": course,
            "lessons": Paginator(queryset, 12).get_page(request.GET.get("page")),
            "courses": Course.objects.filter(is_published=True).select_related("language_level"),
        })


class LessonDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course__language_level"),
            pk=pk, is_published=True, course__is_published=True,
        )
        # Small navigation rows, never full lesson bodies. Open on the current lesson's page.
        siblings = lesson.course.lessons.filter(is_published=True).order_by("order", "pk")
        current_page = siblings.filter(order__lt=lesson.order).count() // 12 + 1
        course_lessons = Paginator(siblings.values("pk", "title", "order", "estimated_time"), 12).get_page(
            request.GET.get("nav_page", current_page)
        )
        word_links = lesson.lesson_words.filter(word__is_published=True).select_related("word").order_by("order", "pk")
        exercises = lesson.exercises.filter(is_published=True).order_by("order", "pk")
        return render(request, "lessons/lesson_detail.html", {
            "lesson": lesson,
            "course_lessons": course_lessons,
            "blocks": lesson.contents.order_by("order", "pk"),
            "grammar_links": lesson.lesson_grammars.filter(grammar__is_published=True).select_related("grammar").order_by("order", "pk"),
            "sentence_links": lesson.lesson_sentences.filter(sentence__is_published=True).select_related("sentence").order_by("order", "pk"),
            "word_links": Paginator(word_links, 24).get_page(request.GET.get("words_page")),
            "exercises": exercises,
        })


class LessonListView(View):
    def get(self, request, *args, **kwargs):
        queryset = Lesson.objects.filter(
            is_published=True, course__is_published=True,
        ).select_related("course__language_level").order_by("course__language_level__order", "order", "pk")
        lessons = Paginator(queryset, 12).get_page(request.GET.get("page"))
        return render(request, "lessons/lesson_list.html", {
            "lessons": lessons,
            "courses": Course.objects.filter(is_published=True).select_related("language_level"),
        })
