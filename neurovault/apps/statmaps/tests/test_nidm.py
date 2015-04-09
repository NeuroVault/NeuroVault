from django.test import TestCase, Client
from neurovault.apps.statmaps.models import Collection,User
import tempfile
import os
import shutil
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.nidm_results import NIDMUpload
from neurovault.apps.statmaps.forms import NIDMResultsForm
from .utils import clearTestMediaRoot


class NIDMResultsTest(TestCase):

    def setUp(self):
        testpath = os.path.abspath(os.path.dirname(__file__))
        self.files = {
            'fsl_nidm': {
                'file': os.path.join(testpath,'test_data/nidm/fsl.nidm.zip'),
                'output_row': {'type': u'TStatistic','name': u'Statistic Map: Generation',},
                'num_statmaps': 2,
            },
            'two_contrasts': {
                'file': os.path.join(testpath,'test_data/nidm/two_contrasts.nidm.zip'),
                'output_row': {'type': u'FStatistic', 'name': 'Statistic Map: Generation FStatistic',},
                'num_statmaps': 6,
            },
            'spm_example': {
                'file': os.path.join(testpath,'test_data/nidm/spm_example.nidm.zip'),
                'output_row': {'type': u'TStatistic', 'name': u'Statistic Map: passive listening > rest', },
                'num_statmaps': 1,
            },
            # case for a zip with no enclosed directory
            'spm_nosubdir': {
                'file': os.path.join(testpath,'test_data/nidm/spm_nosubdir.nidm.zip'),
                'output_row': {'type': u'FStatistic', 'name': u'Statistic Map: Generation FStatistic',},
                'num_statmaps': 6,
            },
        }

        self.failing_files = {
            'spm_bad_ttl':   os.path.join(testpath,'test_data/nidm/spm_bad_ttl.nidm.zip'),
        }

        self.tmpdir = tempfile.mkdtemp()
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user)
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearTestMediaRoot()

    def testParseNIDMZip(self):
        contrasts = {}
        turtles = {}  # I like turtles.
        uploads = {}
        statmaps = {}

        for name in self.files:
            uploads[name] = NIDMUpload(self.files[name]['file'],tmp_dir=self.tmpdir,load=False)
            turtles[name] = uploads[name].parse_metafiles(extract_ttl=True)
            contrasts[name] = uploads[name].parse_contrasts()
            statmaps[name] = uploads[name].get_statmaps()

        """
        assert known bad file throws parsing error
        """
        with self.assertRaises(NIDMUpload.ParseException):
            print NIDMUpload(self.failing_files['spm_bad_ttl'])

        """
        assert output matches expected output
        """
        for name, info in self.files.items():
            first_map = sorted(statmaps[name])[0]
            for field in 'name','type':
                self.assertEquals(first_map[field],info['output_row'][field])
            self.assertEquals(len(statmaps[name]), info['num_statmaps'])

    def testUploadNIDMZip(self):

        for name, info in self.files.items():
            zip_file = open(info['file'], 'rb')
            post_dict = {
                'name': name,
                'description':'{0} upload test'.format(name),
                'collection':self.coll.pk,
            }

            fname = os.path.basename(info['file'])
            file_dict = {'zip_file': SimpleUploadedFile(fname, zip_file.read())}
            form = NIDMResultsForm(post_dict, file_dict)

            self.assertTrue(form.is_valid())

            nidm = form.save()

            self.assertEquals(len(nidm.nidmresultstatisticmap_set.all()),info['num_statmaps'])

            map_type = info['output_row']['type'][0]
            map_img = nidm.nidmresultstatisticmap_set.filter(map_type=map_type).first()

            self.assertEquals(map_img.name,info['output_row']['name'])
