# meta.py
import os
import nibabel as nib
import numpy as np
from nilearn.image import resample_to_img
from nilearn.masking import apply_mask
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Collection, StatisticMap
from nimare.meta.ibma import Stouffers
from nimare.transforms import t_to_z
from nilearn.masking import apply_mask
from nilearn.image import resample_to_img

# 1. Get the default mask image
def load_default_mask(get_possible_templates, default_template):
    """
    Loads the default mask NIfTI image from your POSSIBLE_TEMPLATES.
    """
    POSSIBLE_TEMPLATES = get_possible_templates()
    mask_path = POSSIBLE_TEMPLATES[default_template]["mask"]
    
    # Get the absolute path to this app's directory
    this_path = os.path.abspath(os.path.dirname(__file__))
    full_mask_path = os.path.join(this_path, "static", "anatomical", mask_path)
    
    return nib.load(full_mask_path)

# 2. Create a new Collection for the meta-analysis
def create_collection_for_metaanalysis(metaanalysis):
    """
    Creates and returns a new Collection object 
    for the final meta-analysis results.
    """
    new_collection = Collection(
        name=f"Metaanalysis {metaanalysis.pk}: {metaanalysis.name}",
        owner=metaanalysis.owner,
        full_dataset_url=metaanalysis.get_absolute_url(),
    )
    new_collection.save()
    return new_collection

# 3. Gather Z images (and sizes if applicable) from each map
def gather_images_and_sizes(metaanalysis, mask_img):
    """
    Loops over all maps in `metaanalysis` and returns:
      - A list of Z images (after converting T->Z if needed)
      - A list of sample sizes for each valid image
    """
    z_imgs = []
    sizes = []

    for img in metaanalysis.maps.all():
        # We only handle Z or T (with known # subjects)
        if img.map_type not in ["Z", "T"]:
            continue
        
        valid = False
        file_path = img.file.path
        
        if img.map_type == "Z":
            z_imgs.append(resample_to_img(nib.load(file_path), mask_img))
            valid = True
        elif img.map_type == "T" and img.number_of_subjects:
            t_map_nii = nib.load(file_path)
            # Convert T->Z (assuming one-sided by default)
            z_data = t_to_z(
                np.asanyarray(t_map_nii.dataobj),
                img.number_of_subjects - 1
            )
            z_map_nii = nib.Nifti1Image(z_data, t_map_nii.affine)
            z_imgs.append(resample_to_img(z_map_nii, mask_img))
            valid = True

        if valid and img.number_of_subjects:
            sizes.append(img.number_of_subjects)

    return z_imgs, sizes

# 4. Update the collection's description based on weighted or unweighted
def set_collection_description(collection, z_imgs, do_weighted):
    """
    Sets the description field on `collection` based on 
    how many images and whether weighting is used.
    """
    num_images = len(z_imgs)
    
    if do_weighted:
        collection.description = (
            "Two sided Stouffer's fixed-effects image-based "
            f"meta-analysis on {num_images} maps weighted by "
            "their corresponding sample sizes. FWE corrected "
            "with theoretical null distribution."
        )
    else:
        collection.description = (
            "Two sided Stouffer's fixed-effects image-based "
            f"meta-analysis on {num_images} maps. FWE "
            "corrected with theoretical null distribution."
        )

    collection.save()

# 5. Run the chosen meta-analysis (weighted or unweighted)
def run_meta_analysis(z_imgs, sizes, mask_img):
    """
    Decides whether to use weighted_stouffers or Stouffers 
    based on matching sizes length. Returns a result object 
    with images["z"], images["p"], etc.
    """
    do_weighted = (len(sizes) == len(z_imgs)) and len(z_imgs) > 0
    z_data = apply_mask(z_imgs, mask_img)

    if do_weighted:
        result = weighted_stouffers(
            z_data,
            np.array(sizes),
            mask_img,
            corr="FWE",
            two_sided=True,
            use_sample_size=True,
        )
    else:
        result = Stouffers(
            z_data,
            mask_img,
            inference="ffx",
            null="theoretical",
            corr="FWE",
            two_sided=True,
        )
    
    return result, do_weighted

# 6. Create Django StatisticMap objects from result images
def create_and_save_statmaps(result, do_weighted, collection, tmp_dir):
    """
    Creates Z map, P map, and optionally FFX map from `result`.
    Saves them to disk in `tmp_dir`, then uploads to the DB.
    Returns the created StatisticMap objects (z_map, p_map, ffx_map or None).
    """

    z_map = StatisticMap(
        name="FWE corrected Z map",
        description="",
        collection=collection,
        modality="Other",
        map_type="Z",
        analysis_level="M",
        target_template_image="GenericMNI",
    )
    p_map = StatisticMap(
        name="FWE corrected P map",
        description="",
        collection=collection,
        modality="Other",
        map_type="P",
        analysis_level="M",
        number_of_subjects=-1,
        target_template_image="GenericMNI",
    )
    ffx_map = None

    # 6.1 Save Z image
    z_path = os.path.join(tmp_dir, "z_fwe_corr.nii.gz")
    result.images["z"].to_filename(z_path)
    z_map.file = SimpleUploadedFile("z_fwe_corr.nii.gz", open(z_path, "rb").read())
    z_map.save()

    # 6.2 Save P image
    p_path = os.path.join(tmp_dir, "p_fwe_corr.nii.gz")
    result.images["p"].to_filename(p_path)
    p_map.file = SimpleUploadedFile("p_fwe_corr.nii.gz", open(p_path, "rb").read())
    p_map.save()

    # 6.3 If weighted, save ffx_stat
    if do_weighted:
        ffx_map = StatisticMap(
            name="FFX map",
            description="",
            collection=collection,
            modality="Other",
            map_type="Other",
            analysis_level="M",
            target_template_image="GenericMNI",
        )
        ffx_path = os.path.join(tmp_dir, "ffx_stat.nii.gz")
        result.images["ffx_stat"].to_filename(ffx_path)
        ffx_map.file = SimpleUploadedFile("ffx_stat.nii.gz", open(ffx_path, "rb").read())
        ffx_map.save()

    return z_map, p_map, ffx_map
