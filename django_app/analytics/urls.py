from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("feedback/", views.feedback_view, name="feedback"),
    path("infographics/", views.infographics_view, name="infographics"),
]
