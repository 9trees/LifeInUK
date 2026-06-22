from django.db import models


class Topic(models.Model):
    code = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}. {self.name}"


class StudyPage(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="pages")
    sequence_no = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=300)
    # Ordered list of content blocks: headings, paragraphs, bullets, images, tables.
    blocks = models.JSONField(default=list)

    class Meta:
        ordering = ["topic__code", "sequence_no"]
        constraints = [
            models.UniqueConstraint(fields=["topic", "sequence_no"], name="unique_study_page"),
        ]

    @property
    def slug(self):
        return f"{self.topic.code}_{self.sequence_no}"

    def __str__(self):
        return f"{self.slug}: {self.title}"


class StudyPlanItem(models.Model):
    week_no = models.PositiveSmallIntegerField(default=0)
    order_no = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=500)
    description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["order_no"]

    def __str__(self):
        return f"W{self.week_no}: {self.title[:50]}"
