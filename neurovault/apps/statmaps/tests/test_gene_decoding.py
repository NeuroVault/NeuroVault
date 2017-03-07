from neurovault.apps.statmaps.tasks import save_resampled_transformation_single
from neurovault.apps.statmaps.tests.utils import (clearDB, save_statmap_form)
from neurovault.apps.statmaps.models import (Collection)
from django.contrib.auth.models import User
from django.test import TestCase, Client
import pandas as pd
import os.path
import json


class TestGeneDecoding(TestCase):
    _map = None

    @classmethod
    def setUpClass(cls):
        cls.test_path = os.path.abspath(os.path.dirname(__file__))
        cls.user, _ = User.objects.get_or_create(username='neurovault')
        cls.client = Client()
        cls.client.login(username=cls.user)
        cls.Collection1 = Collection(name='Collection1', owner=cls.user)
        cls.Collection1.save()

        nii_path = os.path.join(
            cls.test_path, cls._map)
        map = save_statmap_form(
            image_path=nii_path, collection=cls.Collection1)
        save_resampled_transformation_single(map.pk)
        response = json.loads(cls.client.get("/images/%d/gene_expression/json&mask=full" % map.pk, follow=True).content)
        cls.df = pd.DataFrame(response["data"], columns=response["columns"])

    @classmethod
    def tearDownClass(cls):
        clearDB()
        cls.user.delete()

    def _assess_gene(self, gene_name, field='t'):
        value = self.df.loc[self.df['gene_symbol'] == gene_name][field]

        self.assertEquals(len(value), 1)

        value = list(value)[0]

        self.assertGreaterEqual(value, 0.0)

    def _assess_gene_relation(self, gene_name1, gene_name2, field='variance explained (mean)'):
        value1 = self.df.loc[self.df['gene_symbol'] == gene_name1][field]
        self.assertEquals(len(value1), 1)

        value2 = self.df.loc[self.df['gene_symbol'] == gene_name2][field]
        self.assertEquals(len(value2), 1)

        value1 = list(value1)[0]
        value2 = list(value2)[0]

        self.assertGreater(value1, value2)


class TestWAY1(TestGeneDecoding):
    _map = 'test_data/gene_validation/WAY_HC36_mean.nii.gz'

    def test_positive_HTR1A(self):
        self._assess_gene("HTR1A")


# class TestCUM1(TestGeneDecoding):
#     _map = 'test_data/gene_validation/CUMl_BP_MNI.nii.gz'
#
#     def test_HTR1A_greater_DRD2(self):
#         self._assess_gene_relation("HTR1A", "DRD2")
#
#
# class TestFDOPA(TestGeneDecoding):
#     _map = 'test_data/gene_validation/18FDOPA.nii.gz'
#
#     def test_positive_DDC(self):
#         self._assess_gene("DDC")
#
#
# class TestMWC(TestGeneDecoding):
#     _map = 'test_data/gene_validation/MNI152_WaterContent_figureAlignedForPaper_resliceForSTOLTUSanalysis.nii.gz'
#
#     def test_MBP_greater_DDC(self):
#         self._assess_gene_relation("MBP", "DDC")
#
#     def test_MOG_greater_DDC(self):
#         self._assess_gene_relation("MOG", "DDC")
#
#     def test_MOBP_greater_DDC(self):
#         self._assess_gene_relation("MOBP", "DDC")
#
#
# class TestRACLOPRIDE(TestGeneDecoding):
#     _map = 'test_data/gene_validation/RACLOPRIDE_TEMPLATE_inMNI_181_217_181.nii.gz'
#
#     def test_positive_DRD2(self):
#         self._assess_gene("DRD2")
#
#
# class TestFP_CIT(TestGeneDecoding):
#     _map = 'test_data/gene_validation/123I-FP-CIT.nii.gz'
#
#     def test_positive_SLC6A3_greater_HTR1A(self):
#         self._assess_gene_relation("SLC6A3", "HTR1A")
#
#
# class TestDASB(TestGeneDecoding):
#     _map = 'test_data/gene_validation/DASB_HC30_mean.nii.gz'
#
#     def test_positive_SLC6A4(self):
#         self._assess_gene("SLC6A4")
#
#
# class TestWAY2(TestGeneDecoding):
#     _map = 'test_data/gene_validation/WAY_VT_MNI.nii.gz'
#
#     def test_positive_HTR1A(self):
#         self._assess_gene("HTR1A")
#
#
# #class TestP943(TestGeneDecoding):
# #    _map = 'test_data/gene_validation/P943_HC22_mean.nii.gz'
# #
# #    def test_positive_HTR1B(self):
# #        self._assess_gene("HTR1B")
#
#
# class TestALTANSERIN(TestGeneDecoding):
#     _map = 'test_data/gene_validation/ALT_HC19_mean.nii.gz'
#
#     def test_positive_HTR1B(self):
#         self._assess_gene("HTR2A")
