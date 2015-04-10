import os
import shutil
from neurovault.settings import PRIVATE_MEDIA_ROOT

def clearTestMediaRoot():
    if os.path.exists(PRIVATE_MEDIA_ROOT):
        for the_file in os.listdir(PRIVATE_MEDIA_ROOT):
            file_path = os.path.join(PRIVATE_MEDIA_ROOT, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path): 
                    shutil.rmtree(file_path)
            except Exception, e:
                print e
