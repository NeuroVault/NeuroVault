'''
Created on 1 Sep 2014

@author: gorgolewski
'''
from neurovault.apps.statmaps.models import Image
import os

import os, errno

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

for image in Image.objects.all():
    if not image.file.name.endswith(".nii.gz") and image.file.name.endswith(".gz"):
        print(image.file.name)
        if image.file.name.endswith("nii.gz"):
            offset = 6
        else:
            offset = 3
        new_name = image.file.name[:-offset] + ".nii.gz"
        print(new_name)
        print(image.file.path)
        new_path = image.file.path[:-offset] + ".nii.gz"
        print(new_path)
        
        os.rename(image.file.path, new_path)
        image.file.name = new_name
        image.save()


