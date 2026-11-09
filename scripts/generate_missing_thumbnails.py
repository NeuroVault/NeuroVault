import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.config.settings")
django.setup()

from neurovault.adapters.persistence.models import Item
from neurovault.adapters.tasks import process_map, save_resampled_transformation_single

for image in Item.objects.statmaps():
    print(image.id)
    if not image.thumbnail or not os.path.exists(image.thumbnail.path):
        process_map.apply_async([image.id])
        save_resampled_transformation_single.apply_async([image.id])
