"""
URL configuration for the Language_Learning project.

Each local app exposes its own urlpatterns in <app>/urls.py; add routes there
and they become reachable under the prefix declared below.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('lessons/', include('lessons.urls')),
    path('vocabulary/', include('vocabulary.urls')),
    path('exercises/', include('exercises.urls')),
    path('tests/', include('tests.urls')),
]
