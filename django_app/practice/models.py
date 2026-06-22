from django.conf import settings
from django.db import models

from content.models import Topic


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    explanation = models.TextField(blank=True)

    def __str__(self):
        return self.text[:60]


class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.text} ({'correct' if self.is_correct else 'wrong'})"


class PracticeSession(models.Model):
    MODE_RANDOM_10 = "random_10"
    MODE_RANDOM_20 = "random_20"
    MODE_RANDOM_30 = "random_30"
    MODE_UNANSWERED = "unanswered"
    MODE_ALL = "all"
    MODE_CHOICES = [
        (MODE_RANDOM_10, "Random 10"),
        (MODE_RANDOM_20, "Random 20"),
        (MODE_RANDOM_30, "Random 30"),
        (MODE_UNANSWERED, "Unanswered"),
        (MODE_ALL, "All"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="practice_sessions")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    selected_topics = models.JSONField(default=list)
    question_ids = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    score_percent = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Practice {self.id} ({self.user})"


class PracticeResponse(models.Model):
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    response_time_ms = models.PositiveIntegerField(default=0)
    explanation_viewed = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "question"], name="unique_practice_response"),
        ]
