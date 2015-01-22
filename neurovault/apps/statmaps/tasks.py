from __future__ import absolute_import

import os
from celery import shared_task
from nilearn.plotting import plot_glass_brain

@shared_task
def generate_glassbrain_image(nifti_file,pk):
  nifti_file = str(nifti_file)
  png_img_name = "glass_brain_%s.png" % pk
  png_img_path = os.path.join(os.path.split(nifti_file)[0],png_img_name)
  glass_brain = plot_glass_brain(nifti_file)
  glass_brain.savefig(png_img_path)

@shared_task
def correlation_matrix(pks):
  print "DO CORRELATION"

