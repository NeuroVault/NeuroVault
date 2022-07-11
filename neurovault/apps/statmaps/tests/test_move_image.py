from django.test import TestCase, Client, override_settings, RequestFactory
from django.urls import reverse
from neurovault.apps.statmaps.models import Collection,User, Atlas, Image
from django.core.files.uploadedfile import SimpleUploadedFile
from uuid import uuid4
import tempfile
import os
import shutil
from neurovault.apps.statmaps.utils import detect_4D, split_4D_to_3D
import nibabel
from .utils import clearDB
from neurovault.settings import PRIVATE_MEDIA_ROOT

from neurovault.apps.statmaps.views import delete_collection



class MoveImageTest(TestCase):

    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user)
        self.coll1 = Collection(owner=self.user, name="Test Collection 1")
        self.coll1.save()
        
        self.coll2 = Collection(owner=self.user, name="Test Collection 2")
        self.coll2.save()
    
    def tearDown(self):
        clearDB()

    def testCollectionSharing(self):

        self.unorderedAtlas = Atlas(name='unorderedAtlas', description='',collection=self.coll1)
        self.unorderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        self.unorderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(self.test_path,'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        self.unorderedAtlas.save()
        
        self.unorderedAtlas = Image.objects.get(id=self.unorderedAtlas.id)
        print(self.unorderedAtlas.file.path)
        self.assertTrue(os.path.exists(self.unorderedAtlas.file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.label_description_file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.thumbnail.path))
        old_path = self.unorderedAtlas.file.path
        
        self.unorderedAtlas.collection = self.coll2
        self.unorderedAtlas.save()
        
        #check if old files were deleted
        self.assertFalse(os.path.exists(old_path))
        
        #check if new files exist
        self.unorderedAtlas = Image.objects.get(id=self.unorderedAtlas.id)
        self.assertTrue(os.path.exists(self.unorderedAtlas.file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.label_description_file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.thumbnail.path))
        
        self.coll1.delete()
        
        self.unorderedAtlas = Image.objects.get(id=self.unorderedAtlas.id)
        print(self.unorderedAtlas.file.path)
        self.assertTrue(os.path.exists(self.unorderedAtlas.file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.label_description_file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.thumbnail.path))
