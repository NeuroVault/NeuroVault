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
        cls.user = User.objects.create(username='neurovault')
        cls.client = Client()
        cls.client.login(username=cls.user)
        cls.Collection1 = Collection(name='Collection1', owner=cls.user)
        cls.Collection1.save()

        nii_path = os.path.join(
            cls.test_path, cls._map)
        map = save_statmap_form(
            image_path=nii_path, collection=cls.Collection1)
        response = json.loads(cls.client.get("/images/%d/gene_expression" % map.pk, follow=True).content)
        cls.df = pd.DataFrame(response["data"], columns=response["columns"])

    @classmethod
    def tearDownClass(cls):
        clearDB()

    def _assess_gene(self, gene_name, positive, field='variance explained (mean)'):
        value = self.df.loc[self.df['gene_symbol_richardi'] == gene_name][field]

        self.assertEquals(len(value), 1)

        value = list(value)[0]

        if positive:
            self.assertGreater(value, 10)
        else:
            self.assertLessEqual(value, 10)


class TestWAY1(TestGeneDecoding):
    _map = 'test_data/gene_validation/WAY_HC36_mean.nii.gz'

    def test_positive_HTR1A(self):
        self._assess_gene("HTR1A", True)


class TestCUM1(TestGeneDecoding):
    _map = 'test_data/gene_validation/CUMl_BP_MNI.nii.gz'

    def test_positive_HTR1A(self):
        self._assess_gene("HTR1A", True)

    def test_negative_DRD2(self):
        self._assess_gene("DRD2", False)


class TestFDOPA(TestGeneDecoding):
    _map = 'test_data/gene_validation/18FDOPA.nii.gz'

    def test_positive_DDC(self):
        self._assess_gene("DDC", True)


class TestMWC(TestGeneDecoding):
    _map = 'test_data/gene_validation/MNI152_WaterContent_figureAlignedForPaper_resliceForSTOLTUSanalysis.nii.gz'

    def test_positive_MBP(self):
        self._assess_gene("MBP", True)

    def test_positive_MOG(self):
        self._assess_gene("MOG", True)

    def test_positive_MOBP(self):
        self._assess_gene("MOBP", True)

    def test_negative_DDC(self):
        self._assess_gene("DDC", False)


class TestRACLOPRIDE(TestGeneDecoding):
    _map = 'test_data/gene_validation/RACLOPRIDE_TEMPLATE_inMNI_181_217_181.nii.gz'

    def test_positive_DRD2(self):
        self._assess_gene("DRD2", True)


class TestFP_CIT(TestGeneDecoding):
    _map = 'test_data/gene_validation/123I-FP-CIT.nii.gz'

    def test_positive_SLC6A3(self):
        self._assess_gene("SLC6A3", True)

    def test_negative_HTR1A(self):
        self._assess_gene("HTR1A", False)


class TestDASB(TestGeneDecoding):
    _map = 'test_data/gene_validation/DASB_HC30_mean.nii.gz'

    def test_positive_SLC6A4(self):
        self._assess_gene("SLC6A4", True)


class TestWAY2(TestGeneDecoding):
    _map = 'test_data/gene_validation/WAY_VT_MNI.nii.gz'

    def test_positive_HTR1A(self):
        self._assess_gene("HTR1A", True)


class TestP943(TestGeneDecoding):
    _map = 'test_data/gene_validation/P943_HC22_mean.nii.gz'

    def test_positive_HTR1B(self):
        self._assess_gene("HTR1B", True)


class TestALTANSERIN(TestGeneDecoding):
    _map = 'test_data/gene_validation/ALT_HC19_mean.nii.gz'

    def test_positive_HTR1B(self):
        self._assess_gene("HTR2A", True)
