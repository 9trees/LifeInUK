from django.urls import path

from . import views

app_name = "mocktest"

urlpatterns = [
    path("", views.mock_intro, name="start"),
    path("begin/", views.mock_start, name="begin"),
    path("<int:session_id>/q/<int:index>/", views.mock_question, name="question"),
    path("<int:session_id>/q/<int:index>/save/", views.mock_save_answer, name="save_answer"),
    path("<int:session_id>/q/<int:index>/flag/", views.mock_toggle_flag, name="toggle_flag"),
    path("<int:session_id>/q/<int:index>/track/", views.mock_track_event, name="track_event"),
    path("<int:session_id>/submit/", views.mock_submit, name="submit"),
    path("<int:session_id>/result/", views.mock_result, name="result"),
]
