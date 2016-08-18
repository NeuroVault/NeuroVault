import uuid

from rest_framework import status

from neurovault.apps.statmaps.models import StatisticMap
from neurovault.apps.statmaps.tests.utils import save_statmap_form

from neurovault.api.tests.base import BaseTestCases
from neurovault.api.tests.base import STATMAPS_TESTS_PATH


class TestStatisticMapChange(BaseTestCases.TestCollectionItemChange):
    def setUp(self):
        super(TestStatisticMapChange, self).setUp()
        self.item = save_statmap_form(
            image_path=self.abs_file_path(
                STATMAPS_TESTS_PATH + 'test_data/statmaps/motor_lips.nii.gz'
            ),
            collection=self.coll
        )

        self.item_url = '/api/images/%s/' % self.item.pk

    def test_statistic_map_update(self):
        self.client.force_authenticate(user=self.user)

        file = self.simple_uploaded_file(
            STATMAPS_TESTS_PATH + 'test_data/statmaps/motor_lips.nii.gz'
        )

        put_dict = {
            'name': "renamed %s" % uuid.uuid4(),
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': file,
            'custom_metadata_numeric_field': 42
        }

        response = self.client.put(self.item_url, put_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['name'], put_dict['name'])
        self.assertEqual(response.data['custom_metadata_numeric_field'], 42)

    def test_statistic_map_metadata_partial_update(self):
        self.client.force_authenticate(user=self.user)

        self.item.data['custom_metadata_field_a'] = 'a text'
        self.item.data['custom_metadata_field_b'] = 'b text'
        self.item.save()

        patch_dict = {
            'name': "renamed %s" % uuid.uuid4(),
            'custom_metadata_field_b': 'override b with %s' % uuid.uuid4(),
            'custom_metadata_field_c': 42
        }

        response = self.client.patch(self.item_url, patch_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['name'], patch_dict['name'])

        self.assertEqual(response.data['custom_metadata_field_a'], 'a text')
        self.assertEqual(
            response.data['custom_metadata_field_b'],
            patch_dict['custom_metadata_field_b']
        )
        self.assertEqual(response.data['custom_metadata_field_c'], 42)

        statmap = StatisticMap.objects.get(pk=response.data['id'])
        self.assertEqual(statmap.data['custom_metadata_field_a'], 'a text')
        self.assertEqual(
            statmap.data['custom_metadata_field_b'],
            patch_dict['custom_metadata_field_b']
        )
        self.assertEqual(statmap.data['custom_metadata_field_c'], '42')

    def test_statistic_map_destroy(self):
        self._test_collection_item_destroy(StatisticMap)
