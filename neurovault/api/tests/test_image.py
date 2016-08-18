import os

from django.contrib.auth.models import User

from rest_framework.test import APITestCase

from neurovault.apps.statmaps.models import Collection
from neurovault.apps.statmaps.tests.utils import (
    save_atlas_form, save_nidm_form, save_statmap_form, clearDB
)
from neurovault.api.tests.base import STATMAPS_TESTS_PATH
from neurovault.api.pagination import StandardResultPagination


class TestImage(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.collection = Collection(owner=self.user, name="Test Collection")
        self.collection.save()
        self.test_path = os.path.abspath(os.path.dirname(__file__))

        nii_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'
        )
        xml_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml'
        )

        self.unorderedAtlas = save_atlas_form(
            nii_path=nii_path,
            xml_path=xml_path,
            collection=self.collection,
            name="unorderedAtlas"
        )

        nii_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/statmaps/motor_lips.nii.gz'
        )
        self.image1 = save_statmap_form(
            image_path=nii_path,
            collection=self.collection
        )

        nii_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/statmaps/beta_0001.nii.gz'
        )
        self.image2 = save_statmap_form(
            image_path=nii_path,
            collection=self.collection
        )

        zip_file = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/nidm/spm_example.nidm.zip'
        )
        self.nidm = save_nidm_form(
            zip_file=zip_file, collection=self.collection)

    def tearDown(self):
        clearDB()

    def test_fetch_image_list(self):
        response = self.client.get('/api/images/')
        names = [item['name'] for item in response.data['results']]
        self.assertTrue('unorderedAtlas' in names)
        self.assertTrue('Statistic Map: passive listening > rest' in names)

    def test_fetch_image(self):
        url = '/api/images/%d/' % self.image1.pk
        response = self.client.get(url)
        self.assertTrue('http' in response.data['collection'])
        image_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/statmaps/motor_lips.nii.gz'
        )
        self.assertEqual(response.data['name'], image_path)

    def test_images_datatable(self):
        url = '/api/images/%d/datatable/' % self.image2.pk
        response = self.client.get(url)
        resp_dict = dict(response.data['aaData'])
        self.assertIn('http', resp_dict['url'])
        self.assertEqual(resp_dict['id'], self.image2.pk)

    def test_pagination(self):
        print "\nTesting API pagination..."
        print "Max limit is set to %s" % StandardResultPagination.max_limit
        self.assertEqual(1000, StandardResultPagination.max_limit)
        print "Default limit is set to %s" % (
            StandardResultPagination.default_limit
        )
        self.assertEqual(100, StandardResultPagination.default_limit)
        print "Page size (equal to default) is set to %s" % (
            StandardResultPagination.PAGE_SIZE
        )
        self.assertEqual(100, StandardResultPagination.PAGE_SIZE)

        url = '/api/images/?limit=1'
        response = self.client.get(url)
        self.assertEqual(1, len(response.data['results']))
        url = '/api/images/?limit=2'
        response = self.client.get(url)
        self.assertEqual(2, len(response.data['results']))
