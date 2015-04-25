from neurovault.apps.statmaps.tests.utils import clearDB, save_atlas_form, save_statmap_form, save_nidm_form
from neurovault.apps.statmaps.models import Atlas, Collection, Image, StatisticMap
from neurovault.apps.statmaps.urls import StandardResultPagination
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase, Client
import xml.etree.ElementTree as ET
from operator import itemgetter
import os.path
import json

class Test_Atlas_APIs(TestCase):
    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1',owner=self.user)
        self.Collection1.save()
        self.unorderedAtlas = Atlas(name='unorderedAtlas', description='',collection=self.Collection1)
        
        # Save new atlas object, unordered
        print "Adding unordered and ordered atlas..."
        nii_path = os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')
        xml_path = os.path.join(self.test_path,'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')
        self.unorderedAtlas = save_atlas_form(nii_path=nii_path,
                              xml_path=xml_path,
                              collection=self.Collection1,
                              name = "unorderedAtlas")
        # Ordered
        nii_path = os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')
        xml_path = os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml')
        self.orderedAtlas = save_atlas_form(nii_path=nii_path,
                              xml_path=xml_path,
                              collection=self.Collection1,
                              name = "orderedAtlas")

        # Statistical Map 1 and 2
        print "Adding statistical maps..."
        nii_path = os.path.join(self.test_path,'test_data/statmaps/motor_lips.nii.gz') 
        self.Image1 = save_statmap_form(image_path=nii_path, collection=self.Collection1)
        nii_path = os.path.join(self.test_path,'test_data/statmaps/beta_0001.nii.gz') 
        self.Image2 = save_statmap_form(image_path=nii_path, collection=self.Collection1)
  
        # Zip file with nidm results
        print "Adding nidm results..."
        zip_file = os.path.join(self.test_path,'test_data/nidm/fsl.nidm.zip')  
        self.nidm = save_nidm_form(zip_file=zip_file,collection=self.Collection1)
            

    def tearDown(self):
        clearDB()

### Atlas Query Tests

    def test_query_region_out_of_order_indices(self):
        
        print "\nAssessing equality of ordered vs. unordered atlas query..."
        atlas_dir = os.path.join(self.test_path, 'test_data/api')
        tree = ET.parse(os.path.join(atlas_dir,'VentralFrontal_thr75_summaryimage_2mm.xml'))
        root = tree.getroot()
        atlasRegions = [x.text.lower() for x in root.find('data').findall('label')]
        for region in atlasRegions:
            orderedURL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=orderedAtlas&collection=Collection1' %(region)
            orderedResponse = self.client.get(orderedURL, follow=True)
            unorderedURL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=unorderedAtlas&collection=Collection1' %(region)
            unorderedResponse = self.client.get(unorderedURL, follow=True)
            orderedList = eval(orderedResponse.content)['voxels']
            unorderedList = eval(unorderedResponse.content)['voxels']
            orderedTriples = [(orderedList[0][i],orderedList[1][i],
                               orderedList[2][i]) for i in range(len(orderedList[0]))]
            unorderedTriples = [(unorderedList[0][i],unorderedList[1][i],
                                 unorderedList[2][i]) for i in range(len(unorderedList[0]))]
            orderedSorted = sorted(orderedTriples, key=itemgetter(0))
            unorderedSorted = sorted(unorderedTriples, key=itemgetter(0))
            print "Equality of lists for region %s: %s" %(region,orderedSorted==unorderedSorted) 
            self.assertEqual(orderedSorted, unorderedSorted)

        print "\nAssessing consistency of results for regional query..."             
        testRegions = {'6v':[(58.00,-4.00,18.00),(62.00,6.00,30.00)], 
                       'fop':[(56.00,20.00,24.00),(34.00,18.00,30.00)], 
                       'fpm':[(8.00,62.00,10.00),(10.00,62.00,-16.00)]}
        for region, testVoxels in testRegions.items():
            URL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=orderedAtlas&collection=Collection1' %(region)
            response = self.client.get(URL, follow=True)
            voxelList = eval(response.content)['voxels']
            triples = [(voxelList[0][i],voxelList[1][i],voxelList[2][i]) for i in range(len(voxelList[0]))]
            for voxel in testVoxels:
                self.assertTrue(voxel in triples)


    def test_out_of_order_indices(self):
        print "\nAssessing consistency of results for coordinate query..."             
        testRegions = {'6v':[(58.00,-4.00,18.00),(62.00,6.00,30.00)],
                       'fop':[(56.00,20.00,24.00),(34.00,18.00,30.00)],
                       'fpm':[(8.00,62.00,10.00),(10.00,62.00,-16.00)]}        

        for region, testVoxels in testRegions.items():
            for triple in testVoxels:
                X, Y, Z = triple[0],triple[1],triple[2]
                URL = 'http://127.0.0.1:8000/api/atlases/atlas_query_voxel/?x=%s&y=%s&z=%s&atlas=orderedAtlas&collection=Collection1' % (X,Y,Z)
                response = self.client.get(URL, follow=True)
                responseText = eval(response.content)
                self.assertEqual(responseText, region)
    

### General API Tests

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
        self.assertTrue('.xml' in response['aaData'][1][1])

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
        self.assertEqual(response['results'][0][u'nidm_results'][0][u'name'], u'fsl.nidm')
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
        self.assertEqual(collection_name, u'Collection1' )

    def test_images(self):
        print "\nTesting images API...."
        url = '/api/images/'
        response = json.loads(self.client.get(url, follow=True).content)
        names = [item[u'name'] for item in response['results']]
        self.assertTrue(u'unorderedAtlas' in names)
        self.assertTrue(u'Z-Statistic Map: Generation' in names)

    def test_images_pk(self):
        url = '/api/images/%d/' % self.Image1.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('http' in response['collection'])
        self.assertEqual(response['name'], u'/opt/nv_env/NeuroVault/neurovault/apps/statmaps/tests/test_data/statmaps/motor_lips.nii.gz')

    def test_images_datatable(self):
        url = '/api/images/%d/datatable/' % self.Image2.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('http' in response['aaData'][1][1])

    def test_nidm_results(self):
        print "\nTesting NIDM results API...."
        url = '/api/nidm_results/'
        response = json.loads(self.client.get(url, follow=True).content)
        descriptions = [item[u'description'] for item in response['results'][0][u'statmaps']]
        self.assertTrue('NIDM Results: fsl.nidm.zip > TStatistic.nii.gz' in descriptions)
        self.assertEqual(response['results'][0]['description'], u'fsl_nidm upload test')

    def test_nidm_results_pk(self):
        url = '/api/nidm_results/%d/' % self.nidm.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('fsl.nidm.ttl' in response['ttl_file'])
        self.assertEqual(response['statmaps'][0][u'figure'], None)


### Pagination

    def test_pagination(self):
        print "\nTesting API pagination..."
        print "Max limit is set to %s" %(StandardResultPagination.max_limit)
        self.assertEqual(1000,StandardResultPagination.max_limit)
        print "Default limit is set to %s" %(StandardResultPagination.default_limit)
        self.assertEqual(100,StandardResultPagination.default_limit)
        print "Page size (equal to default) is set to %s" %(StandardResultPagination.PAGE_SIZE)
        self.assertEqual(100,StandardResultPagination.PAGE_SIZE)

        url = '/api/images/?limit=1'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(1,len(response['results']))
        url = '/api/images/?limit=2'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(2,len(response['results']))
