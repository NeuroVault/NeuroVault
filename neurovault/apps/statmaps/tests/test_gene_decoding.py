import uuid

from neurovault.apps.statmaps.tests.utils import (clearDB, save_atlas_form,
                                                  save_statmap_form,
                                                  save_nidm_form)
from neurovault.apps.statmaps.models import (Atlas, Collection,
                                             StatisticMap, NIDMResults)
from neurovault.apps.statmaps.urls import StandardResultPagination
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User, Permission
from django.test import TestCase, Client
from rest_framework.test import APITestCase
from rest_framework import status
import xml.etree.ElementTree as ET
from operator import itemgetter
import os.path
import json

from .test_nidm import NIDM_TEST_FILES


class TestGeneDecoding(TestCase):
    def setUp(self):
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1', owner=self.user)
        self.Collection1.save()

    def tearDown(self):
        clearDB()

    # Atlas Query Tests

    def test_validation(self):
        gene_validators = [{"map": 'test_data/gene_validation/WAY_HC36_mean.nii.gz',
                            "correct": ["HTR1A"]},
                           {"map": 'test_data/gene_validation/CUMl_BP_MNI.nii.gz',
                            "correct": ["HTR1A"],
                            #"incorrect": "DRD2", # negative correlation
                            },
                           {"map": 'test_data/gene_validation/18FDOPA.nii.gz',
                            "correct": ["DDC"]},
                           {"map": 'test_data/gene_validation/MNI152_WaterContent_figureAlignedForPaper_resliceForSTOLTUSanalysis.nii.gz',
                            "correct": [
                                #"MBP", #mislabeled Richardi gene
                                "MOG",
                                "MOBP"]},
                           {"map": 'test_data/gene_validation/RACLOPRIDE_TEMPLATE_inMNI_181_217_181.nii.gz',
                            "correct": ["DRD2"]},
                           {"map": 'test_data/gene_validation/123I-FP-CIT.nii.gz',
                            "correct": ["SLC6A3"]},
                           {"map": 'test_data/gene_validation/DASB_HC30_mean.nii.gz',
                            "correct": ["SLC6A4"]},
                           {"map": 'test_data/gene_validation/WAY_VT_MNI.nii.gz',
                            "correct": ["HTR1A"]},
                           {"map": 'test_data/gene_validation/P943_HC22_mean.nii.gz',
                            "correct": ["HTR1B"]},
                           {"map": 'test_data/gene_validation/ALT_HC19_mean.nii.gz',
                            "correct": ["HTR2A"]},
                           ]

        for d in gene_validators:
            nii_path = os.path.join(
                self.test_path, d["map"])
            map = save_statmap_form(
                image_path=nii_path, collection=self.Collection1)

            response = json.loads(self.client.get("/images/%d/gene_expression" % map.pk, follow=True).content)

            column_id = response["columns"].index("gene_symbol_richardi")
            for row in response["data"]:
                if row[column_id] in d["correct"]:
                    print dict(zip(response["columns"], row))
                    self.assertTrue(row[response["columns"].index('p (FDR corrected)')] < 0.05, msg=d["map"])

            if "incorrect" in d.keys():
                for row in response["data"]:
                    if row[column_id] == d["incorrect"]:
                        print row
                        self.assertTrue(row[response["columns"].index('p (FDR corrected)')] > 0.05, msg=d["map"])
                        break