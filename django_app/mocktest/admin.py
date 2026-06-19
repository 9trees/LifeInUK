from django.contrib import admin

from .models import MockTestQuestionEvent, MockTestResponse, MockTestSession

admin.site.register(MockTestSession)
admin.site.register(MockTestResponse)
admin.site.register(MockTestQuestionEvent)
