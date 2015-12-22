'''
Created on 10 April 2015

@author: vsochat

Update database with image transformations
'''
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Similarity, Comparison, Image, Collection
from neurovault.apps.statmaps.tasks import run_voxelwise_pearson_similarity

# Images should have the "transform" field after applying migrations (I think)

# First create/update the image similarity metric
pearson_metric = Similarity.objects.update_or_create(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")

# Delete all old comparisons
all_comparisons = Comparison.objects.all().delete()

# Delete all reduced representations
for img in Image.objects.all():
    img.reduced_representation.delete()

# Filter down to images that are not private, not thresholded
# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for collection in Collection.objects.filter(DOI__isnull=False):
    for image in collection.image_set.all():
      print "Calculating pearson similarity for images %s" %image
      run_voxelwise_pearson_similarity.apply_async([image.pk])
