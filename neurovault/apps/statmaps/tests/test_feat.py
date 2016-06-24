import os
import shutil
import tempfile
import urllib
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from nidmfsl.fsl_exporter.fsl_exporter import FSLtoNIDMExporter

from neurovault.apps.statmaps.forms import NIDMResultsForm
from neurovault.apps.statmaps.models import Collection,User
from neurovault.apps.statmaps.utils import detect_feat_directory
from .utils import clearDB


class FeatDirectoryTest(TestCase):

    def setUp(self):
        testpath = os.path.join(os.path.abspath(os.path.dirname(__file__)),'test_data','feat')
        testdata_repo = 'https://github.com/NeuroVault/neurovault_data/blob/master/FEAT_testdata/'

        self.testfiles = {
            'ds105.feat.zip': {
                'fileuri':'ds105.feat.zip?raw=true',
                'num_statmaps':2,
                'export_dir':'ds105.feat/cope1.feat/nidm',
                'ttl_fsize': 30000,
                'map_types': ['T','Z'],
                'names':['Statistic Map: group mean', 'Z-Statistic Map: group mean'],

            },

            'ds017A.zip': {
                'fileuri':'ds017A.zip?raw=true',
                'num_statmaps':2,
                'export_dir': 'ds017A/group/model001/task001/cope001.gfeat/cope1.feat/nidm',
                'ttl_fsize': 68026,
                'map_types': ['T','Z'],
                'names':['Statistic Map: group mean', 'Z-Statistic Map: group mean'],
            },
        }

        self.tmpdir = tempfile.mkdtemp()
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user)
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

        # FEAT test data is large so it lives in the external data repo
        for fname, info in self.testfiles.items():
            self.testfiles[fname]['file'] = os.path.join(testpath,fname)
            if not os.path.exists(self.testfiles[fname]['file']):
                print '\ndownloading test data {}'.format(fname)
                furl = '{0}{1}'.format(testdata_repo, info['fileuri'])
                try:
                    urllib.urlretrieve(furl, self.testfiles[fname]['file'])
                except:
                    os.remove(os.path.join(testpath,fname))
                    raise

            self.testfiles[fname]['sourcedir'] = self.testfiles[fname]['file'][:-4]
            self.testfiles[fname]['dir'] = os.path.join(self.tmpdir,fname[:-4])

            if not os.path.exists(self.testfiles[fname]['sourcedir']):
                fh = open(os.path.join(testpath,fname), 'rb')
                z = zipfile.ZipFile(fh)
                for name in [v for v in z.namelist() if not v.startswith('.') and
                             '/.files' not in v]:
                    outpath = self.testfiles[fname]['sourcedir']
                    z.extract(name, outpath)
                fh.close()

            shutil.copytree(self.testfiles[fname]['sourcedir'], self.testfiles[fname]['dir'])

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()

    def testFEAT_NIDM(self):

        # test feat parsing
        for fname, info in self.testfiles.items():
            info['found_feat'] = False
            for root, dirs, files in os.walk(info['dir']):
                if detect_feat_directory(root):
                    print 'Found FEAT directory at {}.'.format(root)
                    info['found_feat'] = True
                    fslnidm = FSLtoNIDMExporter(feat_dir=root, version="1.2.0")
                    fslnidm.parse()
                    info['nidm_file'] = fslnidm.export()

                    # confirm results path and existence
                    self.assertTrue(os.path.exists(info['nidm_file']))

        # test upload nidm
        for fname, info in self.testfiles.items():

            zname = os.path.basename(info['nidm_file'])
            post_dict = {
                'name': zname,
                'description': '{0} upload test'.format(zname),
                'collection': self.coll.pk,
            }
            

            file_dict = {'zip_file': SimpleUploadedFile(zname, open(info['nidm_file'],'r').read())}
            form = NIDMResultsForm(post_dict, file_dict)

            # validate NIDM Results
            self.assertEqual(form.errors, {})
            nidm = form.save()

            statmaps = nidm.nidmresultstatisticmap_set.all()
            self.assertEquals(len(statmaps),info['num_statmaps'])

            map_types = [v.map_type for v in statmaps]
            self.assertEquals(sorted(map_types), sorted(info['map_types']))

            names = [v.name for v in statmaps]
            self.assertEquals(sorted(names), sorted(info['names']))

