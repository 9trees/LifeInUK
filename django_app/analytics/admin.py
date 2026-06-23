from django.contrib import admin

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "rating", "is_read", "created_at")
    list_filter = ("category", "rating", "is_read")
    search_fields = ("user__email", "message")
    readonly_fields = ("user", "category", "rating", "message", "created_at")
