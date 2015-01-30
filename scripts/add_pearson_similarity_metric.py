'''
Created on 30 Jan 2015

@author: vsochat
'''
from neurovault.apps.statmaps.models import Similarity, Comparison, Image
from neurovault.apps.statmaps.tasks import calculate_voxelwise_pearson_similarity


# First create the image similarity metric
pearson_metric = Similarity(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")
pearson_metric.save()

# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for image1 in Image.objects.filter(collection__private=False):
  for image2 in Image.objects.filter(collection__private=False):
    if image1.pk < image2.pk:
      try:
        calculate_voxelwise_pearson_similarity(image1.pk,image2.pk)
        print "Calculated voxelwise pearson comparison for %s and %s successfully!" %(image1,image2)
      except:
        print "Voxelwise pearson comparison for %s and %s already exists!" %(image1,image2)

