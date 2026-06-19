from django.core.management.base import BaseCommand

from content.models import Topic

TOPICS = {
    1: "The values and principles of the UK",
    2: "What is the UK?",
    3: "A long and illustrious history",
    4: "A modern, thriving society",
    5: "The UK government, the law and your role",
}


class Command(BaseCommand):
    help = "Create the five Life in the UK topics."

    def handle(self, *args, **options):
        for code, name in TOPICS.items():
            obj, created = Topic.objects.update_or_create(code=code, defaults={"name": name})
            self.stdout.write(("Created " if created else "Updated ") + str(obj))
        self.stdout.write(self.style.SUCCESS("Topics imported."))
