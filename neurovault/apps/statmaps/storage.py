import errno
import itertools
import os
import tempfile
from django.apps import apps
from django.core.files.move import file_move_safe
from django.core.files.storage import FileSystemStorage
from fnmatch import fnmatch

from neurovault import settings


class NeuroVaultStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None):
        if location is None:
            location = settings.PRIVATE_MEDIA_ROOT
        if base_url is None:
            base_url = settings.PRIVATE_MEDIA_URL
        super(NeuroVaultStorage, self).__init__(location, base_url)

    def url(self, name):
        collection_id = None
        spath, file_name = os.path.split(name)
        urlsects = [v for v in spath.split('/') if v]
        for i in range(len(urlsects)):
            sect = urlsects.pop(0)
            if sect.isdigit():
                collection_id = sect
                break
        cont_path = '/'.join(urlsects)
        coll_model = apps.get_model('statmaps', 'Collection')
        collection = coll_model.objects.get(id=collection_id)
        if collection.private:
            cid = collection.private_token
        else:
            cid = collection.id
        return os.path.join(self.base_url, str(cid), cont_path, file_name)


class NiftiGzStorage(NeuroVaultStorage):
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


class OverwriteStorage(NeuroVaultStorage):
    def get_available_name(self, name):
        return name

    def _save(self, name, content):
        full_path = self.path(name)

        # Create any intermediate directories that do not exist.
        # Note that there is a race between os.path.exists and os.makedirs:
        # if os.makedirs fails with EEXIST, the directory was created
        # concurrently, and we can continue normally. Refs #16082.
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            try:
                if self.directory_permissions_mode is not None:
                    # os.makedirs applies the global umask, so we reset it,
                    # for consistency with file_permissions_mode behavior.
                    old_umask = os.umask(0)
                    try:
                        os.makedirs(directory, self.directory_permissions_mode)
                    finally:
                        os.umask(old_umask)
                else:
                    os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        if not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        tmp_file = tempfile.mktemp()
        filey = open(tmp_file, 'wb')
        filey.write(content.read())
        # make sure that all data is on disk
        filey.flush()
        os.fsync(filey.fileno())
        filey.close()
        file_move_safe(tmp_file, full_path, allow_overwrite=True)
        return name


class NIDMStorage(NiftiGzStorage):
    def __init__(self, location=None, base_url=None):
        super(NIDMStorage, self).__init__(location, base_url)

    def url(self, name):
        rpath = super(NIDMStorage, self).url(name)
        rpath = rpath.replace(self.base_url, '/collections/').split('/')
        for ext in ['.ttl', '.zip']:
            if fnmatch(rpath[-1], '*{0}'.format(ext)):
                rpath.pop()
                return '/'.join(rpath) + ext
        return '/'.join(rpath)
