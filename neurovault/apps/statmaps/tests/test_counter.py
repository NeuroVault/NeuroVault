import json
import os.path
import time
from .utils import clearDB
from operator import itemgetter
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.utils import count_images_processing
from neurovault.apps.statmaps.forms import NIDMResultsForm
from numpy.testing import assert_array_equal, assert_almost_equal, assert_equal
from neurovault.apps.statmaps.models import Atlas, Collection, Image,StatisticMap

class Test_Counter(TestCase):
    def setUp(self):
        print "\n\n### TESTING COUNTER ###"
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1',owner=self.user)
        self.Collection1.save()


    def tearDown(self):
        clearDB()

    # An empty database should have zero images still processing
    def test_empty_database(self):
        images_processing = count_images_processing()
        print "%s images processing [should be 0]" %(images_processing)
        assert_equal(images_processing,0)

    def test_statmaps_processing(self):

        print "\nTesting Counter - added statistic maps ###" 
        Image1 = StatisticMap(name='Image1', collection=self.Collection1, file='motor_lips.nii.gz', map_type="Z")
        Image1.file = SimpleUploadedFile('motor_lips.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/motor_lips.nii.gz')).read())
        Image1.save()
        images_processing = count_images_processing()
        print "%s images processing [should be 1]" %(images_processing)
        assert_equal(images_processing,1)
        
        Image2 = StatisticMap(name='Image2', collection=self.Collection1, file='beta_0001.nii.gz', map_type="Other")
        Image2.file = SimpleUploadedFile('beta_0001.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/beta_0001.nii.gz')).read())
        Image2.save()
        
        # Give 5 seconds to process
        time.sleep(5)
        images_processing = count_images_processing()
        print "%s images processing" %(images_processing)
        assert_equal(images_processing,0)


    # Atlas should not be counted
    def test_adding_atlas(self):

        unorderedAtlas = Atlas(name='unorderedAtlas', description='',collection=self.Collection1)
        unorderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        unorderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(self.test_path,'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        unorderedAtlas.save()
        images_processing = count_images_processing()
        print "\nTesting Counter - added an atlas ###" 
        print "%s images processing" %(images_processing)
        assert_equal(images_processing,0)

    def test_adding_nidm(self):
        # NIDM result should not be counted
        zip_file = open(os.path.join(self.test_path,'test_data/nidm/fsl.nidm.zip'), 'rb')
        post_dict = {
            'name': 'fsl_nidm',
            'description':'{0} upload test'.format('fsl_nidm'),
            'collection':self.Collection1.pk}
        fname = os.path.basename(os.path.join(self.test_path,'test_data/nidm/fsl.nidm.zip'))
        file_dict = {'zip_file': SimpleUploadedFile(fname, zip_file.read())}
        zip_file.close()
        form = NIDMResultsForm(post_dict, file_dict)
        nidm = form.save()
        images_processing = count_images_processing()
        print "\nTesting Counter - added nidm result ###" 
        print "%s images processing" %(images_processing)
        assert_equal(images_processing,0)


     
