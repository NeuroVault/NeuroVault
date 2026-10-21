"""Map files on the local filesystem under PRIVATE_MEDIA_ROOT."""
import os
import shutil
import stat
from contextlib import contextmanager

from django.core.files import File
from django.core.files.base import ContentFile

from neurovault.adapters.persistence.storage import DoubleExtensionStorage, OverwriteStorage


def _remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class LocalMapStore:
    """Files keep today's layout: images/<collection>/[<bundle>/]<filename>.

    New names never overwrite: `x.nii.gz` becomes `x_1.nii.gz` when taken,
    unless `overwrite` is requested.
    """

    def __init__(self):
        self.storage = DoubleExtensionStorage()
        self.overwriting = OverwriteStorage()

    def save(self, directory, filename, content, overwrite=False):
        storage = self.overwriting if overwrite else self.storage
        if isinstance(content, (bytes, str)):
            content = ContentFile(content)
        elif not isinstance(content, File):
            content = File(content)
        name = storage.generate_filename(os.path.join(directory, os.path.basename(filename)))
        return storage.save(name, content)

    def save_local(self, directory, filename, path):
        with open(path, "rb") as f:
            return self.save(directory, filename, File(f))

    def open(self, ref):
        return self.storage.open(ref, "rb")

    @contextmanager
    def local_path(self, ref):
        yield self.storage.path(ref)

    def path(self, ref):
        return self.storage.path(ref)

    def exists(self, ref):
        return bool(ref) and self.storage.exists(ref)

    def size(self, ref):
        return self.storage.size(ref)

    def delete(self, ref):
        if ref:
            self.storage.delete(ref)

    def delete_tree(self, directory):
        path = self.storage.path(directory)
        if os.path.isdir(path):
            shutil.rmtree(path, onerror=_remove_readonly)

    def move(self, ref, directory):
        new_ref = self.storage.get_available_name(os.path.join(directory, os.path.basename(ref)))
        old_path, new_path = self.storage.path(ref), self.storage.path(new_ref)
        assert old_path != new_path
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        shutil.copy(old_path, new_path)
        os.remove(old_path)
        return new_ref
