from __future__ import absolute_import
from pybraincompare.compare.maths import calculate_correlation, calculate_pairwise_correlation
from pybraincompare.compare.mrutils import resample_images_ref, make_binary_deletion_mask, make_binary_deletion_vector
from pybraincompare.mr.transformation import make_resampled_transformation_vector
from pybraincompare.mr.datasets import get_data_directory
from neurovault.celery import nvcelery as celery_app
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from nilearn.plotting import plot_glass_brain
from nilearn.image import resample_img
from sklearn.externals import joblib
from django.db.models import Q
from celery import shared_task
from six import BytesIO
import nibabel as nib
import pylab as plt
import numpy
import os


# THUMBNAIL IMAGE GENERATION ###########################################################################

@shared_task
def generate_glassbrain_image(image_pk):
    from neurovault.apps.statmaps.models import Image
    import neurovault
    import matplotlib as mpl
    mpl.rcParams['savefig.format'] = 'jpg'
    my_dpi = 50
    fig = plt.figure(figsize=(330.0/my_dpi, 130.0/my_dpi), dpi=my_dpi)
    
    img = Image.objects.get(pk=image_pk)    
    f = BytesIO()
    try:
        glass_brain = plot_glass_brain(img.file.path, figure=fig)
        glass_brain.savefig(f, dpi=my_dpi)
    except:
        # Glass brains that do not produce will be given dummy image
        this_path = os.path.abspath(os.path.dirname(__file__))
        f = open(os.path.abspath(os.path.join(this_path,
                                              "static","images","glass_brain_empty.jpg"))) 
        raise
    finally:
        plt.close('all')
        f.seek(0)
        content_file = ContentFile(f.read())
        img.thumbnail.save("glass_brain_%s.jpg" % img.pk, content_file)
        img.save()

# IMAGE TRANSFORMATION ################################################################################

# Save 4mm, brain masked image vector in pkl file in image folder
@shared_task
def save_resampled_transformation_single(pk1, resample_dim=[4, 4, 4]):
    from neurovault.apps.statmaps.models import Image
    from six import BytesIO
    import numpy as np
    import neurovault

    img = get_object_or_404(Image, pk=pk1)
    nii_obj = nib.load(img.file.path)   # standard_mask=True is default
    image_vector = make_resampled_transformation_vector(nii_obj,resample_dim)

    f = BytesIO()
    np.save(f, image_vector)
    f.seek(0)
    content_file = ContentFile(f.read())
    img.reduced_representation.save("transform_%smm_%s.npy" %(resample_dim[0],img.pk), content_file)

    return img


# SIMILARITY CALCULATION ##############################################################################

@shared_task
def run_voxelwise_pearson_similarity(pk1):
    from neurovault.apps.statmaps.models import Image
    
    image = Image.objects.get(pk=pk1)
    #added for improved performance
    if not image.reduced_representation:
        image = save_resampled_transformation_single(pk1)

    # Calculate comparisons for other images, and generate reduced_representation if needed
    imgs = Image.objects.filter(collection__private=False).exclude(pk=pk1)
    comp_qs = imgs.exclude(polymorphic_ctype__model__in=['image','atlas']).order_by('id')
    for comp_img in comp_qs:
        iargs = sorted([comp_img.pk,pk1]) 
        if comp_img.is_thresholded == False:
            save_voxelwise_pearson_similarity.apply_async(iargs)  # Default uses reduced_representaion, reduced_representation = True


@shared_task
def save_voxelwise_pearson_similarity(pk1,pk2,resample_dim=[4,4,4],reduced_representaion=True):
    if reduced_representaion == False:
        save_voxelwise_pearson_similarity_resample(pk1,pk2,resample_dim)
    else:
        save_voxelwise_pearson_similarity_reduced_representation(pk1,pk2)


# Calculate pearson correlation from pickle files with brain masked vectors of image values
def save_voxelwise_pearson_similarity_reduced_representation(pk1, pk2):
    from neurovault.apps.statmaps.models import Similarity, Comparison
    import numpy as np

    # We will always calculate Comparison 1 vs 2, never 2 vs 1
    if pk1 != pk2:
        sorted_images = get_images_by_ordered_id(pk1, pk2)
        image1 = sorted_images[0]
        image2 = sorted_images[1]
        pearson_metric = Similarity.objects.get(similarity_metric="pearson product-moment correlation coefficient",
                                                transformation="voxelwise")
    
        # Make sure we have a transforms for pks in question
        if not image1.reduced_representation:
            image1 = save_resampled_transformation_single(pk1) # cannot run this async

        if not image2.reduced_representation:
            image2 = save_resampled_transformation_single(pk2) # cannot run this async

        # Load image pickles
        image_vector1 = np.load(image1.reduced_representation.file)
        image_vector2 = np.load(image2.reduced_representation.file)

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
            print "Comparison returned NaN."
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
        images_resamp, _ = resample_images_ref(images=image_paths, 
                                               reference=reference, 
                                               interpolation="continuous",
                                               resample_dim=resample_dim)
        # resample_images_ref will "squeeze" images, but we should keep error here for now
        for image_nii, image_obj in zip(images_resamp, [image1, image2]):
            if len(numpy.squeeze(image_nii.get_data()).shape) != 3:
                raise Exception("Image %s (id=%d) has incorrect number of dimensions %s"%(image_obj.name, 
                                                                                          image_obj.id, 
                                                                                          str(image_nii.get_data().shape)))

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


# COGNITIVE ATLAS
###########################################################################
def repopulate_cognitive_atlas(CognitiveAtlasTask=None,CognitiveAtlasContrast=None):
    if CognitiveAtlasTask==None:
        from neurovault.apps.statmaps.models import CognitiveAtlasTask
    if CognitiveAtlasContrast==None:
        from neurovault.apps.statmaps.models import CognitiveAtlasContrast
    
    import json, os
    from cognitiveatlas.api import get_task
    tasks = get_task()

    # Update tasks
    for t in range(0,len(tasks.json)):
        task = tasks.json[t]
        print "%s of %s" %(t,len(tasks.json)) 
        if tasks.json[t]["name"]:
            task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=task["id"],defaults={"name":task["name"]})
            task.save()
            if tasks.json[t]["id"]:
                task_details = get_task(id=tasks.json[t]["id"])
                if task_details.json[0]["contrasts"]:
                    print "Found %s contrasts!" %(len(task_details.json[0]["contrasts"]))
                    for contrast in task_details.json[0]["contrasts"]:
                        contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id=contrast["id"], 
                                                                                      defaults={"name":contrast["contrast_text"],
                                                                                      "task":task})
                        contrast.save() 



# HELPER FUNCTIONS ####################################################################################

'''Return list of Images sorted by the primary key'''
def get_images_by_ordered_id(pk1, pk2):
    from neurovault.apps.statmaps.models import Image
    image1 = get_object_or_404(Image, pk=pk1)
    image2 = get_object_or_404(Image, pk=pk2)
    return sorted([image1,image2], key=lambda x: x.pk)
