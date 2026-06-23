from django.conf import settings
from django.db import models


class Feedback(models.Model):
    CATEGORY_CHOICES = [
        ("bug", "Bug Report"),
        ("feature", "Feature Request"),
        ("content", "Content Issue"),
        ("general", "General Feedback"),
    ]
    RATING_CHOICES = [(i, f"{i} star{'s' if i != 1 else ''}") for i in range(1, 6)]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="feedbacks",
    )
    # Snapshot so feedback survives user deletion
    user_name = models.CharField(max_length=200, blank=True, default="")
    user_email = models.EmailField(blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Snapshot user details on first save so they persist after deletion."""
        if self.user and not self.user_email:
            self.user_name = getattr(self.user, "full_name", "") or ""
            self.user_email = self.user.email or ""
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        """Return the best available name for display."""
        if self.user:
            return getattr(self.user, "full_name", None) or self.user.email
        return self.user_name or self.user_email or "Deleted User"

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback #{self.id} by {self.user} ({self.category})"
