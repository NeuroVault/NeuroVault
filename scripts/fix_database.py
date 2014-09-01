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
    if len(image.file.name.split("/")) < 3:
        print image.file.name
        new_name = "/".join(["images", str(image.collection_id), image.file.path.split("/")[-1]])
        print new_name
        print image.file.path
        new_path = "/".join(image.file.path.split("/")[:-1] + ["images", str(image.collection_id), image.file.path.split("/")[-1],])
        print new_path
        
        mkdir_p("/".join(image.file.path.split("/")[:-1] + ["images", str(image.collection_id)]))
        os.rename(image.file.path, new_path)
        image.file.name = new_name
        image.save()


