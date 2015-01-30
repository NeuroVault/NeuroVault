from __future__ import absolute_import

import os
import numpy
import pandas as pd
import neurovault
import pylab as plt
import nibabel as nib
from celery import shared_task
from scipy.stats.stats import pearsonr
from nilearn.plotting import plot_glass_brain
from nilearn.image import resample_img
from django.shortcuts import get_object_or_404
from neurovault.apps.statmaps.models import Image, Similarity, Comparison


@shared_task
def generate_glassbrain_image(nifti_file,pk):
  nifti_file = str(nifti_file)
  png_img_name = "glass_brain_%s.png" % pk
  png_img_path = os.path.join(os.path.split(nifti_file)[0],png_img_name)
  glass_brain = plot_glass_brain(nifti_file)
  glass_brain.savefig(png_img_path)
  plt.close('all')


@shared_task
def make_correlation_df(resample_dim=[4,4,4],pkl_path=None):
  if not pkl_path:
    pkl_path = os.path.abspath(os.path.join(neurovault.settings.PRIVATE_MEDIA_ROOT,'matrices/pearson_corr.pkl'))
  # Get standard space brain
  reference = os.path.join(os.environ['FREESURFER_HOME'],'subjects', 'fsaverage', 'mri', 'brain.nii.gz')
  public_images = Image.objects.filter(collection__private=False)
  # Get all image paths
  image_paths = [image.file.path for image in public_images]
  images_resamp, reference_resamp = resample_multi_images_ref(image_paths,reference,resample_dim)
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
  if not os.path.exists(os.path.join(neurovault.settings.PRIVATE_MEDIA_ROOT,'matrices')):
      os.mkdir(os.path.join(neurovault.settings.PRIVATE_MEDIA_ROOT,'matrices'))
  corr_df.to_pickle(pkl_path)


@shared_task
def calculate_voxelwise_pearson_similarity(pk1,pk2,resample_dim=[4,4,4]):
  image1 = get_object_or_404(Image, pk=pk1)
  image2 = get_object_or_404(Image, pk=pk2)
 
  # Sort images by the key (I'm sure there is a better way to do this)
  # We will always calculate Comparison 1 vs 2, never 2 vs 1
  images = dict()
  images[image1.pk] = image1
  images[image2.pk] = image2
  inputs = [] 
  for pks,image in images.iteritems():
    inputs.append(image)
  
  # Now image 1 and 2 are ordered by the primary keys
  image1 = inputs[0]; image2 = inputs[1]

  # Get standard space brain
  reference = os.path.join(os.environ['FREESURFER_HOME'],'subjects', 'fsaverage', 'mri', 'brain.nii.gz')
  image_paths = [image.file.path for image in inputs]
  images_resamp, reference_resamp = resample_multi_images_ref(image_paths,reference,resample_dim)

  # Calculate pearson correlation
  corr_df = pd.DataFrame()
  corr_df[0] = images_resamp[0].get_data().flatten()
  corr_df[1] = images_resamp[1].get_data().flatten()
  pearson_score = corr_df.corr(method="pearson")[1][0]

  # create new Comparison with the voxelwise pearson similarity metric
  pearson_metric = Similarity.objects.filter(similarity_metric="pearson product-moment correlation coefficient",transformation="voxelwise")
  pearson_comparison = Comparison(image1=image1,
                                  image2=image2,
                                  similarity_metric=pearson_metric[0],
                                  similarity_score=pearson_score)
  pearson_comparison.save()


# Helper functions
'''Resample single image to match some other reference (continuous interpolation, not for atlas)'''
def resample_single_img_ref(image,reference):
  return resample_img(image, target_affine=reference.get_affine(), target_shape=reference.get_shape())

'''Resample multiple image to match some other reference (continuous interpolation, not for atlas)'''
def resample_multi_images_ref(images,mask,resample_dim):
  affine = numpy.diag(resample_dim)
  # Prepare the reference
  reference = nib.load(mask)
  reference_resamp = resample_img(reference, target_affine=affine)
  # Resample images to match reference
  if isinstance(images,str): images = [images]
  images_resamp = []
  for image in images:
    im = nib.load(image)
    images_resamp.append(resample_single_img_ref(im,reference_resamp))
  return images_resamp, reference_resamp

