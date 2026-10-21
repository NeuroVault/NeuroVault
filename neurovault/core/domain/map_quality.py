"""Quality assessment of brain maps.

Pure functions over nibabel images and numpy arrays; the brain mask for a
template is passed in by the caller.
"""
import os
import re

import nibabel as nb
import numpy as np

from . import vocabulary as v

THRESHOLDED_RATIO = 0.85


def is_thresholded(nii_obj, thr=THRESHOLDED_RATIO):
    """(is the map thresholded, ratio of zero or NaN voxels)."""
    data = np.asanyarray(nii_obj.dataobj)
    missing_mask = (data == 0) | np.isnan(data)
    ratio_bad = float(missing_mask.sum()) / float(missing_mask.size)
    return (ratio_bad > thr, ratio_bad)


def infer_map_type(nii_obj):
    """ROI/mask, parcellation or other, from the distinct non-zero values."""
    data = np.asanyarray(nii_obj.dataobj)
    missing_mask = (data == 0) | np.isnan(data)
    unique_values = np.unique(data[np.logical_not(missing_mask)])
    if len(unique_values) == 1:
        return v.R
    if len(unique_values) > 1200:
        return v.OTHER
    map_type = v.Pa
    for val in unique_values:
        if not (
            isinstance(val, np.integer)
            or (isinstance(val, np.floating) and float(val).is_integer())
        ):
            return v.OTHER
        if (data == val).sum() == 1:
            return v.OTHER
    return map_type


def not_in_mni(nii, mask_nii):
    """(outside template space, % of mask covered, % of voxels outside the mask).

    `mask_nii` is the template's brain mask, or None when the template has none.
    """
    if mask_nii is None:
        return False, 100.0, 100.0
    from nilearn.image import resample_img

    # resample to the smaller one
    if np.prod(nii.shape) > np.prod(mask_nii.shape):
        nan_mask = np.isnan(np.asanyarray(nii.dataobj))
        if nan_mask.sum() > 0:
            np.asanyarray(nii.dataobj)[nan_mask] = 0
        nii = resample_img(
            nii,
            target_affine=mask_nii.affine,
            target_shape=mask_nii.shape,
            interpolation="nearest",
        )
    else:
        mask_nii = resample_img(
            mask_nii,
            target_affine=nii.affine,
            target_shape=nii.shape,
            interpolation="nearest",
        )

    brain_mask = np.asanyarray(mask_nii.dataobj) > 0
    data = np.asanyarray(nii.dataobj)
    excursion_set = np.logical_not(np.logical_or(data == 0, np.isnan(data)))

    # AFNI files
    if len(excursion_set.shape) == 5:
        excursion_set = excursion_set[:, :, :, 0, 0]
    # 4D files
    elif len(excursion_set.shape) == 4:
        excursion_set = excursion_set[:, :, :, 0]
    in_brain_voxels = np.logical_and(excursion_set, brain_mask).sum()
    out_of_brain_voxels = np.logical_and(excursion_set, np.logical_not(brain_mask)).sum()

    perc_mask_covered = in_brain_voxels / float(brain_mask.sum()) * 100.0
    if np.isnan(perc_mask_covered):
        perc_mask_covered = 0
    perc_voxels_outside_of_mask = out_of_brain_voxels / float(excursion_set.sum()) * 100.0

    if perc_mask_covered > 50:
        ret = perc_mask_covered < 90 and perc_voxels_outside_of_mask > 20
    elif perc_mask_covered == 0:
        ret = True
    elif perc_voxels_outside_of_mask > 50:
        ret = True
    else:
        ret = False

    return ret, perc_mask_covered, perc_voxels_outside_of_mask


def detect_4D(nii):
    shape = nii.shape
    return (len(shape) == 4 and 1 < shape[3] < 20) or (len(shape) == 5 and shape[3] == 1)


def map_type_from_filename(path):
    """T, F or Other, from the SPM naming convention."""
    basename = os.path.basename(path)
    if re.match("spmT.*", basename, re.IGNORECASE):
        return v.T
    if re.match("spmF.*", basename, re.IGNORECASE):
        return v.F
    return v.OTHER


def load_gzipped(name, fileobj):
    """Read a NIfTI from an open (possibly gzipped) file object."""
    from gzip import GzipFile

    if name.endswith(".gz"):
        fileobj = GzipFile(filename=name, mode="rb", fileobj=fileobj)
    return nb.Nifti1Image.from_file_map({"image": nb.FileHolder(name, fileobj)})
