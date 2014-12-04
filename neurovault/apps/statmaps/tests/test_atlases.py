from django.test import TestCase
import xml.etree.ElementTree as ET
from neurovault.apps.statmaps.models import Atlas, Collection
from django.db import models
import os.path
from django.contrib.auth.models import User
import neurovault
from operator import itemgetter

class TestGetAtlasVoxels(TestCase):
    
    
    def test_out_of_order_indices(self):

        self.u1 = User.objects.create(username='neurovault')
        atlasCollection = Collection(name='atlasCollection',owner=self.u1)
        atlasCollection.save()
        unorderAtlas = Atlas(name='unorderAtlas', description='',collection=atlasCollection, file='images/11/VentralFrontal_thr75_summaryimage_2mm.nii.gz', label_description_file='images/11/test_VentralFrontal_thr75_summaryimage_2mm.xml')
        unorderAtlas.save()
        orderAtlas = Atlas(name='orderAtlas', collection=atlasCollection, file='images/11/VentralFrontal_thr75_summaryimage_2mm.nii.gz', label_description_file='images/11/VentralFrontal_thr75_summaryimage_2mm.xml')
        orderAtlas.save()
        neurovault_root = os.path.dirname(os.path.dirname(os.path.realpath(neurovault.__file__)))
        atlas_dir = os.path.join(neurovault_root, 'private_media/')
        tree = ET.parse(os.path.join(atlas_dir,'images/11/VentralFrontal_thr75_summaryimage_2mm.xml'))
        root = tree.getroot()
        atlasRegions = [x.text.lower() for x in root[1]]
        for region in atlasRegions:
            orderURL = 'http://127.0.0.1:8000/api/atlas_query_region/?region=%s&atlas=orderAtlas' %region
            orderResponse = self.client.get(orderURL, follow=True)
            unorderURL = 'http://127.0.0.1:8000/api/atlas_query_region/?region=%s&atlas=unorderAtlas' %region
            unorderResponse = self.client.get(unorderURL, follow=True)
            orderList = eval(orderResponse.content)['voxels']
            unorderList = eval(unorderResponse.content)['voxels']

            orderTriples = [(orderList[0][i],orderList[1][i],orderList[2][i]) for i in range(len(orderList[0]))]
            unorderTriples = [(unorderList[0][i],unorderList[1][i],unorderList[2][i]) for i in range(len(unorderList[0]))]
            orderSorted = sorted(orderTriples, key=itemgetter(0))
            unorderSorted = sorted(unorderTriples, key=itemgetter(0))

            self.assertEqual(orderSorted, unorderSorted)
            