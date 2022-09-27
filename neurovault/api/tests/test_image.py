from django.contrib.auth.models import User

from neurovault.apps.statmaps.models import Collection, CognitiveAtlasTask
from neurovault.apps.statmaps.tests.utils import (
    save_atlas_form, save_nidm_form, save_statmap_form, clearDB
)
from neurovault.api.tests.base import APITestCase
from neurovault.api.pagination import StandardResultPagination


class TestImage(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.collection = Collection(owner=self.user, name="Test Collection")
        self.collection.save()
        cat = CognitiveAtlasTask.objects.update_or_create(
            cog_atlas_id="trm_4f24126c22011",defaults={"name": "abstract/concrete task"})
        cat[0].save()

        self.unorderedAtlas = save_atlas_form(
            nii_path=self.abs_data_path(
                'api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'
            ),
            xml_path=self.abs_data_path(
                'api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml'
            ),
            collection=self.collection,
            name="unorderedAtlas"
        )

        self.image1 = save_statmap_form(
            image_path=self.abs_data_path(
                'statmaps/motor_lips.nii.gz'
            ),
            collection=self.collection
        )

        self.image2 = save_statmap_form(
            image_path=self.abs_data_path(
                'statmaps/beta_0001.nii.gz'
            ),
            collection=self.collection
        )

        self.nidm = save_nidm_form(
            zip_file=self.abs_data_path(
                'nidm/spm_example.nidm.zip'
            ),
            collection=self.collection
        )

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
        image_path = self.abs_data_path('statmaps/motor_lips.nii.gz')
        self.assertEqual(response.data['name'], image_path)

    def test_images_datatable(self):
        url = '/api/images/%d/datatable/' % self.image2.pk
        response = self.client.get(url)
        resp_dict = dict(response.data['aaData'])
        self.assertIn('http', resp_dict['url'])
        self.assertEqual(resp_dict['id'], self.image2.pk)

    def test_pagination(self):
        print("\nTesting API pagination...")
        print("Max limit is set to %s" % StandardResultPagination.max_limit)
        self.assertEqual(1000, StandardResultPagination.max_limit)
        print("Default limit is set to %s" % (
            StandardResultPagination.default_limit
        ))
        self.assertEqual(100, StandardResultPagination.default_limit)
        print("Page size (equal to default) is set to %s" % (
            StandardResultPagination.PAGE_SIZE
        ))
        self.assertEqual(100, StandardResultPagination.PAGE_SIZE)

        url = '/api/images/?limit=1'
        response = self.client.get(url)
        self.assertEqual(1, len(response.data['results']))
        url = '/api/images/?limit=2'
        response = self.client.get(url)
        self.assertEqual(2, len(response.data['results']))
