from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.models import Collection, Image
from neurovault.apps.statmaps.tasks import save_resampled_transformation_single, generate_glassbrain_image



class Command(BaseCommand):
    help = 'triggers comparisons and glassbrain generation'

    def handle(self, *args, **options):
        collections = Collection.objects.exclude(DOI__isnull=True).exclude(private=True)
        for col in collections:
            for image in col.basecollectionitem_set.instance_of(Image).all():
                if image.pk:
                    print "Generating glassbrain and reduced representation for %s" %image.name
                    generate_glassbrain_image.apply([image.pk])
                    save_resampled_transformation_single.apply([image.pk])