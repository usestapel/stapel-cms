"""Promote scheduled snapshots whose time has come (the beat pass, by hand)."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Publish scheduled pages and posts whose publish_at has passed."

    def handle(self, *args, **options):
        from stapel_cms.services.content import promote_due

        count = promote_due()
        self.stdout.write(f"published {count} scheduled item(s)")
