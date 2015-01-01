'''
Created on 1 Sep 2014

@author: gorgolewski
'''
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