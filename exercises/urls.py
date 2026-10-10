"""URL patterns for the exercises app."""
from django.urls import path
from .views import (
    ExerciseDetailView,
    ExerciseHintView,
    ExerciseListView,
    ExerciseSubmitView,
    PracticeChatView,
    PracticeDialogueView,
    SessionView,
)

app_name = "exercises"

urlpatterns = [
    path(
        "",
        ExerciseListView.as_view(),
        name="exercise-list",
    ),
    # Before `<int:pk>/`, though "session" is not an int either way — the order keeps
    # the two shapes easy to read together.
    path(
        "session/",
        SessionView.as_view(),
        name="session",
    ),
    path(
        "<int:pk>/",
        ExerciseDetailView.as_view(),
        name="exercise-detail",
    ),
    # Concept 9's delivery mode. Its own prefix, because it is a different reading of the
    # same exercise rather than a second exercise page.
    path(
        "chat/<int:pk>/",
        PracticeChatView.as_view(),
        name="exercise-chat",
    ),
    # Concept 13's delivery mode: the same turn engine, framed as a role-play.
    path(
        "dialogue/<int:pk>/",
        PracticeDialogueView.as_view(),
        name="exercise-dialogue",
    ),
    path(
        "<int:pk>/submit/",
        ExerciseSubmitView.as_view(),
        name="exercise-submit",
    ),
    path(
        "<int:pk>/hint/",
        ExerciseHintView.as_view(),
        name="exercise-hint",
    ),
]