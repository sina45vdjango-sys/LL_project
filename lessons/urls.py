from django.urls import path
from .views import CourseDetailView, LessonDetailView, LessonListView, LessonProgressView

app_name = "lessons"
urlpatterns = [
    path("<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("<int:pk>/progress/", LessonProgressView.as_view(), name="lesson-progress"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("", LessonListView.as_view(), name="lesson-list"),
]
