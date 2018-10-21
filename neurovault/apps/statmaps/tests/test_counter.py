import os.path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client

from neurovault.apps.statmaps.forms import NIDMResultsForm
from neurovault.apps.statmaps.models import Collection, StatisticMap, Comparison
from neurovault.apps.statmaps.utils import count_processing_comparisons,count_existing_comparisons
from .utils import clearDB


class Test_Counter(TestCase):
    def setUp(self):
        print "\n\n### TESTING COUNTER ###"
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1', owner=self.user,
                                      DOI='10.3389/fninf.2015.00008')
        self.Collection1.save()
        self.Collection2 = Collection(name='Collection2', owner=self.user,
                                      DOI='10.3389/fninf.2015.00009')
        self.Collection2.save()
        self.Collection3 = Collection(name='Collection3', owner=self.user,
                                      DOI='10.3389/fninf.2015.00011')
        self.Collection3.save()


    def tearDown(self):
        clearDB()

    def test_statmaps_processing(self):

        # The counter is the count of the number of images with the field "transform" set to None
        # The field is populated with the file when image comparisons are done, meaning that if there is only one
        # image in the database (case below) we cannot calculate comparisons, and the "transform" field remains none
        # This is currently the only way that we can test the counter, which will be "1" in this case
        print "\nTesting Counter - added statistic maps ###" 
        Image1 = StatisticMap(name='Image1', collection=self.Collection1, file='motor_lips.nii.gz',
                              map_type="Z", analysis_level='G')
        Image1.file = SimpleUploadedFile('motor_lips.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/motor_lips.nii.gz')).read())
        Image1.save()
        images_processing = count_processing_comparisons(Image1.pk)
        print "%s images processing [should be 0]" %(images_processing)
        self.assertEqual(images_processing,0)

        # When we add an image, the comparison will be calculated with image1, and both images transform fields will be populated
        # the counter will be set to 0.  Celery runs in synchronous mode when testing (meaning that jobs are run locally, one
        # after the other, instead of being sent to worker nodes) so there is no way to test submitting a batch of async
        # jobs and watching the "images still processing" counter go from N to 0. There is also no way of arbitrarily
        # setting an image transform field to "None" because on save, all image comparisons are automatically re-calcualted        
        Image2 = StatisticMap(name='Image2', collection=self.Collection2, file='beta_0001.nii.gz',
                              map_type="Other", analysis_level='G')
        Image2.file = SimpleUploadedFile('beta_0001.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/beta_0001.nii.gz')).read())
        Image2.save()
        images_processing = count_processing_comparisons(Image1.pk)
        print "%s images processing [should be 0]" %(images_processing)
        self.assertEqual(images_processing,0)

        # We should have 2 images total, so 1 comparison
        total_comparisons = count_existing_comparisons(Image1.pk)
        self.assertEqual(total_comparisons,1)
