from __future__ import absolute_import
from neurovault.celery import nvcelery as celery_app
from celery import shared_task
from celery.decorators import periodic_task
from nilearn.plotting import plot_glass_brain
from neurovault.settings import PRIVATE_MEDIA_ROOT
import os
import numpy
import pandas as pd
import nibabel as nib
from nilearn.image import resample_img
import pylab as plt


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
def make_correlation_df(resample_dim=[4, 4, 4], pkl_path=None):
    from neurovault.apps.statmaps.models import Image
    if not pkl_path:
        pkl_path = os.path.join(PRIVATE_MEDIA_ROOT, 'matrices/pearson_corr.pkl')
    # Get standard space brain
    reference = os.path.join(os.environ['FREESURFER_HOME'],
                             'subjects', 'fsaverage', 'mri', 'brain.nii.gz')
    public_images = Image.objects.filter(collection__private=False)
    # Get all image paths
    image_paths = [image.file.path for image in public_images]
    images_resamp, reference_resamp = resample_multi_images_ref(
        image_paths, reference, resample_dim)
    # Read into pandas data frame
    corr_df = pd.DataFrame()
    row_count = 0
    for image in images_resamp:
        corr_df[row_count] = image.get_data().flatten()
        row_count = row_count + 1
    corr_df = corr_df.corr(method="pearson")
    image_pks = [image.pk for image in public_images]
    corr_df.columns = image_pks
    corr_df.index = image_pks
    if not os.path.exists(os.path.join(PRIVATE_MEDIA_ROOT, 'matrices')):
        os.mkdir(os.path.join(PRIVATE_MEDIA_ROOT, 'matrices'))
    corr_df.to_pickle(pkl_path)


# Helper functions
'''
Resample single image to match some other reference (continuous interpolation, not for atlas)
'''


def resample_single_img_ref(image, reference):
    return resample_img(image, target_affine=reference.get_affine(),
                        target_shape=reference.get_shape())

'''
Resample multiple image to match some other reference (continuous interpolation, not for atlas)
'''


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
