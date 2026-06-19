from django.urls import path

from . import views

app_name = "practice"

urlpatterns = [
    path("", views.practice_setup, name="setup"),
    path("<int:session_id>/q/<int:index>/", views.practice_question, name="question"),
    path("<int:session_id>/q/<int:index>/answer/", views.practice_answer, name="answer"),
    path("<int:session_id>/result/", views.practice_result, name="result"),
]
