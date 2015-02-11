from __future__ import absolute_import
from neurovault.celery import nvcelery as celery_app
import os
import numpy
import pylab as plt
import nibabel as nib
from celery import shared_task
from scipy.stats.stats import pearsonr
from nilearn.plotting import plot_glass_brain
from nilearn.image import resample_img
from django.shortcuts import get_object_or_404


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

        pearson_score = calculate_voxelwise_pearson_similarity(image1, image2, resample_dim)

        try:
            compare = Comparison.objects.get(image1=image1, image2=image2,
                                             similarity_metric=pearson_metric)
        except Comparison.DoesNotExist:
            compare = Comparison(image1=image1, image2=image2, similarity_metric=pearson_metric)

        compare.similarity_score = pearson_score
        compare.save()
        return image1.pk,image2.pk,pearson_score
    else:
        raise Exception("You are trying to compare image with itself!")


# Helper functions
'''Return list of Images sorted by the primary key'''


def get_images_by_ordered_id(pk1, pk2):
    from neurovault.apps.statmaps.models import Image
    image1 = get_object_or_404(Image, pk=pk1)
    image2 = get_object_or_404(Image, pk=pk2)
    return sorted([image1,image2], key=lambda x: x.pk)


'''Calculate a voxelwise pearson correlation via pairwise deletion'''


def calculate_voxelwise_pearson_similarity(image1, image2, resample_dim):

    # Get standard space brain
    reference = os.path.join(
        os.environ['FREESURFER_HOME'], 'subjects', 'fsaverage', 'mri', 'brain.nii.gz')
    image_paths = [image.file.path for image in [image1, image2]]
    images_resamp, reference_resamp = resample_multi_images_ref(
        image_paths, reference, resample_dim)
    
    for image_nii, image_obj in zip(images_resamp, [image1, image2]):
        if len(numpy.squeeze(image_nii.get_data()).shape) != 3:
            raise Exception("Image %s (id=%d) has incorrect number of dimensions %s"%(image_obj.name, image_obj.id, str(image_nii.get_data().shape)))

    # Calculate correlation only on voxels that are in both maps (not zero, and not nan)
    binary_mask = make_binary_deletion_mask(images_resamp)
    image1_res = images_resamp[0]
    image2_res = images_resamp[1]
    

    # Calculate correlation with voxels within mask
    return pearsonr(numpy.squeeze(image1_res.get_data())[binary_mask == 1],
                    numpy.squeeze(image2_res.get_data())[binary_mask == 1])[0]


'''Make a nonzero, non-nan mask for a or or more images (registered, equally sized)'''


def make_binary_deletion_mask(images):

    if isinstance(images, nib.nifti1.Nifti1Image):
        images = [images]
    images_data = [numpy.squeeze(image.get_data()) for image in images]
    mask = numpy.ones(images_data[0].shape)
    for image_data in images_data:
        mask *= (image_data != 0) & ~numpy.isnan(image_data)
    return mask


'''Resample single image to match some other reference (continuous interpolation, not for atlas)'''


def resample_single_img_ref(image, reference):
    return resample_img(image, target_affine=reference.get_affine(), target_shape=reference.get_shape())


'''Resample multiple image to match some other reference (continuous interpolation, not for atlas)'''


def resample_multi_images_ref(images, mask, resample_dim):
    affine = numpy.diag(resample_dim)
    # Prepare the reference
    reference = nib.load(mask)
    reference_resamp = resample_img(reference, target_affine=affine)
    # Resample images to match reference
    if isinstance(images, str):
        images = [images]
    images_resamp = []
    for image in images:
        im = nib.load(image)
        images_resamp.append(resample_single_img_ref(im, reference_resamp))
    return images_resamp, reference_resamp
