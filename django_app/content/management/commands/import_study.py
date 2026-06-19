import json

from django.conf import settings
from django.core.management.base import BaseCommand

from content.models import StudyPage, Topic


class Command(BaseCommand):
    help = "Import study pages from study_content.json (scraped from the site)."

    def handle(self, *args, **options):
        path = settings.STUDY_CONTENT_FILE
        if not path.exists():
            self.stderr.write(f"Missing {path}")
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        topic_names = data.get("topic_names", {})
        for code_str, name in topic_names.items():
            Topic.objects.update_or_create(code=int(code_str), defaults={"name": name})

        count = 0
        for page in data.get("pages", []):
            topic = Topic.objects.get(code=page["topic_code"])
            StudyPage.objects.update_or_create(
                topic=topic,
                sequence_no=page["sequence_no"],
                defaults={
                    "title": page.get("title", ""),
                    "blocks": page.get("blocks", page.get("content_blocks", [])),
                },
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} study pages."))
