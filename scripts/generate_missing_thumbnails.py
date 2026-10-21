import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.config.settings")
django.setup()

from neurovault.adapters.persistence.models import StatisticMap
from neurovault.adapters.tasks import generate_glassbrain_image,\
    save_resampled_transformation_single

for image in StatisticMap.objects.all():
    print(image.id)
    if not image.thumbnail or not os.path.exists(image.thumbnail.path):
       generate_glassbrain_image.apply_async([image.id])
       save_resampled_transformation_single.apply_async([image.id])
