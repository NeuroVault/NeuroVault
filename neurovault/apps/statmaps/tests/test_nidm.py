from django.test import TestCase, Client, override_settings
from django.core.urlresolvers import reverse
from neurovault.apps.statmaps.models import Collection,User
from uuid import uuid4
import tempfile
import os
import shutil
import zipfile
from neurovault.apps.statmaps.utils import NIDMUpload


class NIDMResultsTest(TestCase):

    def setUp(self):
        testpath = os.path.abspath(os.path.dirname(__file__))
        self.files = {
            'fsl_nidm':      os.path.join(testpath,'test_data/nidm/fsl.nidm.zip'),
            'two_contrasts': os.path.join(testpath,'test_data/nidm/two_contrasts.nidm.zip'),

            ## not parsing with latest rdflib 4.1.2
            ## turtle parsing still under active development
            ## see also: https://github.com/RDFLib/rdflib/issues/336
            'broken_spm_example':   os.path.join(testpath,'test_data/nidm/spm_example.nidm.zip'),
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

    def testParseNIDMZip(self):
        contrasts = {}
        turtles = {}  # I like turtles.
        uploads = {}
        statmaps = {}

        for name in ['fsl_nidm','two_contrasts']:
            uploads[name] = NIDMUpload(self.files[name],tmp_dir=self.tmpdir,load=False)
            turtles[name] = uploads[name].parse_ttl(extract=True)
            contrasts[name] = uploads[name].parse_contrasts()
            statmaps[name] = uploads[name].get_statmaps()

        """
        assert known bad file throws parsing error
        """
        with self.assertRaises(NIDMUpload.ParseException):
            bad_ttl = NIDMUpload(self.files['broken_spm_example'])
