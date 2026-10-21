"""Project fsaverage surface maps into an MNI volume with FreeSurfer."""
import os
import shutil
import subprocess
import tempfile
from io import BytesIO
from subprocess import CalledProcessError

import nibabel as nb
import numpy as np

from neurovault.core.application.ports import ProjectedSurface, SurfaceInputError

FIELDS = {"lh": "surface_left_file", "rh": "surface_right_file"}
INTENTS = {"lh": "CortexLeft", "rh": "CortexRight"}
SURFACE_EXTENSIONS = [".mgh", ".curv", ".gii", ".nii", ".nii.gz"]


def _splitext_nii_gz(fname):
    head, ext = os.path.splitext(fname)
    if ext.lower() == ".gz":
        _, ext2 = os.path.splitext(fname[:-3])
        ext = ext2 + ext
    return head, ext


def _run(cmd):
    try:
        subprocess.check_output(cmd)
    except CalledProcessError as e:
        raise RuntimeError(
            str(e.cmd) + " returned code " + str(e.returncode) + " with output " + e.output
        )


class FreeSurferProjector:
    def __init__(self, freesurfer_home=None):
        self.home = freesurfer_home

    def _fs(self, *parts):
        return os.path.join(self.home or os.environ["FREESURFER_HOME"], *parts)

    def project(self, left, right, name):
        uploads = {"lh": left, "rh": right}
        tmp_dir = tempfile.mkdtemp()
        try:
            new_name = name + ".nii.gz"
            ribbon_projection_file = os.path.join(tmp_dir, new_name)
            for hemi in ["lh", "rh"]:
                surface_file = uploads[hemi]
                _, ext = _splitext_nii_gz(surface_file.name)
                if ext.lower() not in SURFACE_EXTENSIONS:
                    raise SurfaceInputError(FIELDS[hemi], "Doesn't have proper extension")

                infile = os.path.join(tmp_dir, hemi + ext)
                surface_file.open()
                with open(infile, "wb") as fd:
                    shutil.copyfileobj(BytesIO(surface_file.read()), fd)

                if ext.lower() != ".gii":
                    out_gii = os.path.join(tmp_dir, hemi + ".gii")
                    _run([
                        self._fs("bin", "mris_convert"), "-c", infile,
                        self._fs("subjects", "fsaverage", "surf", hemi + ".white"), out_gii,
                    ])
                else:
                    out_gii = infile

                gii = nb.load(out_gii)
                if gii.darrays[0].dims != [163842]:
                    raise SurfaceInputError(
                        FIELDS[hemi], "Doesn't have proper dimensions - are you sure it's fsaverage?"
                    )
                # fix intent
                meta = gii.meta.metadata
                meta["AnatomicalStructurePrimary"] = INTENTS[hemi]
                gii.meta = gii.meta.from_dict(meta)
                gii.to_filename(os.path.join(tmp_dir, hemi + ".gii"))

                _run([
                    self._fs("bin", "mri_surf2surf"), "--s", "fsaverage", "--hemi", hemi,
                    "--srcsurfval", os.path.join(tmp_dir, hemi + ".gii"),
                    "--trgsubject", "ICBM2009c_asym_nlin",
                    "--trgsurfval", os.path.join(tmp_dir, hemi + ".MNI.gii"),
                ])

            _run([
                self._fs("bin", "mri_surf2vol"), "--subject", "ICBM2009c_asym_nlin",
                "--o", ribbon_projection_file[:-3],
                "--so", self._fs("subjects", "ICBM2009c_asym_nlin", "surf", "lh.white"),
                os.path.join(tmp_dir, "lh.MNI.gii"),
                "--so", self._fs("subjects", "ICBM2009c_asym_nlin", "surf", "rh.white"),
                os.path.join(tmp_dir, "rh.MNI.gii"),
            ])

            # fix one voxel offset
            nii = nb.load(ribbon_projection_file[:-3])
            affine = nii.affine
            affine[0, 3] -= 1
            nb.Nifti1Image(np.asanyarray(nii.dataobj), affine).to_filename(ribbon_projection_file)

            def read(path):
                with open(path, "rb") as f:
                    return f.read()

            return ProjectedSurface(
                volume_name=new_name,
                volume=read(ribbon_projection_file),
                left_name=new_name[:-7] + ".fsaverage.lh.func.gii",
                left=read(os.path.join(tmp_dir, "lh.gii")),
                right_name=new_name[:-7] + ".fsaverage.rh.func.gii",
                right=read(os.path.join(tmp_dir, "rh.gii")),
            )
        finally:
            shutil.rmtree(tmp_dir)
