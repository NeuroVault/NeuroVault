from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.models import ValueTaggedItem, Image

class Command(BaseCommand):
    args = 'none'
    help = 'Lowercases all tag names'

    def handle(self, *args, **options):
        value_tags = ValueTaggedItem.objects.all().distinct('object_id')
        for i_, value in enumerate(value_tags):
            image = Image.objects.all().filter(id=value.object_id)
            tags = image[0].tags.names()
            tags = [x.lower() for x in tags]
            tags = list(set(tags))[:]
            image[0].tags.clear()
            for j_, tag_name in enumerate(tags):
                image[0].tags.add(tag_name)