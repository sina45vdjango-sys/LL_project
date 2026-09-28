from django.urls import path
from django.views.generic import RedirectView
from .views import (
    WordDetailView,
    WordLevelListView,
    WordListView,
    WordLookupView,
    WordReviewView,
)



app_name = "vocabulary"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="vocabulary:word-list")),
    path("words/", WordListView.as_view(), name="word-list"),
    path("words/level/<str:level_code>/", WordLevelListView.as_view(), name="word-level-list"),
    path("review/", WordReviewView.as_view(), name="word-review"),
    path("words/<int:pk>/", WordDetailView.as_view(), name="word-detail"),
    # Keep previously shared detail URLs usable after the rename.
    path("word/<int:pk>/", RedirectView.as_view(pattern_name="vocabulary:word-detail")),
    path("lookup/", WordLookupView.as_view(), name="word-lookup"),
]
