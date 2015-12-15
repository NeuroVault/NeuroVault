import uuid

from neurovault.apps.statmaps.tests.utils import (clearDB, save_atlas_form,
                                                  save_statmap_form,
                                                  save_nidm_form)
from neurovault.apps.statmaps.models import (Atlas, Collection,
                                             StatisticMap, NIDMResults)
from neurovault.apps.statmaps.urls import StandardResultPagination
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase, Client
from rest_framework.test import APITestCase
from rest_framework import status
import xml.etree.ElementTree as ET
from operator import itemgetter
import os.path
import json

from .test_nidm import NIMD_TEST_FILES


class Test_Atlas_APIs(TestCase):

    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1', owner=self.user)
        self.Collection1.save()
        self.unorderedAtlas = Atlas(
            name='unorderedAtlas', description='', collection=self.Collection1)

        # Save new atlas object, unordered
        print "Adding unordered and ordered atlas..."
        nii_path = os.path.join(
            self.test_path, 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')
        xml_path = os.path.join(
            self.test_path, 'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')
        self.unorderedAtlas = save_atlas_form(nii_path=nii_path,
                                              xml_path=xml_path,
                                              collection=self.Collection1,
                                              name="unorderedAtlas")
        # Ordered
        nii_path = os.path.join(
            self.test_path, 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')
        xml_path = os.path.join(
            self.test_path, 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml')
        self.orderedAtlas = save_atlas_form(nii_path=nii_path,
                                            xml_path=xml_path,
                                            collection=self.Collection1,
                                            name="orderedAtlas")

        # Statistical Map 1 and 2
        print "Adding statistical maps..."
        nii_path = os.path.join(
            self.test_path, 'test_data/statmaps/motor_lips.nii.gz')
        self.Image1 = save_statmap_form(
            image_path=nii_path, collection=self.Collection1)
        nii_path = os.path.join(
            self.test_path, 'test_data/statmaps/beta_0001.nii.gz')
        self.Image2 = save_statmap_form(
            image_path=nii_path, collection=self.Collection1)

        # Zip file with nidm results
        print "Adding nidm results..."
        zip_file = os.path.join(
            self.test_path, 'test_data/nidm/spm_example.nidm.zip')
        self.nidm = save_nidm_form(
            zip_file=zip_file, collection=self.Collection1)

    def tearDown(self):
        clearDB()

# Atlas Query Tests

    def test_query_region_out_of_order_indices(self):

        print "\nAssessing equality of ordered vs. unordered atlas query..."
        atlas_dir = os.path.join(self.test_path, 'test_data/api')
        tree = ET.parse(
            os.path.join(atlas_dir, 'VentralFrontal_thr75_summaryimage_2mm.xml'))
        root = tree.getroot()
        atlasRegions = [x.text.lower()
                        for x in root.find('data').findall('label')]
        for region in atlasRegions:
            orderedURL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=orderedAtlas&collection=Collection1' % (
                region)
            orderedResponse = self.client.get(orderedURL, follow=True)
            unorderedURL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=unorderedAtlas&collection=Collection1' % (
                region)
            unorderedResponse = self.client.get(unorderedURL, follow=True)
            orderedList = eval(orderedResponse.content)['voxels']
            unorderedList = eval(unorderedResponse.content)['voxels']
            orderedTriples = [(orderedList[0][i], orderedList[1][i],
                               orderedList[2][i]) for i in range(len(orderedList[0]))]
            unorderedTriples = [(unorderedList[0][i], unorderedList[1][i],
                                 unorderedList[2][i]) for i in range(len(unorderedList[0]))]
            orderedSorted = sorted(orderedTriples, key=itemgetter(0))
            unorderedSorted = sorted(unorderedTriples, key=itemgetter(0))
            print "Equality of lists for region %s: %s" % (region, orderedSorted == unorderedSorted)
            self.assertEqual(orderedSorted, unorderedSorted)

        print "\nAssessing consistency of results for regional query..."
        testRegions = {'6v': [(58.00, -4.00, 18.00), (62.00, 6.00, 30.00)],
                       'fop': [(56.00, 20.00, 24.00), (34.00, 18.00, 30.00)],
                       'fpm': [(8.00, 62.00, 10.00), (10.00, 62.00, -16.00)]}
        for region, testVoxels in testRegions.items():
            URL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=orderedAtlas&collection=Collection1' % (
                region)
            response = self.client.get(URL, follow=True)
            voxelList = eval(response.content)['voxels']
            triples = [(voxelList[0][i], voxelList[1][i], voxelList[2][i])
                       for i in range(len(voxelList[0]))]
            for voxel in testVoxels:
                self.assertTrue(voxel in triples)

    def test_out_of_order_indices(self):
        print "\nAssessing consistency of results for coordinate query..."
        testRegions = {'6v': [(58.00, -4.00, 18.00), (62.00, 6.00, 30.00)],
                       'fop': [(56.00, 20.00, 24.00), (34.00, 18.00, 30.00)],
                       'fpm': [(8.00, 62.00, 10.00), (10.00, 62.00, -16.00)]}

        for region, testVoxels in testRegions.items():
            for triple in testVoxels:
                X, Y, Z = triple[0], triple[1], triple[2]
                URL = 'http://127.0.0.1:8000/api/atlases/atlas_query_voxel/?x=%s&y=%s&z=%s&atlas=orderedAtlas&collection=Collection1' % (
                    X, Y, Z)
                response = self.client.get(URL, follow=True)
                responseText = eval(response.content)
                self.assertEqual(responseText, region)


# General API Tests

    def test_atlases(self):
        print "\nChecking that atlas images are returned by atlas api..."
        url = '/api/atlases/'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('.nii.gz' in response['results'][0][u'file'])
        names = [item[u'name'] for item in response['results']]
        self.assertTrue(u'orderedAtlas' in names)

    def test_atlases_pk(self):
        print "\nTesting atlas query with specific atlas pk...."
        url = '/api/atlases/%d/' % self.unorderedAtlas.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('.nii.gz' in response[u'file'])
        self.assertEqual(response['name'], u'unorderedAtlas')

    def test_atlases_datatable(self):
        print "\nTesting atlas datatable query...."
        url = '/api/atlases/%d/datatable/' % self.unorderedAtlas.pk
        response = json.loads(self.client.get(url, follow=True).content)
        data = dict(response['aaData'])
        self.assertEqual(data['label_description_file'].split("/")[-1],
                         'unordered_VentralFrontal_thr75_summaryimage_2mm.xml')

    def test_atlases_regions_table(self):
        print "\nTesting atlas regions table query...."
        url = '/api/atlases/%d/regions_table/' % self.unorderedAtlas.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(response['aaData'][2][1], u'fop')
        self.assertEqual(response['aaData'][11][1], u'46')

    def test_collections(self):
        print "\nTesting collections API...."
        url = '/api/collections/'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(response['results'][0][u'echo_time'], None)

    def test_collections_pk(self):
        url = '/api/collections/%d/' % self.Collection1.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('-' in response['add_date'])
        self.assertTrue(isinstance(response['id'], int))

    def test_collections_datatable(self):
        url = '/api/collections/%d/datatable/' % self.Collection1.pk
        response = json.loads(self.client.get(url, follow=True).content)
        collection_name = "not found"
        for prop in response['aaData']:
            if prop[0] == 'name':
                collection_name = prop[1]
                break
        self.assertEqual(collection_name, u'Collection1')

    def test_images(self):
        print "\nTesting images API...."
        url = '/api/images/'
        response = json.loads(self.client.get(url, follow=True).content)
        names = [item[u'name'] for item in response['results']]
        self.assertTrue(u'unorderedAtlas' in names)
        self.assertTrue(u'Statistic Map: passive listening > rest' in names)

    def test_images_pk(self):
        url = '/api/images/%d/' % self.Image1.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('http' in response['collection'])
        image_path = os.path.join(
            self.test_path, 'test_data/statmaps/motor_lips.nii.gz')
        self.assertEqual(response['name'], image_path)

    def test_images_datatable(self):
        url = '/api/images/%d/datatable/' % self.Image2.pk
        response = json.loads(self.client.get(url, follow=True).content)
        resp_dict = dict(response['aaData'])
        assert('http' in resp_dict['url'])

    def test_nidm_results(self):
        print "\nTesting NIDM results API...."
        url = '/api/nidm_results/'
        response = json.loads(self.client.get(url, follow=True).content)
        descriptions = [item[u'description']
                        for item in response['results'][0][u'statmaps']]
        self.assertTrue(
            'NIDM Results: spm_example.nidm.zip > TStatistic.nii.gz' in descriptions)

    def test_nidm_results_pk(self):
        url = '/api/nidm_results/%d/' % self.nidm.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('spm_example.nidm.ttl' in response['ttl_file'])
        self.assertEqual(response['statmaps'][0][u'figure'], None)


# Pagination

    def test_pagination(self):
        print "\nTesting API pagination..."
        print "Max limit is set to %s" % (StandardResultPagination.max_limit)
        self.assertEqual(1000, StandardResultPagination.max_limit)
        print "Default limit is set to %s" % (StandardResultPagination.default_limit)
        self.assertEqual(100, StandardResultPagination.default_limit)
        print "Page size (equal to default) is set to %s" % (StandardResultPagination.PAGE_SIZE)
        self.assertEqual(100, StandardResultPagination.PAGE_SIZE)

        url = '/api/images/?limit=1'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(1, len(response['results']))
        url = '/api/images/?limit=2'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(2, len(response['results']))


class TestAuthenticatedUser(APITestCase):
    def setUp(self):
        self.user_fields = {
            'username': 'NeuroGuy',
            'email': 'neuroguy@example.com',
            'first_name': 'Neuro',
            'last_name': 'Guy'
        }
        self.user = User.objects.create_user(**self.user_fields)
        self.user.save()

    def test_unauthenticated_user(self):
        response = self.client.get('/api/user/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {
            'detail': 'Authentication credentials were not provided.'
        })

    def test_authenticated_user(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/user/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data['id'], int)

        for field in self.user_fields.keys():
            self.assertEqual(response.data[field], self.user_fields[field])


class TestCollection(APITestCase):
    def setUp(self):
        self.user_password = 'apitest'
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

    def test_fetch_collection(self):
        response = self.client.get('/api/collections/%s/' % self.coll.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.coll.id)
        self.assertEqual(response.data['name'], self.coll.name)

    def test_create_collection(self):
        self.client.force_authenticate(user=self.user)

        post_dict = {
            'name': 'Test Create Collection',
        }

        response = self.client.post('/api/collections/', post_dict)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], post_dict['name'])

    def test_missing_required_authentication(self):
        url = '/api/collections/%s/' % self.coll.id

        response = self.client.post(url, {'name': 'failed test'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {
            'detail': 'Authentication credentials were not provided.'
        })


class TestCollectionItemUpload(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

    def tearDown(self):
        clearDB()

    def abs_file_path(self, rel_path):
        return os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            rel_path)

    def test_upload_statmap(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/images/' % self.coll.pk
        fname = self.abs_file_path('test_data/statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname).read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['collection'], self.coll.id)
        self.assertRegexpMatches(response.data['file'], r'\.nii\.gz$')

        exclude_keys = ('file',)
        test_keys = set(post_dict.keys()) - set(exclude_keys)
        for key in test_keys:
            self.assertEqual(response.data[key], post_dict[key])

    def test_upload_atlas(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/atlases/' % self.coll.pk
        nii_path = self.abs_file_path(
            'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')
        xml_path = self.abs_file_path(
            'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml')

        post_dict = {
            'name': 'test atlas',
            'file': SimpleUploadedFile(nii_path, open(nii_path).read()),
            'label_description_file': SimpleUploadedFile(xml_path,
                                                         open(xml_path).read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['collection'], self.coll.id)
        self.assertRegexpMatches(response.data['file'], r'\.nii\.gz$')
        self.assertRegexpMatches(response.data['label_description_file'],
                                 r'\.xml$')

        self.assertEqual(response.data['name'], post_dict['name'])

    def test_upload_nidm_results(self):
        self.client.force_authenticate(user=self.user)
        url = '/api/collections/%s/nidm_results/' % self.coll.pk

        for name, data in NIMD_TEST_FILES.items():
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
        self.assertRegexpMatches(response.data['zip_file'], r'\.nidm\.zip$')

        nidm = NIDMResults.objects.get(pk=response.data['id'])
        self.assertEquals(len(nidm.nidmresultstatisticmap_set.all()),
                          data['num_statmaps'])

        map_type = data['output_row']['type'][0]
        map_img = nidm.nidmresultstatisticmap_set.filter(
            map_type=map_type).first()

        self.assertEquals(map_img.name, data['output_row']['name'])

    def test_missing_required_fields(self):
        self.client.force_authenticate(user=self.user)

        url = '/api/collections/%s/images/' % self.coll.pk

        post_dict = {
            'name': 'test map',
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        expect_dict = {'map_type': [u'This field is required.'],
                       'modality': [u'This field is required.'],
                       'file': [u'No file was submitted.']}

        self.assertEqual(response.data, expect_dict)

    def test_missing_required_authentication(self):
        url = '/api/collections/%s/images/' % self.coll.pk
        fname = self.abs_file_path('test_data/statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname).read())
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
        fname = self.abs_file_path('test_data/statmaps/motor_lips.nii.gz')

        post_dict = {
            'name': 'test map',
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': SimpleUploadedFile(fname, open(fname).read())
        }

        response = self.client.post(url, post_dict, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {
            'detail': 'You do not have permission to perform this action.'
        })


class TestCollectionItemChange(APITestCase):
    def abs_file_path(self, rel_path):
        return os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            rel_path)

    def simple_uploaded_file(self, rel_path):
        fname = self.abs_file_path(rel_path)
        return SimpleUploadedFile(rel_path, open(fname).read())

    def setUp(self):
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

    def tearDown(self):
        clearDB()

    def test_collection_item_partial_update(self):
        self.client.force_authenticate(user=self.user)

        patch_dict = {
            'name': "renamed %s" % uuid.uuid4(),
        }

        response = self.client.patch(self.item_url, patch_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], patch_dict['name'])

    def test_collection_item_destroy(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.item_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(StatisticMap.DoesNotExist):
            StatisticMap.objects.get(pk=self.item.pk)


class TestStatisticMapChange(TestCollectionItemChange):
    def setUp(self):
        super(TestStatisticMapChange, self).setUp()

        self.item = save_statmap_form(
            image_path=self.abs_file_path(
                'test_data/statmaps/motor_lips.nii.gz'
            ),
            collection=self.coll
        )

        self.item_url = '/api/images/%s/' % self.item.pk

    def test_statistic_map_update(self):
        self.client.force_authenticate(user=self.user)

        file = self.simple_uploaded_file(
            'test_data/statmaps/motor_lips.nii.gz'
        )

        put_dict = {
            'name': "renamed %s" % uuid.uuid4(),
            'modality': 'fMRI-BOLD',
            'map_type': 'T',
            'file': file
        }

        response = self.client.put(self.item_url, put_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['name'], put_dict['name'])

