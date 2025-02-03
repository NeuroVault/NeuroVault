import nibabel as nb
import os
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import TestCase, Client

from neurovault.apps.statmaps.forms import StatisticMapForm
from neurovault.apps.statmaps.models import Collection, User, StatisticMap
from neurovault.apps.statmaps.utils import detect_4D, split_4D_to_3D
from neurovault.api.tests.utils import _setup_test_cognitive_atlas
from .utils import clearDB


class AddStatmapsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("NeuroGuy", password="pass")
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user, password="pass")
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()
        _setup_test_cognitive_atlas()

    def tearDown(self):
        clearDB()

    def testaddNiiGz(self):
        post_dict = {
            "name": "test map",
            "cognitive_task_choice": "yes_other",
            "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
            "modality": "fMRI-BOLD",
            "map_type": "T",
            "number_of_subjects": 10,
            "analysis_level": "G",
            "collection": self.coll.pk,
            "target_template_image": "GenericMNI",
        }
        testpath = os.path.abspath(os.path.dirname(__file__))
        fname = os.path.join(testpath, "test_data/statmaps/motor_lips.nii.gz")
        file_dict = {"file": SimpleUploadedFile(fname, open(fname, "rb").read())}
        post_dict.update(file_dict)
        form = StatisticMapForm(post_dict, file_dict)
        breakpoint()
        self.assertTrue(form.is_valid())

        form.save()

        self.assertEqual(
            StatisticMap.objects.filter(collection=self.coll.pk)[0].name, "test map"
        )

    @unittest.skip("Not supporting AFNI file uploads")
    def testaddAFNI(self):
        post_dict = {
            "name": "test map",
            "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
            "modality": "fMRI-BOLD",
            "map_type": "T",
            "number_of_subjects": 10,
            "analysis_level": "G",
            "collection": self.coll.pk,
            "target_template_image": "GenericMNI",
        }
        testpath = os.path.abspath(os.path.dirname(__file__))
        fname = os.path.join(testpath, "test_data/statmaps/saccade.I_C.MNI.nii.gz")

        nii = nb.load(fname)

        self.assertTrue(detect_4D(nii))
        self.assertTrue(len(split_4D_to_3D(nii)) > 0)

        file_dict = {"file": SimpleUploadedFile(fname, open(fname, "rb").read())}
        post_dict.update(file_dict)
        form = StatisticMapForm(post_dict, file_dict)

        self.assertTrue(form.is_valid())

        form.save()

        self.assertEqual(
            StatisticMap.objects.filter(collection=self.coll.pk).count(), 2
        )

    @unittest.skip("Not supporting separate hdr/img files")
    def testaddImgHdr(self):
        post_dict = {
            "name": "test map",
            "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
            "modality": "fMRI-BOLD",
            "map_type": "T",
            "number_of_subjects": 10,
            "analysis_level": "G",
            "collection": self.coll.pk,
            "target_template_image": "GenericMNI",
        }
        testpath = os.path.abspath(os.path.dirname(__file__))
        fname_img = os.path.join(testpath, "test_data/statmaps/box_0b_vs_1b.img")
        fname_hdr = os.path.join(testpath, "test_data/statmaps/box_0b_vs_1b.hdr")
        file_dict = {
            "file": SimpleUploadedFile(fname_img, open(fname_img, "rb").read()),
            "hdr_file": SimpleUploadedFile(fname_hdr, open(fname_hdr, "rb").read()),
        }
        post_dict.update(file_dict)
        form = StatisticMapForm(post_dict, file_dict)
        self.assertFalse(form.is_valid())
        self.assertTrue("thresholded" in form.errors["file"][0])

        post_dict = {
            "name": "test map",
            "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
            "modality": "fMRI-BOLD",
            "map_type": "T",
            "number_of_subjects": 10,
            "analysis_level": "G",
            "collection": self.coll.pk,
            "ignore_file_warning": True,
            "target_template_image": "GenericMNI",
        }
        testpath = os.path.abspath(os.path.dirname(__file__))
        fname_img = os.path.join(testpath, "test_data/statmaps/box_0b_vs_1b.img")
        fname_hdr = os.path.join(testpath, "test_data/statmaps/box_0b_vs_1b.hdr")
        file_dict = {
            "file": SimpleUploadedFile(fname_img, open(fname_img, "rb").read()),
            "hdr_file": SimpleUploadedFile(fname_hdr, open(fname_hdr, "rb").read()),
        }
        form = StatisticMapForm(post_dict, file_dict)
        self.assertTrue(form.is_valid())

        form.save()

        self.assertEqual(
            StatisticMap.objects.filter(collection=self.coll.pk)[0].name, "test map"
        )
