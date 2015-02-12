'''
Created on 1 Sep 2014

@author: gorgolewski
'''

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Image,ValueTaggedItem
from neurovault.apps.statmaps.utils import detect_afni4D, split_afni4D_to_3D,memory_uploadfile


from neurovault.apps.statmaps.models import Image
import nibabel as nb
import numpy as np



for image in Image.objects.all():
    nii = nb.load(image.file.path)
    if len(nii.shape) > 3:
        print image.file.path, nii.shape
        data = np.squeeze(nii.get_data())
        new_nii = nb.Nifti1Image(data, nii.get_affine())
        nb.save(new_nii, image.file.path)
