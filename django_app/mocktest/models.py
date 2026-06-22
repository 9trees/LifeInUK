from django.conf import settings
from django.db import models

from practice.models import AnswerOption, Question


class MockTestSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mock_sessions")
    question_ids = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=24)
    correct_answers = models.PositiveIntegerField(default=0)
    pass_status = models.BooleanField(default=False)
    score_percent = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Mock {self.id} ({self.user})"


class MockTestResponse(models.Model):
    mock_session = models.ForeignKey(MockTestSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mock_session", "question"], name="unique_mock_response"),
        ]


class MockTestQuestionEvent(models.Model):
    mock_session = models.ForeignKey(MockTestSession, on_delete=models.CASCADE, related_name="events")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    question_order = models.PositiveSmallIntegerField(default=0)
    dwell_time_ms = models.PositiveIntegerField(default=0)
    revisit_count = models.PositiveIntegerField(default=0)
    answer_changed_count = models.PositiveIntegerField(default=0)
