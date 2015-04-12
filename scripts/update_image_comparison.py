'''
Created on 10 April 2015

@author: vsochat

Update database with image transformations
'''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Similarity, Comparison, Image
from neurovault.apps.statmaps.tasks import save_voxelwise_pearson_similarity
from django.db import IntegrityError
import errno

# Images should have the "transform" field after applying migrations (I think)

# First create/update the image similarity metric
pearson_metric = Similarity.objects.update_or_create(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")

# Delete all old comparisons
all_comparisons = Comparison.objects.all()
all_comparisons.delete()

all_images = Image.objects.filter(collection__private=False and is_thresholded == False).exclude(polymorphic_ctype__model__in=['image','atlas'])

# Filter down to images that are not private, not thresholded
# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for image1 in all_images:
  for image2 in all_images:
    if image1.pk < image2.pk:
      print "Calculating pearson similarity for images %s and %s" %(image1,image2)
      save_voxelwise_pearson_similarity(image1.pk,image2.pk)
