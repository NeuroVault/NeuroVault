from neurovault.apps.statmaps.models import Image
import os, errno
from neurovault.apps.statmaps.tasks import generate_glassbrain_image

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

for image in Image.objects.filter(collection__private=False):
    generate_glassbrain_image(image.file.path, image.id)
