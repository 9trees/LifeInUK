import json

from django.conf import settings
from django.core.management.base import BaseCommand

from content.models import StudyPlanItem


class Command(BaseCommand):
    help = "Import study plan checklist items from study_plan.json."

    def handle(self, *args, **options):
        path = settings.STUDY_PLAN_FILE
        if not path.exists():
            self.stderr.write(f"Missing {path}")
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        StudyPlanItem.objects.all().delete()
        count = 0
        for item in data.get("items", []):
            StudyPlanItem.objects.create(
                week_no=item.get("week_no", 0),
                order_no=item.get("order_no", count + 1),
                title=item.get("title", ""),
                description=item.get("description", ""),
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} study plan items."))
