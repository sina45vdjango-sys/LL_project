from django.urls import path
from .views import (
    CourseDetailView,
    LessonCheckView,
    LessonDetailView,
    LessonImportView,
    LessonListView,
    LessonProgressView,
    LessonReviewView,
    PracticePathView,
)

app_name = "lessons"
urlpatterns = [
    # Ahead of <int:pk>/ so the literal path is not read as a lesson id. Django would
    # not match "today" to an int converter anyway, but the order keeps it obvious.
    path("today/", PracticePathView.as_view(), name="practice-path"),
    # Ahead of <int:pk>/ for the same reason as "today/": a literal path is not a lesson id.
    path("progress/import/", LessonImportView.as_view(), name="lesson-import"),
    path("<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("<int:pk>/progress/", LessonProgressView.as_view(), name="lesson-progress"),
    path("<int:pk>/review/", LessonReviewView.as_view(), name="lesson-review"),
    path("<int:pk>/check/", LessonCheckView.as_view(), name="lesson-check"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("", LessonListView.as_view(), name="lesson-list"),
]
