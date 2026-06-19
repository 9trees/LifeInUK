from django.urls import path

from . import views

app_name = "mocktest"

urlpatterns = [
    path("", views.mock_start, name="start"),
    path("<int:session_id>/run/", views.mock_run, name="run"),
    path("<int:session_id>/submit/", views.mock_submit, name="submit"),
    path("<int:session_id>/result/", views.mock_result, name="result"),
]
