from django.urls import path

from . import views

app_name = "study"

urlpatterns = [
    path("", views.study_index, name="index"),
    path("plan/", views.study_plan_view, name="plan"),
    path("plan/toggle/<int:item_id>/", views.toggle_plan_item, name="toggle_plan"),
    path("page/<slug:slug>/", views.study_page_view, name="page"),
    path("page/<slug:slug>/complete/", views.complete_page, name="complete"),
]
