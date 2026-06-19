import json

from django.conf import settings
from django.core.management.base import BaseCommand

from content.models import Topic
from practice.models import AnswerOption, Question


class Command(BaseCommand):
    help = "Import the 422-question bank from lituk_questions_422.json."

    def handle(self, *args, **options):
        path = settings.QUESTION_BANK_FILE
        if not path.exists():
            self.stderr.write(f"Missing {path}")
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        topic_by_name = {t.name: t for t in Topic.objects.all()}

        Question.objects.all().delete()
        count = 0
        for item in data:
            topic_name = item.get("topic")
            topic = topic_by_name.get(topic_name)
            if topic is None:
                self.stderr.write(f"Unknown topic: {topic_name}; skipping.")
                continue

            q = Question.objects.create(
                topic=topic,
                text=item.get("question", {}).get("text", "").strip(),
                explanation=item.get("explanation", {}).get("text", "").strip(),
            )
            for order, ans in enumerate(item.get("answers", [])):
                AnswerOption.objects.create(
                    question=q,
                    text=ans.get("text", "").strip(),
                    is_correct=bool(ans.get("correct")),
                    display_order=order,
                )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} questions."))
