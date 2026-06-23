from django.contrib import admin

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "rating", "created_at")
    list_filter = ("category", "rating")
    search_fields = ("user__email", "message")
    readonly_fields = ("user", "category", "rating", "message", "created_at")
