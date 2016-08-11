import os.path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client

from neurovault.apps.statmaps.forms import NIDMResultsForm
from neurovault.apps.statmaps.models import Collection, StatisticMap
from neurovault.apps.statmaps.utils import is_search_compatible,count_existing_comparisons
from .utils import clearDB
from neurovault.apps.statmaps.management.commands.rebuild_engine import Command


class Test_Counter(TestCase):
    def setUp(self):
        print "\n\n### TESTING COUNTER ###"
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neuro_vault')
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
        self.user.delete()

    def counter(self, pk):
        if not is_search_compatible(pk):
            return 0
        else:
            return count_existing_comparisons(pk)

    # Adding a group of NIDM result images
    def test_adding_nidm(self):
        Image2 = StatisticMap(name='Image2', collection=self.Collection1, file='beta_0001.nii.gz', map_type="Other")
        Image2.file = SimpleUploadedFile('beta_0001.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/beta_0001.nii.gz')).read())
        Image2.save()

        # Build Engine, with at least 1 image
        com = Command()
        com.handle()


        # TODO: should be NIDM image comparable??

        # zip_file = open(os.path.join(self.test_path,'test_data/nidm/spm_example.nidm.zip'), 'rb')
        # post_dict = {
        #     'name': 'spm_nidm',
        #     'description':'{0} upload test'.format('spm_example'),
        #     'collection':self.Collection2.pk}
        # fname = os.path.basename(os.path.join(self.test_path,'test_data/nidm/spm_example.nidm.zip'))
        # file_dict = {'zip_file': SimpleUploadedFile(fname, zip_file.read())}
        # zip_file.close()
        # form = NIDMResultsForm(post_dict, file_dict)
        # # Transforms should be generated synchronously
        # nidm = form.save()
        # print "\nTesting Counter - added nidm result ###"
        #
        # # We should have 2 images total, so 1 comparison
        # total_comparisons = self.counter(Image2.pk)
        # self.assertEqual(total_comparisons,1)
        
        #Let's add a single subject map - this should not trigger a comparison
        Image2ss = StatisticMap(name='Image2 - single subject', collection=self.Collection3, file='beta_0001.nii.gz', map_type="Other", analysis_level='S')
        Image2ss.file = SimpleUploadedFile('beta_0001.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/beta_0001.nii.gz')).read())
        Image2ss.save()
        total_comparisons = self.counter(Image2ss.pk)
        self.assertEqual(total_comparisons,0)

        # # Make sure there are comparisons in the Engine
        # number_comparisons = self.counter(Image2.pk)
        # print "\n %s comparisons exist after adding NIDM `[should not be 0]" %(number_comparisons)
        # self.assertEqual(number_comparisons > 0,True)
