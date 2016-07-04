import nibabel
import numpy
import os
import shutil
import tempfile
from django.test import TestCase
from numpy.testing import assert_almost_equal, assert_equal

from neurovault.apps.statmaps.models import Comparison, Similarity, User, Collection, Image
from neurovault.apps.statmaps.tasks import save_voxelwise_pearson_similarity, get_images_by_ordered_id, save_resampled_transformation_single
from neurovault.apps.statmaps.tests.utils import clearDB, save_statmap_form
from neurovault.apps.statmaps.utils import split_4D_to_3D, get_similar_images


class ComparisonTestCase(TestCase):
    pk1 = None
    pk1_copy = None
    pk2 = None
    pk3 = None
    pearson_metric = None
    pknan = None
    
    def setUp(self):
        print "Preparing to test image comparison..."
        self.tmpdir = tempfile.mkdtemp()
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.u1 = User.objects.create(username='neurovault')
        self.comparisonCollection1 = Collection(name='comparisonCollection1', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00008')
        self.comparisonCollection1.save()
        self.comparisonCollection2 = Collection(name='comparisonCollection2', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00009')
        self.comparisonCollection2.save()
        self.comparisonCollection3 = Collection(name='comparisonCollection3', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00010')
        self.comparisonCollection3.save()
        self.comparisonCollection4 = Collection(name='comparisonCollection4', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00011')
        self.comparisonCollection4.save()
        self.comparisonCollection5 = Collection(name='comparisonCollection5', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00012')
        self.comparisonCollection5.save()


        image1 = save_statmap_form(image_path=os.path.join(app_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'),
                              collection=self.comparisonCollection1,
                              image_name = "image1",
                              ignore_file_warning=True)
        self.pk1 = image1.id
                
        # Image 2 is equivalent to 1, so pearson should be 1.0
        image2 = save_statmap_form(image_path=os.path.join(app_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'),
                              collection=self.comparisonCollection2,
                              image_name = "image1_copy",
                              ignore_file_warning=True)
        self.pk1_copy = image2.id
        
        # "Bricks" images
        bricks = split_4D_to_3D(nibabel.load(os.path.join(app_path,'test_data/TTatlas.nii.gz')),tmp_dir=self.tmpdir)
        image3 = save_statmap_form(image_path=bricks[0][1],collection=self.comparisonCollection3,image_name="image2",ignore_file_warning=True)
        self.pk2 = image3.id     
        image4 = save_statmap_form(image_path=bricks[1][1],collection=self.comparisonCollection4,image_name="image3",ignore_file_warning=True)
        self.pk3 = image4.id

        # This last image is a statmap with NaNs to test that transformation doesn't eliminate them
        image_nan = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/motor_lips_nan.nii.gz'),
                                      collection=self.comparisonCollection5,
                                      image_name = "image_nan",
                                      ignore_file_warning=True)
        self.pknan = image_nan.id
                        
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


    # When generating transformations for comparison, NaNs should be maintained in the map 
    # (and not replaced with zero / interpolated to "almost zero" values.
    def test_interpolated_transform_zeros(self): 
        img = save_resampled_transformation_single(self.pknan, resample_dim=[4, 4, 4])
        data = numpy.load(img.reduced_representation.file)
        print "Does transformation calculation maintain NaN values?: %s" %(numpy.isnan(data).any())
        assert_equal(numpy.isnan(data).any(),True)

    def test_save_pearson_similarity(self):
        # Should be 1
        print "Testing %s vs. %s: same images, different ids" %(self.pk1,self.pk1_copy)
        save_voxelwise_pearson_similarity(self.pk1,self.pk1_copy)
 
        # Should not be saved
        with self.assertRaises(Exception):
            print "Testing %s vs. %s: same pks, success is raising exception" %(self.pk1,self.pk1)
            save_voxelwise_pearson_similarity(self.pk1,self.pk1)

        print "Testing %s vs. %s, different image set 1" %(self.pk1,self.pk2)
        save_voxelwise_pearson_similarity(self.pk1,self.pk2)

        print "Testing %s vs. %s, different image set 2" %(self.pk2,self.pk3)
        save_voxelwise_pearson_similarity(self.pk2,self.pk3)

        # Should not exist
        print "Success for this test means there are no comparisons returned."
        image1, image1_copy = get_images_by_ordered_id(self.pk1, self.pk1)
        comparison = Comparison.objects.filter(image1=image1,image2=image1_copy,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 0)

        # Should be 1        
        print "Success for this test means a score of 1.0"
        image1, image2 = get_images_by_ordered_id(self.pk1, self.pk1_copy)
        comparison = Comparison.objects.filter(image1=image1,image2=image2,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        self.assertAlmostEqual(comparison[0].similarity_score, 1.0)

        print "Success for the remaining tests means a specific comparison score."
        image1, image2 = get_images_by_ordered_id(self.pk1, self.pk2)
        comparison = Comparison.objects.filter(image1=image1,image2=image2,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        print comparison[0].similarity_score
        assert_almost_equal(comparison[0].similarity_score, 0.214495998015581,decimal=5)

        image2, image3 = get_images_by_ordered_id(self.pk3, self.pk2)
        comparison = Comparison.objects.filter(image1=image2,image2=image3,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        print comparison[0].similarity_score
        assert_almost_equal(comparison[0].similarity_score, 0.312548260435768,decimal=5)
        
    def test_private_to_public_switch(self):
        private_collection1 = Collection(name='privateCollection1',owner=self.u1, private=True,
                                        DOI='10.3389/fninf.2015.00099')
        private_collection1.save()
        private_collection2 = Collection(name='privateCollection2',owner=self.u1, private=True,
                                        DOI='10.3389/fninf.2015.00089')
        private_collection2.save()

        app_path = os.path.abspath(os.path.dirname(__file__))
        private_image1 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/all.nii.gz'),
                                           collection=private_collection1,
                                           image_name = "image1")
        private_image2 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/motor_lips.nii.gz'),
                                           collection=private_collection2,
                                           image_name = "image2")
        comparison = Comparison.objects.filter(image1=private_image1,image2=private_image2)
        self.assertEqual(len(comparison), 0)
        
        print "before private: %s"%Comparison.objects.all().count()
        private_collection1 = Collection.objects.get(pk=private_collection1.pk)
        private_collection1.private = False
        private_collection1.save()
        private_collection2 = Collection.objects.get(pk=private_collection2.pk)
        private_collection2.private = False
        private_collection2.save()
        print "after private: %s"%Comparison.objects.all().count()
        print private_collection1.basecollectionitem_set.instance_of(Image).all()
        comparison = Comparison.objects.filter(image1=private_image1,image2=private_image2)
        self.assertEqual(len(comparison), 1)

    def test_add_DOI(self): # these collections are actually not private
        private_collection1 = Collection(name='privateCollection1', owner=self.u1, private=False)
        private_collection1.save()
        private_collection2 = Collection(name='privateCollection2', owner=self.u1, private=False)
        private_collection2.save()

        app_path = os.path.abspath(os.path.dirname(__file__))
        private_image1 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/all.nii.gz'),
                                           collection=private_collection1,
                                           image_name = "image1")
        private_image2 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/motor_lips.nii.gz'),
                                           collection=private_collection2,
                                           image_name = "image2")
        comparison = Comparison.objects.filter(image1=private_image1,image2=private_image2)
        self.assertEqual(len(comparison), 0)

        print "without DOI: %s"%Comparison.objects.all().count()
        private_collection = Collection.objects.get(pk=private_collection1.pk)
        private_collection.DOI = '10.3389/fninf.2015.00020'
        private_collection.save()
        print "with DOI: %s"%Comparison.objects.all().count()
        print private_collection.basecollectionitem_set.instance_of(Image).all()
        comparison = Comparison.objects.filter(image1=private_image1,image2=private_image2)
        self.assertEqual(len(comparison), 1)

    def test_get_similar_images(self):
        collection1 = Collection(name='Collection1', owner=self.u1,
                                 DOI='10.3389/fninf.2015.00099')

        collection1.save()
        collection2 = Collection(name='Collection2', owner=self.u1,
                                 DOI='10.3389/fninf.2015.00089')
        collection2.save()

        app_path = os.path.abspath(os.path.dirname(__file__))
        image1 = save_statmap_form(image_path=os.path.join(app_path, 'test_data/statmaps/all.nii.gz'),
                                           collection=collection1,
                                           image_name="image1")
        image2 = save_statmap_form(image_path=os.path.join(app_path, 'test_data/statmaps/all.nii.gz'),
                                           collection=collection2,
                                           image_name="image2")


        similar_images = get_similar_images(int(image1.pk))

        print "Success for this test means the pandas DataFrame shows the copy in first position with score of 1"
        self.assertEqual(similar_images['image_id'][0], int(image2.pk))
        self.assertEqual(similar_images['score'][0], 1)
