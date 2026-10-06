"""URL patterns for the exams app."""
from django.urls import path
from .views import (
    ExamFinishView,
    ExamIndexView,
    ExamRunView,
    ExamStartView,
    ExamSubmitView,
    SprechenView,
    StepTestView,
)

app_name = "exams"

urlpatterns = [
    path("", ExamIndexView.as_view(), name="exam-index"),
    path("start/", ExamStartView.as_view(), name="exam-start"),
    # The short station the practice path's ★ node opens (concept 20).
    path("step/", StepTestView.as_view(), name="step-test"),
    path("sprechen/", SprechenView.as_view(), name="sprechen"),
    path("runs/<int:pk>/", ExamRunView.as_view(), name="exam-run"),
    path("runs/<int:pk>/submit/", ExamSubmitView.as_view(), name="exam-submit"),
    path("runs/<int:pk>/finish/", ExamFinishView.as_view(), name="exam-finish"),
]
