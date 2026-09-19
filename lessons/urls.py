from django.urls import path
from .views import CourseDetailView, LessonDetailView, LessonListView

app_name = "lessons"
urlpatterns = [
    path("<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("", LessonListView.as_view(), name="lesson-list"),
]
