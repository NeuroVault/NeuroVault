from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.models import KeyValueTag

class Command(BaseCommand):
    args = 'none'
    help = 'Deletes non-lowercase tags'

    def handle(self, *args, **options):
        tags = KeyValueTag.objects.all()
        for i_, tag in enumerate(tags):
            if not tag.name.islower():
                print "Deleting %s" %tag.name
                tag.delete()