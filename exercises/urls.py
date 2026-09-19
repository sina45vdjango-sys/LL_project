"""URL patterns for the exercises app."""
from django.urls import path
from .views import ExerciseDetailView, ExerciseListView

app_name = "exercises"

urlpatterns = [
    path(
        "",
        ExerciseListView.as_view(),
        name="exercise-list",
    ),
    path(
        "<int:pk>/",
        ExerciseDetailView.as_view(),
        name="exercise-detail",
    ),
]