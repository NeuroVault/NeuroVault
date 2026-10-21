"""A scratch directory for unpacking uploaded folders and archives."""
import errno
import gzip
import os
import shutil
import tarfile
import tempfile
import zipfile
from fnmatch import fnmatch
from xml.dom import minidom

import nibabel as nib
import numpy as np
from lxml import etree

from neurovault.core.domain.map_quality import detect_4D


def splitext_nii_gz(fname):
    head, ext = os.path.splitext(fname)
    if ext.lower() == ".gz":
        _, ext2 = os.path.splitext(fname[:-3])
        ext = ext2 + ext
    return head, ext


def split_filename(fname):
    """(directory, base name, extension), treating .nii.gz and .tar.gz as one extension."""
    special_extensions = [".nii.gz", ".tar.gz"]
    if fname and fname.endswith(os.path.sep):
        fname = fname[:-1]
    pth, fname = os.path.split(fname)
    ext = None
    for special_ext in special_extensions:
        ext_len = len(special_ext)
        if (len(fname) > ext_len) and (fname[-ext_len:].lower() == special_ext.lower()):
            ext = fname[-ext_len:]
            fname = fname[:-ext_len]
            break
    if not ext:
        fname, ext = os.path.splitext(fname)
    return pth, fname, ext


def get_afni_subbrick_labels(nii):
    # AFNI header is nifti1 header extension 4
    from ast import literal_eval

    extensions = getattr(nii.header, "extensions", [])
    header = [ext for ext in extensions if ext.get_code() == 4]
    if not header:
        return []
    retval = []
    try:
        tree = etree.fromstring(header[0].get_content())
        lnode = [v for v in tree.findall(".//AFNI_atr") if v.attrib["atr_name"] == "BRICK_LABS"]
        if lnode:
            retval += literal_eval(lnode[0].text.strip()).split("~")
    except Exception:
        pass
    return retval


def split_4D_to_3D(nii, with_labels=True, tmp_dir=None):
    outpaths = []
    ext = ".nii.gz"
    base_dir, name = os.path.split(nii.get_filename())
    out_dir = tmp_dir or base_dir
    fname = name.replace(ext, "")
    slices = np.split(np.asanyarray(nii.dataobj), nii.shape[-1], len(nii.shape) - 1)
    labels = get_afni_subbrick_labels(nii)
    for n, slice in enumerate(slices):
        nifti = nib.Nifti1Image(np.squeeze(slice), nii.header.get_best_affine())
        layer_nm = labels[n] if n < len(labels) else "(volume %s)" % (n + 1)
        outpath = os.path.join(out_dir, "%s__%s%s" % (fname, layer_nm, ext))
        nib.save(nifti, outpath)
        outpaths.append((layer_nm, outpath) if with_labels else outpath)
    return outpaths


def detect_feat_directory(path):
    if not os.path.isdir(path):
        return False
    for root, dirs, files in os.walk(path):
        return (
            "stats" in dirs
            and "logs" in dirs
            and "design.fsf" in files
            and "feat4_post" in os.listdir(os.path.join(root, "logs"))
        )


class FeatDirectoryError(Exception):
    pass


class UploadWorkspace:
    """Context manager: `with UploadWorkspace() as ws: ws.extract(upload) ...`"""

    def __enter__(self):
        self.root = tempfile.mkdtemp()
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.root, ignore_errors=True)

    def extract(self, upload):
        _, ext = os.path.splitext(upload.name)
        if ext == ".zip":
            with zipfile.ZipFile(upload, "r") as zf:
                zf.extractall(self.root)
        elif ext == ".gz":
            upload.open()
            with tarfile.TarFile(fileobj=gzip.GzipFile(fileobj=upload.file, mode="r"), mode="r") as tf:
                tf.extractall(self.root)
        else:
            raise ValueError(f"Unsupported archive type: {ext}")

    def write(self, upload, directory=None):
        with open(os.path.join(directory or self.root, upload.name), "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)

    def write_tree(self, uploads, relative_paths):
        """Recreate an uploaded folder; NIDM zips inside it are skipped."""
        for upload, relative_path in zip(uploads, relative_paths):
            if fnmatch(upload.name, "*.nidm.zip"):
                continue
            final_dir, _ = os.path.split(os.path.join(self.root, relative_path))
            try:
                os.makedirs(final_dir)
            except OSError as exc:
                if not (exc.errno == errno.EEXIST and os.path.isdir(final_dir)):
                    raise
            self.write(upload, final_dir)

    def collect(self, allowed_extensions):
        """[(label, path, atlas xml path or None)] for every NIfTI volume found.

        4D files are split into 3D volumes; FEAT directories are not supported.
        """
        nifti_files = []
        atlases = {}
        for root, subdirs, filenames in os.walk(self.root):
            if detect_feat_directory(root):
                raise FeatDirectoryError("Unable to unzip the FEAT directory: \n.")
            if root.endswith(".gfeat"):
                continue
            for fname in sorted(f for f in filenames if not f.startswith(".")):
                name, ext = splitext_nii_gz(fname)
                file_path = os.path.join(root, fname)
                if ext == ".xml":
                    dom = minidom.parse(file_path)
                    for atlas in dom.getElementsByTagName("imagefile"):
                        path_str, base = os.path.split(atlas.lastChild.nodeValue)
                        atlases[os.path.join(path_str, base).lstrip("/")] = file_path
                    continue
                if ext in allowed_extensions:
                    nii = nib.load(file_path)
                    if detect_4D(nii):
                        nifti_files.extend(split_4D_to_3D(nii))
                    else:
                        nifti_files.append((fname, file_path))

        out = []
        for label, path in nifti_files:
            directory, name_no_ext, _ = split_filename(path)
            out.append((label, path, atlases.get(os.path.join(directory, name_no_ext))))
        return out

    @staticmethod
    def squeezed_volume(path):
        """(base name, .nii.gz bytes) of a 3D volume; 4D volumes raise ValueError."""
        nii = nib.load(path)
        shape = nii.shape
        if len(shape) > 3 and shape[3] > 1:
            raise ValueError("4D file detected.")
        _, base_name, _ = split_filename(path)
        squeezed = nib.Nifti1Image(np.squeeze(np.asanyarray(nii.dataobj)), nii.affine, nii.header)
        temp_dir = tempfile.mkdtemp()
        try:
            out_path = os.path.join(temp_dir, base_name + ".nii.gz")
            nib.save(squeezed, out_path)
            with open(out_path, "rb") as f:
                return base_name, f.read()
        finally:
            shutil.rmtree(temp_dir)
