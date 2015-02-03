from neurovault.apps.statmaps.tasks import update_voxelwise_pearson_similarity, save_voxelwise_pearson_similarity, get_images_by_ordered_id
from django.shortcuts import get_object_or_404
from neurovault.apps.statmaps.models import Image, Comparison, Similarity
from django.test import TestCase
from django.db import IntegrityError
import errno

class ComparisonTestCase(TestCase):
    def setUp(self):
      pk1 = 1
      pk2 = 2
      print "Setting up voxelwise pearson metric for images %s and %s" %(pk1,pk2)
      image1 = get_object_or_404(Image,pk=pk1)
      image2 = get_object_or_404(Image,pk=pk2)    
      pearson_metric = Similarity(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")

    def test_save_pearson_metric(self):        
        print "Trying to save pearson metric %s..." %(pearson_metric)
        try: pearson_metric.save()
        except IntegrityError as exc:
          print "A Similarity Metric has already been defined for %s" %(pearson_metric)
          pass 

    def test_save_pearson_similarity(self):
        print "Trying to save pearson score for images %s and %s..." %(image1,image2)
        save_voxelwise_pearson_similarity(pk1,pk2)
        
    def test_update_pearson_similarity(self):
        ids = get_images_by_ordered_id([pk1,pk2])
        image1 = ids[0]; image2 = ids[1]
        comparison = Comparison.objects.filter(image1=image1,image2=image2,similarity_metric=pearson_metric)
        print "Voxelwise pearson correlation score for images %s and %s is currently %s" %(image1,image2,comparison[0].similarity_score)
        print "Trying to update pearson score for images %s and %s..." %(image1,image2)
        update_voxelwise_pearson_similarity(pk1,pk2)
