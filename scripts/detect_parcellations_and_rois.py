import os
from gzip import GzipFile

import django
import nibabel as nb

import neurovault.apps.statmaps.utils as nvutils
from neurovault.apps.statmaps.models import StatisticMap, BaseStatisticMap

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

for image in StatisticMap.objects.filter(map_type=BaseStatisticMap.OTHER):
    image.file.open()
    gzfileobj = GzipFile(filename=image.file.name, mode='rb', fileobj=image.file.file)
    nii = nb.Nifti1Image.from_file_map({'image': nb.FileHolder(image.file.name, gzfileobj)})
    map_type = nvutils.infer_map_type(nii)
    if map_type != BaseStatisticMap.OTHER:
        print "changed type of %s to %s"%(image.get_absolute_url(), map_type)
        image.map_type = map_type
        image.save()
    image.file.close()
