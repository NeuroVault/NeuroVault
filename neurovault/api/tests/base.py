import os
import uuid

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import test as rest_framework_test
from rest_framework import status

from neurovault.apps.statmaps.models import Collection, CognitiveAtlasTask
from neurovault.apps.statmaps.tests.utils import clearDB

STATMAPS_TESTS_PATH = '../../apps/statmaps/tests/'


class APITestCase(rest_framework_test.APITestCase):
    def abs_file_path(self, rel_path):
        return os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            rel_path)

    def abs_data_path(self, relative_filename_path):
        return self.abs_file_path(os.path.join(
            STATMAPS_TESTS_PATH,
            'test_data',
            relative_filename_path
        ))


class BaseTestCases:
    class TestCollectionItemChange(APITestCase):

        def simple_uploaded_file(self, rel_path):
            fname = self.abs_data_path(rel_path)
            return SimpleUploadedFile(rel_path, open(fname, 'rb').read())

        def setUp(self):
            self.user = User.objects.create_user('NeuroGuy')
            self.user.save()
            self.coll = Collection(owner=self.user, name="Test Collection")
            self.coll.save()

            cat = CognitiveAtlasTask.objects.update_or_create(
                cog_atlas_id="trm_4f24126c22011",defaults={"name": "abstract/concrete task"})
            cat[0].save()

        def tearDown(self):
            clearDB()

        def test_collection_item_partial_update(self):
            self.client.force_authenticate(user=self.user)

            patch_dict = {
                'description': "renamed %s" % uuid.uuid4(),
            }

            response = self.client.patch(self.item_url, patch_dict)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['description'],
                             patch_dict['description'])

        def test_missing_required_permissions(self):
            other_user = User.objects.create_user('OtherGuy')
            self.client.force_authenticate(user=other_user)

            patch_dict = {
                'description': "renamed %s" % uuid.uuid4(),
            }

            response = self.client.patch(self.item_url, patch_dict)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.delete(self.item_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        def _test_collection_item_destroy(self, model_class):
            self.client.force_authenticate(user=self.user)

            response = self.client.delete(self.item_url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            with self.assertRaises(model_class.DoesNotExist):
                model_class.objects.get(pk=self.item.pk)
