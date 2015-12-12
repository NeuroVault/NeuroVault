import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Image
from neurovault.apps.statmaps.tasks import generate_glassbrain_image,\
    save_resampled_transformation_single

for image in Image.objects.filter(collection__private=False):
    print image.id
    generate_glassbrain_image.apply_async([image.id])
    save_resampled_transformation_single.apply_async([image.id])
