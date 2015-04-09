from django.test import TestCase, Client
import xml.etree.ElementTree as ET
from neurovault.apps.statmaps.models import Atlas, Collection, Image,\
    StatisticMap
import os.path
from django.contrib.auth.models import User
from operator import itemgetter
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.forms import NIDMResultsForm
import json
from .utils import clearTestMediaRoot

class Test_Atlas_APIs(TestCase):
    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1',owner=self.user)
        self.Collection1.save()
        self.unorderedAtlas = Atlas(name='unorderedAtlas', description='',collection=self.Collection1)
        self.unorderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        self.unorderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(self.test_path,'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        self.unorderedAtlas.save()
        
        self.orderedAtlas = Atlas(name='orderedAtlas', collection=self.Collection1, label_description_file='VentralFrontal_thr75_summaryimage_2mm.xml')
        self.orderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        self.orderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        self.orderedAtlas.save()
        
        self.Image1 = StatisticMap(name='Image1', collection=self.Collection1, file='motor_lips.nii.gz', map_type="Z")
        self.Image1.file = SimpleUploadedFile('motor_lips.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/motor_lips.nii.gz')).read())
        self.Image1.save()
        
        self.Image2 = StatisticMap(name='Image2', collection=self.Collection1, file='beta_0001.nii.gz', map_type="Other")
        self.Image2.file = SimpleUploadedFile('beta_0001.nii.gz', file(os.path.join(self.test_path,'test_data/statmaps/beta_0001.nii.gz')).read())
        self.Image2.save()
        
        
        self.zip_file = open(os.path.join(self.test_path,'test_data/nidm/fsl.nidm.zip'), 'rb')
        self.post_dict = {
            'name': 'fsl_nidm',
            'description':'{0} upload test'.format('fsl_nidm'),
            'collection':self.Collection1.pk}
        self.fname = os.path.basename(os.path.join(self.test_path,'test_data/nidm/fsl.nidm.zip'))
        self.file_dict = {'zip_file': SimpleUploadedFile(self.fname, self.zip_file.read())}
        self.zip_file.close()
        self.form = NIDMResultsForm(self.post_dict, self.file_dict)
        self.nidm = self.form.save()
        
    def tearDown(self):
        clearTestMediaRoot()

    def test_query_region_out_of_order_indices(self):
        atlas_dir = os.path.join(self.test_path, 'test_data/api')
        tree = ET.parse(os.path.join(atlas_dir,'VentralFrontal_thr75_summaryimage_2mm.xml'))
        root = tree.getroot()
        atlasRegions = [x.text.lower() for x in root.find('data').findall('label')]
        for region in atlasRegions:
            orderedURL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=orderedAtlas&collection=Collection1' %region
            orderedResponse = self.client.get(orderedURL, follow=True)
            unorderedURL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=unorderedAtlas&collection=Collection1' %region
            unorderedResponse = self.client.get(unorderedURL, follow=True)
            orderedList = eval(orderedResponse.content)['voxels']
            unorderedList = eval(unorderedResponse.content)['voxels']
 
            orderedTriples = [(orderedList[0][i],orderedList[1][i],orderedList[2][i]) for i in range(len(orderedList[0]))]
            unorderedTriples = [(unorderedList[0][i],unorderedList[1][i],unorderedList[2][i]) for i in range(len(unorderedList[0]))]
            orderedSorted = sorted(orderedTriples, key=itemgetter(0))
            unorderedSorted = sorted(unorderedTriples, key=itemgetter(0))
             
            self.assertEqual(orderedSorted, unorderedSorted)
             
        testRegions = {'6v':[(58.00,-4.00,18.00),(62.00,6.00,30.00)], 'fop':[(56.00,20.00,24.00),(34.00,18.00,30.00)], 'fpm':[(8.00,62.00,10.00),(10.00,62.00,-16.00)]}
        for region, testVoxels in testRegions.items():
            URL = 'http://127.0.0.1:8000/api/atlases/atlas_query_region/?region=%s&atlas=orderedAtlas&collection=Collection1' %region
            response = self.client.get(URL, follow=True)
            voxelList = eval(response.content)['voxels']
            triples = [(voxelList[0][i],voxelList[1][i],voxelList[2][i]) for i in range(len(voxelList[0]))]
            for voxel in testVoxels:
                self.assertTrue(voxel in triples)
    def test_out_of_order_indices(self):
        testRegions = {'6v':[(58.00,-4.00,18.00),(62.00,6.00,30.00)], 'fop':[(56.00,20.00,24.00),(34.00,18.00,30.00)], 'fpm':[(8.00,62.00,10.00),(10.00,62.00,-16.00)]}
        for region, testVoxels in testRegions.items():
            for triple in testVoxels:
                X, Y, Z = triple[0], triple[1], triple[2]
                URL = 'http://127.0.0.1:8000/api/atlases/atlas_query_voxel/?x=%s&y=%s&z=%s&atlas=orderedAtlas&collection=Collection1' % (X, Y, Z)
                response = self.client.get(URL, follow=True)
                responseText = eval(response.content)
                self.assertEqual(responseText, region)
    
    def test_atlases(self):
        url = '/api/atlases/'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('.nii.gz' in response[0][u'file'])
        self.assertEqual(response[0]['name'], u'orderedAtlas')
    def test_atlases_pk(self):
        url = '/api/atlases/%d/' % self.unorderedAtlas.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('.nii.gz' in response[u'file'])
        self.assertEqual(response['name'], u'unorderedAtlas')
    def test_atlases_datatable(self):
        url = '/api/atlases/%d/datatable/' % self.unorderedAtlas.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('.xml' in response['aaData'][1][1])
    def test_atlases_regions_table(self):
        url = '/api/atlases/%d/regions_table/' % self.unorderedAtlas.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(response['aaData'][2][1], u'fop')
        self.assertEqual(response['aaData'][11][1], u'46')
    def test_collections(self):
        url = '/api/collections/'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(response[0][u'nidm_results'][0][u'name'], u'fsl.nidm')
        self.assertEqual(response[0][u'echo_time'], None)
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
        url = '/api/images/'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(response[0][u'name'], u'unorderedAtlas')
        self.assertEqual(response[4][u'name'], u'orderedAtlas')
    def test_images_pk(self):
        url = '/api/images/%d/' % self.Image1.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('http' in response['collection'])
        self.assertEqual(response['name'], 'Image1')
    def test_images_datatable(self):
        url = '/api/images/%d/datatable/' % self.Image2.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('http' in response['aaData'][0][1])
    def test_nidm_results(self):
        url = '/api/nidm_results/'
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertEqual(response[0][u'statmaps'][0][u'description'], 'NIDM Results: fsl.nidm.zip > TStatistic.nii.gz')
        self.assertEqual(response[0]['description'], u'fsl_nidm upload test')
    def test_nidm_results_pk(self):
        url = '/api/nidm_results/%d/' % self.nidm.pk
        response = json.loads(self.client.get(url, follow=True).content)
        self.assertTrue('fsl.nidm.ttl' in response['ttl_file'])
        self.assertEqual(response['statmaps'][0][u'figure'], None)
    
        