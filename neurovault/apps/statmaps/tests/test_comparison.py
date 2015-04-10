from neurovault.apps.statmaps.tasks import save_voxelwise_pearson_similarity, get_images_by_ordered_id
from django.shortcuts import get_object_or_404
from neurovault.apps.statmaps.models import Image, Comparison, Similarity, User, Collection
from django.test import TestCase
from django.db import IntegrityError
import errno
from django.core.files.uploadedfile import SimpleUploadedFile
import os
import tempfile
import shutil
from neurovault.apps.statmaps.utils import split_afni4D_to_3D
import nibabel
from .utils import clearTestMediaRoot


class ComparisonTestCase(TestCase):
    pk1 = None
    pk2 = None
    pk1_copy = None
    pk2_copy = None
    pearson_metric = None
    
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.u1 = User.objects.create(username='neurovault')
        comparisonCollection = Collection(name='comparisonCollection',owner=self.u1)
        comparisonCollection.save()
        
        image1 = Image(name='image1', description='',collection=comparisonCollection)
        image1.file = SimpleUploadedFile('TTatlas.nii.gz', file(os.path.join(app_path,'test_data/TTatlas.nii.gz')).read())
        image1.save()
        self.pk1 = image1.id
        
        image2 = Image(name='image2', description='',collection=comparisonCollection)
        image2.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(app_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        image2.save()
        self.pk2 = image2.id
        
        image2 = Image(name='image2_copy', description='',collection=comparisonCollection)
        image2.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(app_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        image2.save()
        self.pk2_copy = image2.id
        
        bricks = split_afni4D_to_3D(nibabel.load(os.path.join(app_path,'test_data/TTatlas.nii.gz')),tmp_dir=self.tmpdir)
        
        image3 = Image(name='image3', description='',collection=comparisonCollection)
        image3.file = SimpleUploadedFile('brik1.nii.gz', file(bricks[0][1]).read())
        image3.save()
        self.pk3 = image3.id
        
        image4 = Image(name='image4', description='',collection=comparisonCollection)
        image4.file = SimpleUploadedFile('brik2.nii.gz', file(bricks[1][1]).read())
        image4.save()
        self.pk4 = image4.id
        
        self.pearson_metric = Similarity(similarity_metric="pearson product-moment correlation coefficient",
                                         transformation="voxelwise",
                                         metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                         transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")
        self.pearson_metric.save()
        
    def tearDown(self):
        clearTestMediaRoot()
        shutil.rmtree(self.tmpdir)
        clearDB()

    def test_save_pearson_similarity(self):
        with self.assertRaises(Exception):
            save_voxelwise_pearson_similarity(self.pk1,self.pk2)
        save_voxelwise_pearson_similarity(self.pk2,self.pk2_copy)
        save_voxelwise_pearson_similarity(self.pk2,self.pk3)
        save_voxelwise_pearson_similarity(self.pk2,self.pk4)
        save_voxelwise_pearson_similarity(self.pk3,self.pk4)
        
        image2, image2_copy = get_images_by_ordered_id(self.pk2, self.pk2_copy)
        comparison = Comparison.objects.filter(image1=image2,image2=image2_copy,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        self.assertEquals(comparison[0].similarity_score, 1.0)
        
        image3, image4 = get_images_by_ordered_id(self.pk3, self.pk4)
        comparison = Comparison.objects.filter(image1=image3,image2=image4,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        self.assertAlmostEqual(comparison[0].similarity_score, 0.295826311705968)
        
        comparison = Comparison.objects.filter(image1=image2,image2=image3,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        self.assertAlmostEqual(comparison[0].similarity_score, 0.019883382290693)
        
        comparison = Comparison.objects.filter(image1=image2,image2=image4,similarity_metric=self.pearson_metric)
        self.assertEqual(len(comparison), 1)
        self.assertAlmostEqual(comparison[0].similarity_score, -0.0244013809344553)
        
    
