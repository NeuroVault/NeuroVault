import nibabel
import numpy
import os
import shutil
import tempfile
from django.test import TestCase
from numpy.testing import assert_almost_equal, assert_equal

from neurovault.apps.statmaps.models import User, Collection, Image
from neurovault.apps.statmaps.tasks import delete_vector_engine, get_images_by_ordered_id, \
    save_resampled_transformation_single
from neurovault.apps.statmaps.tests.utils import clearDB, save_statmap_form
from neurovault.apps.statmaps.utils import get_existing_comparisons
from neurovault.apps.statmaps.management.commands.rebuild_engine import Command

class ComparisonTestCase(TestCase):
    pk1 = None
    pk1_copy = None
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


        image1 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/all.nii.gz'),
                              collection=self.comparisonCollection1,
                              image_name = "image1",
                              ignore_file_warning=True)
        self.pk1 = image1.id
                
        image2 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/all.nii.gz'),
                              collection=self.comparisonCollection2,
                              image_name = "image1_copy",
                              ignore_file_warning=True)
        self.pk1_copy = image2.id

        com = Command()
        com.handle()

        # This last image is a statmap with NaNs to test that transformation doesn't eliminate them
        image_nan = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/motor_lips_nan.nii.gz'),
                                      collection=self.comparisonCollection5,
                                      image_name = "image_nan",
                                      ignore_file_warning=True)
        self.pknan = image_nan.id

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()

    # When generating transformations for comparison, NaNs should be maintained in the map
    # (and not replaced with zero / interpolated to "almost zero" values.
    def test_interpolated_transform_zeros(self):
        img = save_resampled_transformation_single(self.pknan, resample_dim=[16, 16, 16])
        data = numpy.load(img.reduced_representation.file)
        print "Does transformation calculation maintain NaN values?: %s" %(numpy.isnan(data).any())
        assert_equal(numpy.isnan(data).any(),True)

    def test_private_to_public_switch(self):
        # Clean Engine
        for image in Image.objects.all():
            delete_vector_engine(image.pk)

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
        comparisons = get_existing_comparisons(private_image1.pk)
        self.assertEqual(len(comparisons), 0)

        print "before private: %s"%len(comparisons)
        private_collection1 = Collection.objects.get(pk=private_collection1.pk)
        private_collection1.private = False
        private_collection1.save()
        private_collection2 = Collection.objects.get(pk=private_collection2.pk)
        private_collection2.private = False
        private_collection2.save()
        comparisons = get_existing_comparisons(private_image1.pk)
        print "after private: %s"%len(comparisons)
        self.assertEqual(len(comparisons), 1)

    def test_add_DOI(self):
        # Clean Engine
        for image in Image.objects.all():
            delete_vector_engine(image.pk)

        collection1 = Collection(name='Collection1', owner=self.u1, private=False)
        collection1.save()
        collection2 = Collection(name='Collection2', owner=self.u1, private=False)
        collection2.save()

        app_path = os.path.abspath(os.path.dirname(__file__))
        image1 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/all.nii.gz'),
                                   collection=collection1,
                                   image_name = "image1")
        image2 = save_statmap_form(image_path=os.path.join(app_path,'test_data/statmaps/motor_lips.nii.gz'),
                                   collection=collection2,
                                   image_name = "image2")
        comparisons = get_existing_comparisons(image1.pk)
        self.assertEqual(len(comparisons), 0)

        print "without DOI: %s"%len(comparisons)
        collection = Collection.objects.get(pk=collection1.pk)
        collection.DOI = '10.3389/fninf.2015.00020'
        collection.save()
        collection = Collection.objects.get(pk=collection2.pk)
        collection.DOI = '10.3389/fninf.2015.00030'
        collection.save()
        comparisons = get_existing_comparisons(image1.pk)
        print "with DOI: %s"%len(comparisons)
        self.assertEqual(len(comparisons), 1)

    def test_get_existing_comparisons(self):
        # Clean Engine
        for image in Image.objects.all():
            delete_vector_engine(image.pk)

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

        image3 = save_statmap_form(image_path=os.path.join(app_path, 'test_data/statmaps/motor_lips.nii.gz'),
                                   collection=collection2,
                                   image_name="image2")

        comparisons = get_existing_comparisons(int(image1.pk))

        results = zip(*comparisons)[1][1:]
        scores = zip(*comparisons)[2][1:]

        print "Success for this test means showing the copy in first position with score of 0"
        self.assertEqual(results[0], int(image2.pk))
        self.assertEqual(scores[0], 0)

        print "Success for this test means showing the other image in second position with score of 1.16"
        self.assertEqual(results[1], int(image3.pk))
        assert_almost_equal(scores[1], 1.1621980949117918, decimal=5)
