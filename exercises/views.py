from django.shortcuts import get_object_or_404, render
from django.views import View

from exercises.models import Exercise


class ExerciseListView(View):
    """List all exercises for a lesson (or all exercises)."""

    template_name = "exercises/exercise_list.html"

    def get(self, request, *args, **kwargs):
        from lessons.models import Lesson

        lesson_pk = request.GET.get("lesson")
        lesson = None
        exercises = Exercise.objects.select_related("lesson").order_by("lesson__order", "order")
        if lesson_pk:
            lesson = get_object_or_404(Lesson, pk=lesson_pk)
            exercises = Exercise.objects.filter(lesson=lesson).order_by("order")
        return render(request, self.template_name, {"lesson": lesson, "exercises": exercises})


class ExerciseDetailView(View):
    """Display a single exercise with its questions and answers."""

    template_name = "exercises/exercise_detail.html"

    def get(self, request, pk, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise.objects.prefetch_related(
                "questions__answers",
                "questions__targets",
            ),
            pk=pk,
        )
        return render(request, self.template_name, {"exercise": exercise})
