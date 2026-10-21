"""Stouffer's image-based meta-analysis with NiMARE.

Ported unchanged from the original meta.py, including its known defects: the
weighted branch calls `weighted_stouffers`, which is not defined, and the
`Stouffers` call predates NiMARE's estimator API.
"""
import os

import nibabel as nib
import numpy as np

from neurovault.application.ports import MetaAnalysisResult

from .rendering import ANATOMICAL


class NiMAREEngine:
    def run(self, maps):
        from nilearn.image import resample_to_img
        from nilearn.masking import apply_mask
        from nimare.meta.ibma import Stouffers
        from nimare.transforms import t_to_z

        mask_img = nib.load(os.path.join(ANATOMICAL, "MNI152_T1_2mm_brain_mask.nii.gz"))
        z_imgs, sizes = [], []
        for m in maps:
            if m.map_type not in ["Z", "T"]:
                continue
            valid = False
            if m.map_type == "Z":
                z_imgs.append(resample_to_img(nib.load(m.path), mask_img))
                valid = True
            elif m.map_type == "T" and m.number_of_subjects:
                t_map_nii = nib.load(m.path)
                z_data = t_to_z(np.asanyarray(t_map_nii.dataobj), m.number_of_subjects - 1)
                z_imgs.append(resample_to_img(nib.Nifti1Image(z_data, t_map_nii.affine), mask_img))
                valid = True
            if valid and m.number_of_subjects:
                sizes.append(m.number_of_subjects)

        do_weighted = (len(sizes) == len(z_imgs)) and len(z_imgs) > 0
        z_data = apply_mask(z_imgs, mask_img)
        if do_weighted:
            result = weighted_stouffers(  # noqa: F821 - see module docstring
                z_data, np.array(sizes), mask_img, corr="FWE", two_sided=True, use_sample_size=True
            )
        else:
            result = Stouffers(
                z_data, mask_img, inference="ffx", null="theoretical", corr="FWE", two_sided=True
            )
        return MetaAnalysisResult(images=result.images, n_maps=len(z_imgs), weighted=do_weighted)
