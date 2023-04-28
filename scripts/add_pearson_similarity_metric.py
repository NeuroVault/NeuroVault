'''
Created on 30 Jan 2015

@author: vsochat
'''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Similarity, Comparison, Image
from neurovault.apps.statmaps.tasks import save_voxelwise_pearson_similarity
from django.db import IntegrityError
import errno

# First create the image similarity metric
pearson_metric = Similarity(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")
try:
  pearson_metric.save()
except IntegrityError as exc:
  print("A Similarity Metric has already been defined for %s" %(pearson_metric))
  pass 

# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for image1 in Image.objects.filter(collection__private=False):
  for image2 in Image.objects.filter(collection__private=False):
    if image1.pk < image2.pk:
      print("Calculating pearson similarity for images %s and %s" %(image1,image2))
      save_voxelwise_pearson_similarity(image1.pk,image2.pk)
