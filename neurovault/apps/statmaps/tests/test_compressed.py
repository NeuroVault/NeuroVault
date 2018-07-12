import os
import shutil
import tarfile
import tempfile
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from zipfile import ZipFile

from neurovault.apps.statmaps.models import User, Collection, Image
from .utils import clearDB


# The function 'reverse' resolves a view name and its arguments into a path
# which can be passed into the method self.client.get(). We use the 'reverse'
# method here in order to avoid writing hard-coded URLs inside tests.
 
 
class UploadFolderTestCase(TestCase):
    def setUp(self):
        super(UploadFolderTestCase, self).setUp()
        self.tmpdir = tempfile.mkdtemp()
        test_path = os.path.abspath(os.path.dirname(__file__))
        with ZipFile(os.path.join(self.tmpdir, 'example.zip'), 'w') as myzip:
            myzip.write(os.path.join(test_path, 'test_data/statmaps/all.nii.gz'))
            myzip.write(os.path.join(test_path, 'test_data/statmaps/beta_0001.nii.gz'))
            myzip.write(os.path.join(test_path, 'test_data/statmaps/motor_lips.nii.gz'))
            myzip.write(os.path.join(test_path, 'test_data/statmaps/WA3.nii.gz'))
            
        with tarfile.open(os.path.join(self.tmpdir, 'example.tar.gz'), "w:gz") as tar:
            tar.add(os.path.join(test_path, 'test_data/statmaps/all.nii.gz'))
            tar.add(os.path.join(test_path, 'test_data/statmaps/beta_0001.nii.gz'))
            tar.add(os.path.join(test_path, 'test_data/statmaps/motor_lips.nii.gz'))
            tar.add(os.path.join(test_path, 'test_data/statmaps/WA3.nii.gz'))
            
        self.user = User.objects.create_user('NeuroGuy', password="1234")
        self.user.save()
        self.client = Client()
        login_successful = self.client.login(username=self.user.username, password="1234")
        self.assertTrue(login_successful)
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()
 
    def tearDown(self):
        clearDB()
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        self.coll.delete()
        self.user.delete()
 
    def test_upload_zip(self):
        with open(os.path.join(self.tmpdir, 'example.zip', 'rb')) as fp:
            response = self.client.post(reverse('upload_folder', kwargs={'collection_cid': self.coll.id}), {'collection_cid': self.coll.id, 'file': fp})
        # Assert that self.post is actually returned by the post_detail view
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.coll.basecollectionitem_set.instance_of(Image).count(), 4)
        
    def test_upload_tar_gz(self):
        with open(os.path.join(self.tmpdir, 'example.tar.gz')) as fp:
            response = self.client.post(reverse(str.encode('upload_folder'), kwargs={'collection_cid': self.coll.id}), {'collection_cid': self.coll.id, 'file': fp})
        # Assert that self.post is actually returned by the post_detail view
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.coll.basecollectionitem_set.instance_of(Image).count(), 4)

        