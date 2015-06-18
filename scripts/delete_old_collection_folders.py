"""
deletes collection folders for collections that were deleted. after this update, folders should be deleted
automatically when the collection is deleted so this is simply to delete folders created before this update
"""

from neurovault.settings import PRIVATE_MEDIA_ROOT
import os
import os.path
from neurovault.apps.statmaps.models import *

def delOldCollDir():
    collDir = os.path.join(PRIVATE_MEDIA_ROOT, 'images')
    for folder in os.listdir(collDir):
        if not Collection.objects.filter(pk=folder):
            os.rmdir(os.path.join(collDir, folder))
            
delOldCollDir()