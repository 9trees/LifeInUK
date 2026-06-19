from django.contrib import admin

from .models import AnswerOption, PracticeResponse, PracticeSession, Question


class AnswerInline(admin.TabularInline):
    model = AnswerOption


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "topic")
    list_filter = ("topic",)
    inlines = [AnswerInline]


admin.site.register(PracticeSession)
admin.site.register(PracticeResponse)
