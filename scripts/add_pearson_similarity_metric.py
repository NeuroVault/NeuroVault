'''
Created on 30 Jan 2015

@author: vsochat
'''
from neurovault.apps.statmaps.models import Similarity, Comparison, Image
from neurovault.apps.statmaps.tasks import save_voxelwise_pearson_similarity, update_voxelwise_pearson_similarity
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
  print "A Similarity Metric has already been defined for %s" %(pearson_metric)
  pass 

# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for image1 in Image.objects.filter(collection__private=False):
  for image2 in Image.objects.filter(collection__private=False):
    if image1.pk < image2.pk:
      print "Calculating pearson similarity for images %s and %s" %(image1,image2)
      save_voxelwise_pearson_similarity(image1.pk,image2.pk)

# After this we should have ((N*N)-N)/2
# N^2 is N combinations total for N objects
# we subtract N to account for diagonal
# we divide by 2 to take order into account

M = len(Comparison.objects.all())
N = len(Image.objects.filter(collection__private=False))
we_should_have = ((N*N)-N)/2
print "We have %s comparisons after generating all of them, we should have %s" %(M,we_should_have)

image1 = Image.objects.filter(pk=1)[0]
image2 = Image.objects.filter(pk=2)[0]

# Update a similarity, we should still have N
update_voxelwise_pearson_similarity(image1.pk,image2.pk)

M = len(Comparison.objects.all())
print "We have %s comparisons after updating one, we should have %s." %(M,we_should_have)

# Try adding it again, we should still have N
save_voxelwise_pearson_similarity(image1.pk,image2.pk)

M = len(Comparison.objects.all())
print "We have %s comparisons after trying to add one a second time, we should have %s." %(M,we_should_have)
