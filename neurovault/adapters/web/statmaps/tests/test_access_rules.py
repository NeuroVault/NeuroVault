"""Access rules on the web write paths (review of #866: H1, M5, M6)."""
import json
import os

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from neurovault.adapters.api.tests.utils import _setup_test_cognitive_atlas
from neurovault.adapters.persistence.models import Collection, Item
from .utils import clearDB, persist

DATA = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_data")


def data_file(rel):
    with open(os.path.join(DATA, rel), "rb") as f:
        return SimpleUploadedFile(os.path.basename(rel), f.read())


class WebAccessRules(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.stranger = User.objects.create_user("stranger", password="pw")
        _setup_test_cognitive_atlas()
        self.mine = persist(Collection(owner=self.owner, name="mine"))
        self.theirs = persist(Collection(owner=self.stranger, name="theirs", private=True,
                                         private_token="THEIRSXX"))
        self.client.defaults["HTTP_HOST"] = "testserver"
        self.client.force_login(self.owner)
        self.client.post(reverse("statmaps:upload_folder", args=[self.mine.pk]),
                         {"file": data_file("statmaps/motor_lips.nii.gz")})
        self.image = Item.objects.get(collection=self.mine)

    def tearDown(self):
        clearDB()

    def edit(self, collection_id):
        return self.client.post(
            reverse("statmaps:edit_image", args=[self.image.pk]),
            {
                "name": "moved", "collection": collection_id, "map_type": "T",
                "modality": "fMRI-BOLD", "target_template_image": "GenericMNI",
                "analysis_level": "G", "number_of_subjects": 10, "cognitive_task_choice": "none",
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011", "submit_save": "Save and Exit",
            },
        )

    def test_cannot_move_a_map_into_someone_elses_collection(self):
        r = self.edit(self.theirs.pk)
        self.assertEqual(r.status_code, 200)
        self.assertIn("collection", r.context["form"].errors)
        self.image.refresh_from_db()
        self.assertEqual(self.image.collection_id, self.mine.pk)
        self.assertIn("images/%s/" % self.mine.pk, self.image.file.name)
        self.assertEqual(self.theirs.items.count(), 0)

    def test_can_move_a_map_into_another_own_collection(self):
        other = persist(Collection(owner=self.owner, name="other"))
        r = self.edit(other.pk)
        self.assertEqual(r.status_code, 302)
        self.image.refresh_from_db()
        self.assertEqual(self.image.collection_id, other.pk)

    def test_upload_into_someone_elses_collection_is_forbidden(self):
        public = persist(Collection(owner=self.stranger, name="public theirs"))
        r = self.client.post(reverse("statmaps:upload_folder", args=[public.pk]),
                             {"file": data_file("statmaps/motor_lips.nii.gz")})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(public.items.count(), 0)

    def test_neurosynth_form_cannot_target_someone_elses_collection(self):
        self.client.get(reverse("statmaps:add_for_neurosynth"))
        r = self.client.post(
            reverse("statmaps:add_for_neurosynth"),
            {
                "collection": self.theirs.pk, "name": "x", "map_type": "T",
                "modality": "fMRI-BOLD", "target_template_image": "GenericMNI",
                "cognitive_task_choice": "none", "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
                "file": data_file("statmaps/motor_lips.nii.gz"),
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.theirs.items.count(), 0)

    def test_nidm_map_stays_in_its_collection(self):
        client = APIClient()
        client.force_authenticate(user=self.owner)
        r = client.post("/api/collections/%s/nidm_results/" % self.mine.pk,
                        {"name": "n", "description": "d",
                         "zip_file": data_file("nidm/spm_example.nidm.zip")}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        nidm_map = Item.objects.nidm_statmaps().get(collection=self.mine)
        other = persist(Collection(owner=self.owner, name="other"))
        r = self.client.post(reverse("statmaps:edit_image", args=[nidm_map.pk]),
                             {"name": nidm_map.name, "collection": other.pk, "map_type": "T",
                              "submit_save": "Save and Exit"})
        nidm_map.refresh_from_db()
        self.assertEqual(nidm_map.collection_id, self.mine.pk)
