import os
import itertools
from django.core.files.storage import FileSystemStorage
from neurovault import settings
from django.db.models import get_model


class NiftiGzStorage(FileSystemStorage):

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = settings.PRIVATE_MEDIA_ROOT
        if base_url is None:
            base_url = settings.PRIVATE_MEDIA_URL
        return super(NiftiGzStorage, self).__init__(location, base_url)

    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        if file_ext.lower() == ".gz":
            file_root2, file_ext2 = os.path.splitext(file_root)
            if file_ext2.lower() == ".nii":
                file_root = file_root2
                file_ext = file_ext2 + file_ext
        # If the filename already exists, add an underscore and a number (before
        # the file extension, if one exists) to the filename until the generated
        # filename doesn't exist.
        count = itertools.count(1)
        while self.exists(name):
            # file_ext includes the dot.
            name = os.path.join(dir_name, "%s_%s%s" % (file_root, next(count), file_ext))

        return name

    def url(self, name):
        spath,file_name = os.path.split(name)
        spath,collection_id = os.path.split(spath)
        coll_model = get_model('statmaps','Collection')
        collection = coll_model.objects.get(id=collection_id)
        if collection.private:
            cid = collection.private_token
        else:
            cid = collection.id
        return os.path.join(self.base_url,str(cid),file_name)


class NIDMStorage(NiftiGzStorage):

    def url(self, name):
        spath,file_name = os.path.split(name)
        spath = spath.split('/')
        collection_id = spath[1]
        dirname = spath[2]
        coll_model = get_model('statmaps','Collection')
        collection = coll_model.objects.get(id=collection_id)
        if collection.private:
            cid = collection.private_token
        else:
            cid = collection.id
        return os.path.join(self.base_url,str(cid),dirname,file_name)
