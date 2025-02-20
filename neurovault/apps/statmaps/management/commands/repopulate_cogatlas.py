from django.core.management.base import BaseCommand
from neurovault.apps.statmaps.tasks import repopulate_cognitive_atlas


class Command(BaseCommand):
    help = "repopulates cognitive atlas"

    def handle(self, *args, **options):
        repopulate_cognitive_atlas()