from __future__ import absolute_import
import os
import numpy
import pylab as plt
import nibabel as nib
from celery import shared_task
from scipy.stats.stats import pearsonr
from nilearn.plotting import plot_glass_brain
from django.shortcuts import get_object_or_404
from neurovault.celery import nvcelery as celery_app
from pybraincompare.compare.mrutils import resample_images_ref, make_binary_deletion_mask
from pybraincompare.compare.maths import calculate_correlation
from pybraincompare.mr.datasets import get_data_directory

@shared_task
def generate_glassbrain_image(image_pk):
    from neurovault.apps.statmaps.models import Image
    img = Image.objects.get(pk=image_pk)
    png_img_name = "glass_brain_%s.png" % img.pk
    png_img_path = os.path.join(os.path.split(img.file.path)[0], png_img_name)
    if os.path.exists(png_img_path):
        os.unlink(png_img_path)
    glass_brain = plot_glass_brain(img.file.path)
    glass_brain.savefig(png_img_path)
    plt.close('all')
    return png_img_path


@shared_task
def save_resampled_image(pk1, resample_dim=[4, 4, 4]):
    from neurovault.apps.statmaps.models import Image
    from nilearn.image import resample_img
    import neurovault
    img = get_object_or_404(Image, pk=pk1)
    nii_obj = nib.load(img.file.path)
    
    # If a standard already exists with the voxel dimension, we use that to save time
    standard = os.path.abspath(os.path.join(neurovault.settings.BASE_DIR,
                                                  "static","anatomical",
                                                  "MNI152_%smm.nii.gz" % resample_dim[0]))
    if not os.path.exists(standard):
      standard = os.path.abspath(os.path.join(neurovault.settings.BASE_DIR,"static","anatomical","MNI152.nii.gz"))
    standard_brain = nib.load(standard)
    
    # Resample both image and mask - resampling will be skipped if affines already equivalent
    img_resamp, ref_resamp = resample_images_ref(images=[nii_obj], 
                                                 reference=standard_brain, 
                                                 interpolation="continuous",
                                                 resample_dim=resample_dim)

    # Mask the image, and save to image folder
    empty_nii = numpy.zeros(img_resamp[0].shape)
    empty_nii[ref_resamp.get_data()!=0] = img_resamp[0].get_data()[ref_resamp.get_data()!=0]
    masked_nii = nib.nifti1.Nifti1Image(empty_nii,affine=img_resamp[0].get_affine(),header=img_resamp[0].get_header())

    nii_resamp_name = "resample_%smm_%s.nii" %(resample_dim[0],img.pk)
    nii_img_path = os.path.join(os.path.split(img.file.path)[0], nii_resamp_name)
    if os.path.exists(nii_img_path):
        os.unlink(nii_img_path)

    nib.save(masked_nii,nii_img_path)
    return nii_img_path


@shared_task
def save_voxelwise_pearson_similarity(pk1, pk2, resample_dim=[4, 4, 4]):
    from neurovault.apps.statmaps.models import Similarity, Comparison

    # We will always calculate Comparison 1 vs 2, never 2 vs 1
    if pk1 != pk2:
        sorted_images = get_images_by_ordered_id(pk1, pk2)
        image1 = sorted_images[0]
        image2 = sorted_images[1]
        pearson_metric = Similarity.objects.get(
                            similarity_metric="pearson product-moment correlation coefficient",
                            transformation="voxelwise")


        # Get standard space brain
        mr_directory = get_data_directory()
        reference = "%s/MNI152_T1_2mm_brain_mask.nii.gz" %(mr_directory)
        image_paths = [image.file.path for image in [image1, image2]]
        images_resamp, reference_resamp = resample_images_ref(images=image_paths, 
                                                              reference=reference, 
                                                              interpolation="continuous",
                                                              resample_dim=resample_dim)
        # resample_images_ref will "squeeze" images, but we should keep error here for now
        for image_nii, image_obj in zip(images_resamp, [image1, image2]):
          if len(numpy.squeeze(image_nii.get_data()).shape) != 3:
            raise Exception("Image %s (id=%d) has incorrect number of dimensions %s"%(image_obj.name, 
                             image_obj.id, str(image_nii.get_data().shape)))


        # Calculate correlation only on voxels that are in both maps (not zero, and not nan)
        image1_res = images_resamp[0]
        image2_res = images_resamp[1]
        binary_mask = make_binary_deletion_mask(images_resamp)
        binary_mask = nib.Nifti1Image(binary_mask,header=image1_res.get_header(),affine=image1_res.get_affine())
        # Will return nan if comparison is not possible
        pearson_score = calculate_correlation([image1_res,image2_res],mask=binary_mask,corr_type="pearson")
      
        try:
            compare = Comparison.objects.get(image1=image1, image2=image2,
                                             similarity_metric=pearson_metric)
        except Comparison.DoesNotExist:
            compare = Comparison(image1=image1, image2=image2, similarity_metric=pearson_metric)

        compare.similarity_score = pearson_score
        compare.save()
        return image1.pk,image2.pk,pearson_score
    else:
        raise Exception("You are trying to compare an image with itself!")


# Helper functions
'''Return list of Images sorted by the primary key'''
def get_images_by_ordered_id(pk1, pk2):
    from neurovault.apps.statmaps.models import Image
    image1 = get_object_or_404(Image, pk=pk1)
    image2 = get_object_or_404(Image, pk=pk2)
    return sorted([image1,image2], key=lambda x: x.pk)
