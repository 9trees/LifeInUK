from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("feedback/", views.feedback_view, name="feedback"),
    path("infographics/", views.infographics_view, name="infographics"),
    path("feedback-admin/", views.feedback_admin, name="feedback_admin"),
    path("feedback-admin/<int:pk>/read/", views.feedback_mark_read, name="feedback_mark_read"),
    path("feedback-admin/mark-all-read/", views.feedback_mark_all_read, name="feedback_mark_all_read"),
]
