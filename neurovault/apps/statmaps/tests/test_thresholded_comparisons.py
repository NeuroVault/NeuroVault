from neurovault.apps.statmaps.utils import count_existing_comparisons, get_existing_comparisons, count_processing_comparisons
from neurovault.apps.statmaps.models import Image, Comparison, Similarity, User, Collection, StatisticMap
from neurovault.apps.statmaps.tests.utils import save_statmap_form, save_atlas_form
from numpy.testing import assert_array_equal, assert_almost_equal, assert_equal
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.utils import split_4D_to_3D
from neurovault.apps.statmaps.tests.utils import clearDB
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.test import TestCase
import tempfile
import nibabel
import shutil
import errno
import os

class QueryTestCase(TestCase):
    pk1 = None
    pk2 = None
    pk3 = None
    pk4 = None
    pearson_metric = None
    
    def setUp(self):
        print "\n#### TESTING THRESHOLDED IMAGES IN COMPARISON\n"
        self.tmpdir = tempfile.mkdtemp()
        self.app_path = os.path.abspath(os.path.dirname(__file__))
        self.u1 = User.objects.create(username='neurovault')
        self.comparisonCollection = Collection(name='comparisonCollection',owner=self.u1)
        self.comparisonCollection.save()
        
        # Image 1 is an atlas
        print "Adding atlas image..."
        nii_path = os.path.join(self.app_path,"test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz")
        xml_path = os.path.join(self.app_path,"test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml")
        image1 = save_atlas_form(nii_path=nii_path,xml_path=xml_path,collection = self.comparisonCollection)
        self.pk1 = image1.id

        # Image 2 is a statistical map
        print "Adding statistical map..."
        image_path = os.path.join(self.app_path,'test_data/statmaps/beta_0001.nii.gz')
        image2 = save_statmap_form(image_path=image_path,collection = self.comparisonCollection)
        self.pk2 = image2.id
        
        # Image 3 is a thresholded statistical map
        print "Adding thresholded statistical map..."
        image_paths = [os.path.join(self.app_path,'test_data/statmaps/box_0b_vs_1b.img'),
                       os.path.join(self.app_path,'test_data/statmaps/box_0b_vs_1b.hdr')]
        image3 = save_statmap_form(image_path=image_paths, collection = self.comparisonCollection,ignore_file_warning=True)
        self.pk3 = image3.id

        # Create similarity object
        Similarity.objects.update_or_create(similarity_metric="pearson product-moment correlation coefficient",
                                         transformation="voxelwise",
                                         metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                         transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")
        self.pearson_metric = Similarity.objects.filter(similarity_metric="pearson product-moment correlation coefficient",
                                         transformation="voxelwise",
                                         metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                         transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")        
        
    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()

    def test_thresholded_image_comparison(self):
        # There should be no comparisons for a thresholded image
        print "testing comparisons for thresholded images"
        assert_equal(0,count_existing_comparisons(self.pk3))

        # There should be no comparisons for an atlas
        print "testing comparisons for atlases"
        assert_equal(0,count_existing_comparisons(self.pk1))

        # There should be no comparisons for statistical map because no other statistical maps
        print "testing comparisons for statistical maps"
        assert_equal(0,count_existing_comparisons(self.pk2))

        # Add another statistical map   
        image_path = os.path.join(self.app_path,'test_data/statmaps/motor_lips.nii.gz')
        image4 = save_statmap_form(image_path=image_path,collection = self.comparisonCollection)
        self.pk4 = image4.id
          
        # There should STILL be no comparisons for a thresholded image
        print "testing comparisons for thresholded images"
        assert_equal(0,count_existing_comparisons(self.pk3))

        # There should STILL be no comparisons for an of the atlas
        print "testing comparisons for atlases"
        assert_equal(0,count_existing_comparisons(self.pk1))

        # There should now be one comparison for each statistical map, two total
        print "testing comparisons for statistical maps"
        print Comparison.objects.all()
        assert_equal(1,count_existing_comparisons(self.pk2))
        assert_equal(1,count_existing_comparisons(self.pk4))
        assert_equal(1,count_existing_comparisons())

        # This is the call that find_similar users to get images
        comparisons =  get_existing_comparisons(self.pk4)
        for comp in comparisons:
            pk1=comp.image1.pk
            pk2=comp.image2.pk          
            im1 = Image.objects.get(pk=pk1)
            im2 = Image.objects.get(pk=pk2)
            assert_equal(im1.is_thresholded,False)
            assert_equal(im2.is_thresholded,False)
