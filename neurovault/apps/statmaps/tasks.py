from __future__ import absolute_import
import os
import numpy
import pickle
import pylab as plt
import nibabel as nib
from django.db.models import Q
from celery import shared_task 
from nilearn.plotting import plot_glass_brain
from django.shortcuts import get_object_or_404
from neurovault.celery import nvcelery as celery_app
from pybraincompare.compare.mrutils import resample_images_ref, make_binary_deletion_mask, make_binary_deletion_vector
from pybraincompare.compare.maths import calculate_correlation, calculate_pairwise_correlation
from pybraincompare.mr.datasets import get_data_directory

# THUMBNAIL IMAGE GENERATION ###########################################################################

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

# IMAGE TRANSFORMATION ################################################################################

# Save 4mm, brain masked image vector in pkl file in image folder
@shared_task
def save_resampled_transformation_single(pk1, resample_dim=[4, 4, 4]):
    from neurovault.apps.statmaps.models import Image
    from nilearn.image import resample_img
    from neurovault.apps.statmaps.utils import save_pickle_atomically
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

    # Mask the image, and save pickle image folder 
    # (this is the same procedure used to produce the atlas vector that will be used for scatterplot)
    image_vector = img_resamp[0].get_data()[ref_resamp.get_data()!=0]

    pkl_resamp_name = "transform_%smm_%s.pkl" %(resample_dim[0],img.pk)
    img_directory = os.path.split(img.file.path)[0]
    pkl_img_path = os.path.join(img_directory, pkl_resamp_name)
    save_pickle_atomically(image_vector,filename=pkl_img_path,directory=img_directory) 

    # Update the image "transform" field with the pkl_img_path
    img.transform = pkl_img_path
    img.save()

    return pkl_img_path


# SIMILARITY CALCULATION ##############################################################################

@shared_task
def run_voxelwise_pearson_similarity(pk1):
    from neurovault.apps.statmaps.models import Image, Comparison

    image1 = get_object_or_404(Image, pk=pk1)

    # Calculate comparisons for other images, and generate transform if needed
    imgs = Image.objects.filter(collection__private=False).exclude(pk=pk1)
    comp_qs = imgs.exclude(polymorphic_ctype__model__in=['image','atlas']).order_by('id')
    print "Found %s other images to compare to!" % len(comp_qs)
    for comp_img in comp_qs:
        iargs = sorted([comp_img.pk,pk1]) 
        
        print "Calculating pearson similarity for images %s and %s" % (iargs[0],iargs[1])
        save_voxelwise_pearson_similarity.apply_async(iargs)  # Default uses transformation, transformation = True


@shared_task
def save_voxelwise_pearson_similarity(pk1,pk2,resample_dim=[4,4,4],transformation=True):
    if transformation == False:
      save_voxelwise_pearson_similarity_resample(pk1,pk2,resample_dim)
    else:
      save_voxelwise_pearson_similarity_transformation(pk1,pk2)


# Calculate pearson correlation from pickle files with brain masked vectors of image values
def save_voxelwise_pearson_similarity_transformation(pk1, pk2):
    from neurovault.apps.statmaps.models import Similarity, Comparison, Image

    # We will always calculate Comparison 1 vs 2, never 2 vs 1
    if pk1 != pk2:
        sorted_images = get_images_by_ordered_id(pk1, pk2)
        image1 = sorted_images[0]
        image2 = sorted_images[1]
        pearson_metric = Similarity.objects.get(
                            similarity_metric="pearson product-moment correlation coefficient",
                            transformation="voxelwise")
    
        # Make sure we have a transforms for pks in question
        if image1.transform is None:
            save_resampled_transformation_single(pk1) # cannot run this async
            image1 = get_object_or_404(Image, pk=image1.pk)

        if image2.transform is None:
            save_resampled_transformation_single(pk2) # cannot run this async
            image2 = get_object_or_404(Image, pk=image2.pk)

        # Load image pickles
        image_vector1 = pickle.load(open(image1.transform,"rb"))
        image_vector2 = pickle.load(open(image2.transform,"rb"))

        # Calculate binary deletion vector mask (find 0s and nans)
        mask = make_binary_deletion_vector([image_vector1,image_vector2])

        # Calculate pearson
        pearson_score = calculate_pairwise_correlation(image_vector1[mask==1],
                                                      image_vector2[mask==1],
                                                      corr_type="pearson")   

        # Only save comparison if is not nan
        if not numpy.isnan(pearson_score):     
            Comparison.objects.update_or_create(image1=image1, image2=image2,
                                            similarity_metric=pearson_metric,
                                            similarity_score=pearson_score)

            return image1.pk,image2.pk,pearson_score
    else:
        raise Exception("You are trying to compare an image with itself!")


def save_voxelwise_pearson_similarity_resample(pk1, pk2,resample_dim=[4,4,4]):
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

        # Only save comparison if is not nan
        if not numpy.isnan(pearson_score):     
            Comparison.objects.update_or_create(image1=image1, image2=image2,
                                            similarity_metric=pearson_metric,
                                            similarity_score=pearson_score)

            return image1.pk,image2.pk,pearson_score
    else:
        raise Exception("You are trying to compare an image with itself!")



# HELPER FUNCTIONS ####################################################################################

'''Return list of Images sorted by the primary key'''
def get_images_by_ordered_id(pk1, pk2):
    from neurovault.apps.statmaps.models import Image
    image1 = get_object_or_404(Image, pk=pk1)
    image2 = get_object_or_404(Image, pk=pk2)
    return sorted([image1,image2], key=lambda x: x.pk)
