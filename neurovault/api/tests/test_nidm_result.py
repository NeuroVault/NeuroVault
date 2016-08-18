import uuid

from rest_framework import status

from neurovault.apps.statmaps.models import NIDMResults
from neurovault.apps.statmaps.tests.utils import save_nidm_form
from neurovault.api.tests.base import BaseTestCases

from neurovault.api.tests.base import STATMAPS_TESTS_PATH


class TestNIDMResultsChange(BaseTestCases.TestCollectionItemChange):
    def setUp(self):
        super(TestNIDMResultsChange, self).setUp()

        self.item = save_nidm_form(
            name='fsl_course_av',
            zip_file=self.abs_file_path(
                STATMAPS_TESTS_PATH
                + 'test_data/nidm/fsl_course_av.nidm.zip'
            ),
            collection=self.coll
        )

        self.item_url = '/api/nidm_results/%s/' % self.item.pk

    def test_nidm_results_update(self):
        self.client.force_authenticate(user=self.user)

        file = self.simple_uploaded_file(
            STATMAPS_TESTS_PATH + 'test_data/nidm/fsl_course_fluency2.nidm.zip'
        )

        put_dict = {
            'name': 'fsl_course_fluency2',
            'description': "renamed %s" % uuid.uuid4(),
            'zip_file': file
        }

        response = self.client.put(self.item_url, put_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['description'], put_dict['description'])
        self.assertRegexpMatches(response.data['ttl_file'],
                                 r'fsl_course_fluency2\.nidm\.ttl$')

    def test_nidm_results_destroy(self):
        self._test_collection_item_destroy(NIDMResults)
