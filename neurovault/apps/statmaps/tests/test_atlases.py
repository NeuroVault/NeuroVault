from django.test import TestCase
import xml.etree.ElementTree as ET
from neurovault.apps.statmaps.models import Atlas, Collection
from django.db import models
import os.path
from django.contrib.auth.models import User
import neurovault
from operator import itemgetter
from django.core.files.uploadedfile import SimpleUploadedFile

class Test_atlas_queries(TestCase):
    def setUp(self):
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.u1 = User.objects.create(username='neurovault')
        atlasCollection = Collection(name='atlasCollection',owner=self.u1)
        atlasCollection.save()
        unorderedAtlas = Atlas(name='unorderedAtlas', description='',collection=atlasCollection)
        unorderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(app_path,'test_data/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        unorderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(app_path,'test_data/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        unorderedAtlas.save()
        
        orderedAtlas = Atlas(name='orderedAtlas', collection=atlasCollection, file='VentralFrontal_thr75_summaryimage_2mm.nii.gz', label_description_file='VentralFrontal_thr75_summaryimage_2mm.xml')
        orderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(app_path,'test_data/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        orderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(app_path,'test_data/VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        orderedAtlas.save()
    def test_query_region_out_of_order_indices(self):
        app_path = os.path.abspath(os.path.dirname(__file__))

        
        atlas_dir = os.path.join(app_path, 'test_data')
        tree = ET.parse(os.path.join(atlas_dir,'VentralFrontal_thr75_summaryimage_2mm.xml'))
        root = tree.getroot()
        atlasRegions = [x.text.lower() for x in root.find('data').findall('label')]
        for region in atlasRegions:
            orderedURL = 'http://127.0.0.1:8000/api/atlas_query_region/?region=%s&atlas=orderedAtlas' %region
            orderedResponse = self.client.get(orderedURL, follow=True)
            unorderedURL = 'http://127.0.0.1:8000/api/atlas_query_region/?region=%s&atlas=unorderedAtlas' %region
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
            URL = 'http://127.0.0.1:8000/api/atlas_query_region/?region=%s&atlas=orderedAtlas' %region
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
                URL = 'http://127.0.0.1:8000/api/atlas_query_voxel/?x=%s&y=%s&z=%s&atlas=orderedAtlas' % (X, Y, Z)
                response = self.client.get(URL, follow=True)
                responseText = eval(response.content)
                self.assertEqual(responseText, region)
         
    
        