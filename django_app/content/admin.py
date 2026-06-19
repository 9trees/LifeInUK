from django.contrib import admin

from .models import StudyPage, StudyPlanItem, Topic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(StudyPage)
class StudyPageAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "topic")
    list_filter = ("topic",)


@admin.register(StudyPlanItem)
class StudyPlanItemAdmin(admin.ModelAdmin):
    list_display = ("order_no", "week_no", "title")
