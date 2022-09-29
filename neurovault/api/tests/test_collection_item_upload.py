import os

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status

from neurovault.apps.statmaps.models import (
    Collection, StatisticMap, NIDMResults, CognitiveAtlasTask, CognitiveAtlasContrast
)

from neurovault.apps.statmaps.tests.utils import clearDB
from neurovault.apps.statmaps.tests.test_nidm import NIDM_TEST_FILES
from neurovault.api.tests.base import APITestCase
from neurovault.api.tests.utils import _setup_test_cognitive_atlas


class TestCollectionItemUpload(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()
        _setup_test_cognitive_atlas()
        
    def tearDown(self):
        clearDB()

    def test_upload_statmap(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/images/' % self.coll.pk
        fname = self.abs_data_path('statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'cognitive_paradigm_cogatlas': 'trm_4f24126c22011',
            'cognitive_contrast_cogatlas': 'cnt_4e08fefbf0382',
            'file': SimpleUploadedFile(fname, open(fname, 'rb').read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['collection_id'], self.coll.id)
        self.assertRegex(response.data['file'], r'\.nii\.gz$')

        self.assertEqual(response.data['cognitive_paradigm_cogatlas'],
                         'action observation task')

        for key in ('name', 'modality'):
            self.assertEqual(response.data[key], post_dict[key])

        statmap = StatisticMap.objects.get(pk=response.data['id'])
        self.assertEqual(statmap.cognitive_paradigm_cogatlas.name,
                         'action observation task')
        self.assertEqual(statmap.cognitive_contrast_cogatlas.name,
                         'standard deviation from the mean accuracy score')

    def test_upload_statmap_with_metadata(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/images/' % self.coll.pk
        fname = self.abs_data_path('statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname, 'rb').read()),
            'custom_metadata_numeric_field': 42,
            'custom_metadata_string_field': 'forty two',
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['collection_id'], self.coll.id)
        self.assertRegex(response.data['file'], r'\.nii\.gz$')

        exclude_keys = set([
            'file',
            'map_type',
            'custom_metadata_numeric_field',
            'custom_metadata_string_field'
        ])

        test_keys = post_dict.keys() - exclude_keys
        for key in test_keys:
            self.assertEqual(response.data[key], post_dict[key])

        self.assertEqual(response.data['custom_metadata_numeric_field'], 42)

        statmap = StatisticMap.objects.get(pk=response.data['id'])
        self.assertEqual(
            statmap.map_type, 'T'
        )
        self.assertEqual(statmap.data['custom_metadata_numeric_field'], '42')
        self.assertEqual(
            statmap.data['custom_metadata_string_field'],
            'forty two'
        )

    def test_upload_statmap_with_metadata_data_property(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/images/' % self.coll.pk
        fname = self.abs_data_path('statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname, 'rb').read()),
            'data': 42
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['data'], 42)

        statmap = StatisticMap.objects.get(pk=response.data['id'])
        self.assertEqual(statmap.data['data'], '42')

    def test_upload_atlas(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/atlases/' % self.coll.pk
        nii_path = self.abs_data_path(
            'api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'
        )
        xml_path = self.abs_data_path(
            'api/VentralFrontal_thr75_summaryimage_2mm.xml'
        )

        post_dict = {
            'name': 'test atlas',
            'file': SimpleUploadedFile(nii_path, open(nii_path, 'rb').read()),
            'label_description_file': SimpleUploadedFile(xml_path,
                                                         open(xml_path, 'rb').read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['collection_id'], self.coll.id)
        self.assertRegex(response.data['file'], r'\.nii\.gz$')
        self.assertRegex(response.data['label_description_file'],
                                 r'\.xml$')

        self.assertEqual(response.data['name'], post_dict['name'])

    def test_upload_nidm_results(self):
        self.client.force_authenticate(user=self.user)
        url = '/api/collections/%s/nidm_results/' % self.coll.pk

        for name, data in list(NIDM_TEST_FILES.items()):
            self._test_upload_nidm_results(url, name, data)

    def _test_upload_nidm_results(self, url, name, data):
        fname = os.path.basename(data['file'])

        post_dict = {
            'name': name,
            'description': '{0} upload test'.format(name),
            'zip_file': SimpleUploadedFile(fname,
                                           open(data['file'], 'rb').read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['collection'], self.coll.id)
        self.assertRegex(response.data['zip_file'], r'\.nidm\.zip$')
        self.assertRegex(response.data['url'], r'\.nidm$')

        nidm = NIDMResults.objects.get(pk=response.data['id'])
        self.assertEqual(len(nidm.nidmresultstatisticmap_set.all()),
                          data['num_statmaps'])

        map_type = data['output_row']['type'][0]
        map_imgs = nidm.nidmresultstatisticmap_set.filter(
            map_type=map_type).all()

        self.assertTrue(data['output_row']['name'] in [m.name for m in map_imgs])

    def test_missing_required_fields(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/images/' % self.coll.pk

        post_dict = {
            'name': 'test map',
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        expect_dict = {'map_type': ['This field is required.'],
                       'modality': ['This field is required.'],
                       'file': ['No file was submitted.']}

        self.assertEqual(response.data, expect_dict)

    def test_missing_required_authentication(self):
        url = '/api/collections/%s/images/' % self.coll.pk
        fname = self.abs_data_path('statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname, 'rb').read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {
            'detail': 'Authentication credentials were not provided.'
        })

    def test_missing_required_permissions(self):
        self.client.force_authenticate(user=self.user)

        other_user = User.objects.create_user('OtherGuy')
        other_user.save()

        other_collection = Collection(owner=other_user,
                                      name="Another Test Collection")
        other_collection.save()

        url = '/api/collections/%s/images/' % other_collection.pk
        fname = self.abs_data_path('statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname, 'rb').read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {
            'detail': 'You do not have permission to perform this action.'
        })
