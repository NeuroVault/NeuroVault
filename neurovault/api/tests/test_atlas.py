import os.path
import uuid
import json
from operator import itemgetter
import xml.etree.ElementTree as ET

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from neurovault.apps.statmaps.models import Atlas

from neurovault.apps.statmaps.tests.utils import (
    clearDB, save_atlas_form, save_nidm_form, save_statmap_form
)
from neurovault.apps.statmaps.models import Collection
from neurovault.api.tests.base import BaseTestCases
from neurovault.api.tests.base import STATMAPS_TESTS_PATH


class TestAtlas(APITestCase):

    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1', owner=self.user)
        self.Collection1.save()
        self.unorderedAtlas = Atlas(
            name='unorderedAtlas', description='', collection=self.Collection1)

        # Save new atlas object, unordered
        print "Adding unordered and ordered atlas..."
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
        self.unorderedAtlas = save_atlas_form(nii_path=nii_path,
                                              xml_path=xml_path,
                                              collection=self.Collection1,
                                              name="unorderedAtlas")
        # Ordered
        nii_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'
        )
        xml_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml'
        )
        self.orderedAtlas = save_atlas_form(nii_path=nii_path,
                                            xml_path=xml_path,
                                            collection=self.Collection1,
                                            name="orderedAtlas")

        # Statistical Map 1 and 2
        print "Adding statistical maps..."
        nii_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/statmaps/motor_lips.nii.gz'
        )
        self.Image1 = save_statmap_form(
            image_path=nii_path, collection=self.Collection1)
        nii_path = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/statmaps/beta_0001.nii.gz'
        )
        self.Image2 = save_statmap_form(
            image_path=nii_path, collection=self.Collection1)

        # Zip file with nidm results
        print "Adding nidm results..."
        zip_file = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/nidm/spm_example.nidm.zip'
        )
        self.nidm = save_nidm_form(
            zip_file=zip_file, collection=self.Collection1)

    def tearDown(self):
        clearDB()

    # Atlas Query Tests

    def test_query_region_out_of_order_indices(self):

        print "\nAssessing equality of ordered vs. unordered atlas query..."
        atlas_dir = os.path.join(
            self.test_path,
            STATMAPS_TESTS_PATH,
            'test_data/api'
        )
        tree = ET.parse(os.path.join(
            atlas_dir, 'VentralFrontal_thr75_summaryimage_2mm.xml'
        ))
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


class TestAtlasChange(BaseTestCases.TestCollectionItemChange):
    def setUp(self):
        super(TestAtlasChange, self).setUp()

        nii_path = self.abs_file_path(
            STATMAPS_TESTS_PATH
            + 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'
        )
        xml_path = self.abs_file_path(
            STATMAPS_TESTS_PATH
            + 'test_data/api/'
            + 'unordered_VentralFrontal_thr75_summaryimage_2mm.xml'
        )
        self.item = save_atlas_form(nii_path=nii_path,
                                    xml_path=xml_path,
                                    collection=self.coll,
                                    name="unorderedAtlas")

        self.item_url = '/api/atlases/%s/' % self.item.pk

    def test_atlas_update(self):
        self.client.force_authenticate(user=self.user)

        nii_file = self.simple_uploaded_file(
            STATMAPS_TESTS_PATH
            + 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'
        )
        xml_file = self.simple_uploaded_file(
            STATMAPS_TESTS_PATH
            + 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml'
        )

        put_dict = {
            'name': "renamed %s" % uuid.uuid4(),
            'file': nii_file,
            'label_description_file': xml_file
        }

        response = self.client.put(self.item_url, put_dict)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], put_dict['name'])

    def test_atlas_destroy(self):
        self._test_collection_item_destroy(Atlas)
