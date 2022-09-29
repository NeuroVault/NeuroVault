import os
import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, RequestFactory
from collections import OrderedDict
import io
import zipfile

from neurovault.apps.statmaps.forms import NIDMResultsForm
from neurovault.apps.statmaps.models import Collection, User
from neurovault.apps.statmaps.nidm_results import NIDMUpload
from neurovault.apps.statmaps.views import download_collection
from neurovault.apps.statmaps.tests.utils import clearDB, save_statmap_form
from neurovault.api.tests.utils import _setup_test_cognitive_atlas

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
NIDM_TEST_FILES = OrderedDict({
    'spm_ds005_sub-01': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/spm_ds005_sub-01.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: neg loss param'},
        'num_statmaps': 1,
    },
    'spm_ds005_group': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/spm_ds005_group.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: neg loss param'},
        'num_statmaps': 1,
    },
    'fsl_ds005_sub-01': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/fsl_ds005_sub-01.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: neg_loss_param'},
        'num_statmaps': 2,
    },
    'fsl_ds005_group': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/fsl_ds005_group.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: group mean'},
        'num_statmaps': 2,
    },
    'fsl_course_av': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/fsl_course_av.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: Visual'},
        'num_statmaps': 4,
    },
    'fsl_course_fluency2': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/fsl_course_fluency2.nidm.zip'),
        'output_row': {'type': 'F',
                       'name': 'Statistic Map: Generation F'},
        'num_statmaps': 12,
    },
    'spm_example': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/spm_example.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: passive listening > rest'},
        'num_statmaps': 1,
    },
    'spm_auditory_v1.2.0': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/auditory.nidm.zip'),
        'output_row': {'type': 'T',
                       'name': 'Statistic Map: passive listening > rest'},
        'num_statmaps': 1,
    },
    'fsl_course_ptt_ac_left': {
        'file': os.path.join(TEST_PATH,
                             'test_data/nidm/fsl_course_ptt_ac_left.nidm.zip'),
        'output_row': {'type': 'F',
                       'name': 'Statistic Map: index F'},
        'num_statmaps': 12,
    },
})


class NIDMResultsTest(TestCase):

    def setUp(self):
        #rdflib required CWD to be real
        os.chdir("/tmp")
        self.files = NIDM_TEST_FILES

        self.failing_files = {
            'spm_bad_ttl': os.path.join(TEST_PATH,
                                        'test_data/nidm/spm_bad_ttl.nidm.zip')
        }

        self.tmpdir = tempfile.mkdtemp()
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user)
        # we us private collection to avoid running the comparisons
        self.coll = Collection(owner=self.user,
                               name="Test Collection",
                               private=True,
                               private_token="XBOLFOFU")
        self.coll.save()

        _setup_test_cognitive_atlas()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()

    def testParseNIDMZip(self):
        contrasts = {}
        turtles = {}  # I like turtles.
        uploads = {}
        statmaps = {}

        for name in self.files:
            uploads[name] = NIDMUpload(
                self.files[name]['file'], tmp_dir=self.tmpdir, load=False)
            turtles[name] = uploads[name].parse_metafiles(extract_ttl=True)
            contrasts[name] = uploads[name].parse_contrasts()
            statmaps[name] = uploads[name].get_statmaps()

        """
        assert known bad file throws parsing error
        """
        for key in self.failing_files:
            with self.assertRaises(NIDMUpload.ParseException):
                print(NIDMUpload(self.failing_files[key]))

        """
        assert output matches expected output
        """
        for name, info in list(self.files.items()):
            print(info)
            print(name)
            for field in 'name', 'type':
                self.assertTrue(info['output_row'][field] in [a[field] for a in statmaps[name]])
            self.assertEqual(len(statmaps[name]), info['num_statmaps'])

    def testUploadNIDMZip(self):

        for name, info in list(self.files.items()):
            zip_file = open(info['file'], 'rb')
            post_dict = {
                'name': name,
                'description': '{0} upload test'.format(name),
                'collection': self.coll.pk,
            }

            fname = os.path.basename(info['file'])
            file_dict = {
                'zip_file': SimpleUploadedFile(fname, zip_file.read())}
            form = NIDMResultsForm(post_dict, file_dict)

            self.assertTrue(form.is_valid())

            nidm = form.save()

            self.assertEqual(len(nidm.nidmresultstatisticmap_set.all()),
                              info['num_statmaps'])

            map_type = info['output_row']['type'][0]
            map_imgs = nidm.nidmresultstatisticmap_set.filter(
                map_type=map_type).all()

            self.assertTrue(info['output_row']['name'] in [m.name for m in map_imgs])


    def testDownloadCollection_NIDM_results(self):

        collection = Collection(owner=self.user, name="Collection2")
        collection.save()

        # Upload NIMDResult zip file
        zip_file = open(os.path.join(TEST_PATH, 'test_data/nidm/auditory.nidm.zip'), 'rb')
        post_dict = {
            'name': 'auditory',
            'description': '{0} upload test'.format('spm_auditory_v1.2.0'),
            'collection': collection.pk,
        }
        fname = os.path.basename(os.path.join(TEST_PATH, 'test_data/nidm/auditory.nidm.zip'))
        file_dict = {
            'zip_file': SimpleUploadedFile(fname, zip_file.read())}
        form = NIDMResultsForm(post_dict, file_dict)
        form.save()

        # Upload Statistic Map
        image = save_statmap_form(image_path=os.path.join(TEST_PATH, 'test_data/statmaps/all.nii.gz'),
                                   collection=collection,
                                   image_name="all.nii.gz")

        factory = RequestFactory()
        self.client.login(username=self.user)
        request = factory.get('/collections/%s/download' % collection.pk, {'format': 'img.zip'})
        request.user = self.user
        response = download_collection(request, str(collection.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Disposition'), "attachment; filename=" + collection.name + ".zip")

        zf = zipfile.ZipFile(io.BytesIO(b''.join(response.streaming_content)))

        self.assertEqual(len(zf.filelist),2)  # 1 NIDMResult, 1 Statmap
        self.assertIsNone(zf.testzip())
        self.assertIn("Collection2/all.nii.gz", zf.namelist())
        self.assertIn("Collection2/auditory.nidm.zip", zf.namelist())


