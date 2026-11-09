"""Derived images: glass-brain thumbnails, viewer surfaces, reduced vectors."""
import os
from io import BytesIO

import nibabel as nib
import numpy

ANATOMICAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "statmaps", "static", "anatomical",
)


class NilearnThumbnailRenderer:
    def glass_brain(self, volume_path):
        import matplotlib as mpl
        import pylab as plt
        from nilearn.plotting import plot_glass_brain

        mpl.rcParams["savefig.format"] = "jpg"
        my_dpi = 50
        fig = plt.figure(figsize=(330.0 / my_dpi, 130.0 / my_dpi), dpi=my_dpi)
        f = BytesIO()
        try:
            glass_brain = plot_glass_brain(volume_path, figure=fig)
            glass_brain.savefig(f, dpi=my_dpi)
        finally:
            plt.close("all")
        return f.getvalue()


class FsaverageSurfaceSampler:
    """Sample an MNI volume at the fsaverage vertices (ANTs MNI->fs mapping)."""

    def sample(self, volume_path, nearest):
        from scipy.interpolate import interpn
        from scipy.io import loadmat

        img_vol = nib.load(volume_path)
        data_vol = numpy.asanyarray(img_vol.dataobj)
        if data_vol.ndim > 3:
            data_vol = data_vol[:, :, :, 0]  # number of time points

        out = {}
        for hemi in ["lh", "rh"]:
            ras_coor = loadmat(
                os.path.join(ANATOMICAL, "%s.avgMapping_allSub_RF_ANTs_MNI2fs.mat" % hemi)
            )["ras"]
            vox_coor = nib.affines.apply_affine(numpy.linalg.inv(img_vol.affine), ras_coor.T).T
            data_surf = interpn(
                points=[list(range(n)) for n in data_vol.shape[:3]],
                values=data_vol,
                xi=vox_coor.T,
                method="nearest" if nearest else "linear",
                bounds_error=False,
                fill_value=0,
            )
            # without turning nan's to zeros Connectome Workbench behaves weird
            data_surf[numpy.isnan(data_surf)] = 0

            # ASCII is the only encoding that produces outputs compatible with Connectome Workbench
            img_surf = nib.gifti.GiftiImage()
            img_surf.add_gifti_data_array(
                nib.gifti.GiftiDataArray(data_surf, "NIFTI_INTENT_NONE", "NIFTI_TYPE_FLOAT32", "ASCII")
            )
            img_surf.meta.data.insert(
                0,
                nib.gifti.GiftiNVPairs(
                    "AnatomicalStructurePrimary", {"lh": "CortexLeft", "rh": "CortexRight"}[hemi]
                ),
            )
            out[hemi] = img_surf.to_xml()
        return out


class NilearnMapReducer:
    """4mm, brain-masked vector of a map (the gene-expression decoder input)."""

    def reduce(self, volume_path):
        import numpy as np
        from nilearn.image import resample_img
        from nilearn.maskers import NiftiMasker

        mask = nib.load(os.path.join(ANATOMICAL, "MNI152_T1_4mm_brain_mask.nii.gz"))
        image_resampled = resample_img(
            nib.load(volume_path), target_affine=mask.affine, target_shape=mask.shape
        )
        masker = NiftiMasker(mask_img=mask)
        masker.fit()
        f = BytesIO()
        np.save(f, masker.transform(image_resampled).flatten())
        return f.getvalue()


class StaticTemplateMasks:
    def mask(self, template):
        from neurovault.core.domain.vocabulary import POSSIBLE_TEMPLATES

        mask_file = POSSIBLE_TEMPLATES[template]["mask"]
        if mask_file is None:
            return None
        return nib.load(os.path.join(ANATOMICAL, mask_file))
