from django.test import TestCase, Client, override_settings, RequestFactory
from django.urls import reverse
from neurovault.adapters.persistence.models import Collection, User, Item
from django.core.files.uploadedfile import SimpleUploadedFile
from uuid import uuid4
import tempfile
import os
import shutil
from neurovault.core.domain.map_quality import detect_4D
from neurovault.adapters.neuroimaging.workspace import split_4D_to_3D
import nibabel
from .utils import clearDB
from django.conf import settings

PRIVATE_MEDIA_ROOT = settings.PRIVATE_MEDIA_ROOT

from neurovault.adapters.web.statmaps.views import delete_collection
from neurovault.adapters.web.statmaps.tests.utils import persist
from neurovault.core.application.ports import SYSTEM
from neurovault.config.bootstrap import services


class MoveImageTest(TestCase):
    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))

        self.user = User.objects.create_user("NeuroGuy")
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user)
        self.coll1 = Collection(owner=self.user, name="Test Collection 1")
        persist(self.coll1)

        self.coll2 = Collection(owner=self.user, name="Test Collection 2")
        persist(self.coll2)

    def tearDown(self):
        clearDB()

    def testCollectionSharing(self):
        self.unorderedAtlas = Item(
            kind=Item.ATLAS,
            name="unorderedAtlas", description="", collection=self.coll1
        )
        self.unorderedAtlas.file = SimpleUploadedFile(
            "VentralFrontal_thr75_summaryimage_2mm.nii.gz",
            open(
                os.path.join(
                    self.test_path,
                    "test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz",
                ),
                "rb",
            ).read(),
        )
        self.unorderedAtlas.label_description_file = SimpleUploadedFile(
            "test_VentralFrontal_thr75_summaryimage_2mm.xml",
            open(
                os.path.join(
                    self.test_path,
                    "test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml",
                ),
                "rb",
            ).read(),
        )
        persist(self.unorderedAtlas)

        self.unorderedAtlas = Item.objects.get(id=self.unorderedAtlas.id)
        print(self.unorderedAtlas.file.path)
        self.assertTrue(os.path.exists(self.unorderedAtlas.file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.label_description_file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.thumbnail.path))
        old_path = self.unorderedAtlas.file.path

        services().items.change(SYSTEM, self.unorderedAtlas.pk, {"collection_id": self.coll2.pk})

        # check if old files were deleted
        self.assertFalse(os.path.exists(old_path))

        # check if new files exist
        self.unorderedAtlas = Item.objects.get(id=self.unorderedAtlas.id)
        self.assertTrue(os.path.exists(self.unorderedAtlas.file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.label_description_file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.thumbnail.path))

        self.coll1.delete()

        self.unorderedAtlas = Item.objects.get(id=self.unorderedAtlas.id)
        print(self.unorderedAtlas.file.path)
        self.assertTrue(os.path.exists(self.unorderedAtlas.file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.label_description_file.path))
        self.assertTrue(os.path.exists(self.unorderedAtlas.thumbnail.path))
