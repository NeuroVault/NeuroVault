import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Image
from neurovault.apps.statmaps.tasks import generate_glassbrain_image

for image in Image.objects.filter(collection__private=False):
    generate_glassbrain_image(image.id)
