import uuid

from django.contrib.auth.models import User

from rest_framework import status

from neurovault.apps.statmaps.models import NIDMResults, Collection
from neurovault.apps.statmaps.tests.utils import save_nidm_form, clearDB
from neurovault.api.tests.base import BaseTestCases

from neurovault.api.tests.base import APITestCase


class TestNIDMResults(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.collection = Collection(owner=self.user, name="Test Collection")
        self.collection.save()

        zip_file = self.abs_data_path('nidm/spm_example.nidm.zip')
        self.nidm = save_nidm_form(
            zip_file=zip_file, collection=self.collection)

    def test_fetch_nidm_results_list(self):
        print("\nTesting NIDM results API....")
        response = self.client.get('/api/nidm_results/')
        descriptions = [item['description']
                        for item in response.data['results'][0]['statmaps']]
        self.assertIn(
            'NIDM Results: spm_example.nidm.zip > TStatistic.nii.gz',
            descriptions
        )

    def test_nidm_results_pk(self):
        url = '/api/nidm_results/%d/' % self.nidm.pk
        response = self.client.get(url)
        self.assertTrue('spm_example.nidm.ttl' in response.data['ttl_file'])
        self.assertEqual(response.data['statmaps'][0]['figure'], None)

    def tearDown(self):
        clearDB()


class TestNIDMResultsChange(BaseTestCases.TestCollectionItemChange):
    def setUp(self):
        super(TestNIDMResultsChange, self).setUp()

        self.item = save_nidm_form(
            name='fsl_course_av',
            zip_file=self.abs_data_path('nidm/fsl_course_av.nidm.zip'),
            collection=self.coll
        )

        self.item_url = '/api/nidm_results/%s/' % self.item.pk

    def test_nidm_results_update(self):
        self.client.force_authenticate(user=self.user)

        file = self.simple_uploaded_file('nidm/fsl_course_fluency2.nidm.zip')

        put_dict = {
            'name': 'fsl_course_fluency2',
            'description': "renamed %s" % uuid.uuid4(),
            'zip_file': file
        }

        response = self.client.put(self.item_url, put_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['description'], put_dict['description'])
        self.assertRegex(response.data['ttl_file'],
                                 r'fsl_course_fluency2\.nidm\.ttl$')

    def test_nidm_results_destroy(self):
        self._test_collection_item_destroy(NIDMResults)
