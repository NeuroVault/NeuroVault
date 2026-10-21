"""Characterization tests for the web flows the refactor rewrites.

They observe behaviour only through HTTP (web pages and the public API), so
they do not depend on how models, forms or services are arranged and must keep
passing unchanged through every phase of docs/design/0001.
"""
import io
import json
import os
import re
import tempfile
import unittest
import zipfile

import nibabel as nb
import numpy as np

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from neurovault.api.tests.utils import _setup_test_cognitive_atlas
from .utils import clearDB

DATA = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_data")


def form_errors(response):
    form = response.context and response.context.get("form")
    return form.errors if form is not None else response.content


def data_file(rel, name=None):
    with open(os.path.join(DATA, rel), "rb") as f:
        return SimpleUploadedFile(name or os.path.basename(rel), f.read())


class WebFlows(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", email="owner@example.org", password="pw")
        self.contrib = User.objects.create_user("contrib", email="contrib@example.org", password="pw")
        self.stranger = User.objects.create_user("stranger", password="pw")
        _setup_test_cognitive_atlas()
        self.client.defaults["HTTP_HOST"] = "testserver"
        self.client.force_login(self.owner)

    def tearDown(self):
        clearDB()

    # ------------------------------------------------------------ helpers

    def api(self, url):
        client = APIClient()
        client.force_authenticate(user=self.owner)
        r = client.get(url)
        self.assertEqual(r.status_code, 200, r.content)
        return json.loads(r.content)

    def create_collection(self, name="Web Collection", private=False):
        r = self.client.post(
            reverse("statmaps:new_collection"),
            {"name": name, "publication_status": "in_preparation", "private": private,
             "description": "made on the web"},
        )
        self.assertEqual(r.status_code, 302, form_errors(r))
        cid = r["Location"].rstrip("/").split("/")[-1]
        return cid

    def collection_id(self, name):
        for c in self.api("/api/my_collections/")["results"]:
            if c["name"] == name:
                return c["id"]
        raise AssertionError("collection %s not found" % name)

    def upload(self, cid, uploaded):
        return self.client.post(reverse("statmaps:upload_folder", args=[cid]), {"file": uploaded})

    def images(self, cid):
        return self.api("/api/collections/%s/images/" % cid)["results"]

    def api_post(self, url, data):
        client = APIClient()
        client.force_authenticate(user=self.owner)
        r = client.post(url, data, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        return json.loads(r.content)

    def upload_nidm_via_api(self, cid):
        return self.api_post("/api/collections/%s/nidm_results/" % cid,
                             {"name": "spm_example", "description": "nidm",
                              "zip_file": data_file("nidm/spm_example.nidm.zip")})

    def upload_atlas_via_api(self, cid):
        return self.api_post("/api/collections/%s/atlases/" % cid, {
            "name": "web atlas",
            "file": data_file("api/VentralFrontal_thr75_summaryimage_2mm.nii.gz"),
            "label_description_file": data_file("api/VentralFrontal_thr75_summaryimage_2mm.xml"),
        })

    def thresholded_file(self):
        nii = nb.load(os.path.join(DATA, "statmaps/motor_lips.nii.gz"))
        data = np.asanyarray(nii.dataobj).copy()
        flat = data.reshape(-1)
        flat[: int(flat.size * 0.95)] = 0
        path = os.path.join(tempfile.mkdtemp(), "thresholded.nii.gz")
        nb.save(nb.Nifti1Image(data, nii.affine), path)
        with open(path, "rb") as f:
            return SimpleUploadedFile("thresholded.nii.gz", f.read())

    # -------------------------------------------------------------- tests

    def test_collection_lifecycle_and_sharing(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")

        # owner sees the edit page; contributor-to-be and stranger do not
        edit = reverse("statmaps:edit_collection", args=[cid])
        self.assertEqual(self.client.get(edit).status_code, 200)
        self.client.force_login(self.contrib)
        self.assertEqual(self.client.get(edit).status_code, 403)

        # owner adds a contributor: they get an email and edit rights, not delete rights
        self.client.force_login(self.owner)
        r = self.client.post(edit, {"name": "Web Collection", "publication_status": "in_preparation",
                                    "private": False, "contributors": "contrib"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual([m.to for m in mail.outbox], [["contrib@example.org"]])
        self.client.force_login(self.contrib)
        self.assertEqual(self.client.get(edit).status_code, 200)
        self.assertEqual(self.client.get(reverse("statmaps:delete_collection", args=[cid])).status_code, 403)

        # contributor can upload and edit images in the collection
        self.assertEqual(self.upload(cid, data_file("statmaps/motor_lips.nii.gz")).status_code, 302)
        image_id = self.images(cid)[0]["id"]
        self.assertEqual(self.client.get(reverse("statmaps:edit_image", args=[image_id])).status_code, 200)

        # removing the contributor revokes access to the collection and its images
        self.client.force_login(self.owner)
        self.client.post(edit, {"name": "Web Collection", "publication_status": "in_preparation",
                                "private": False, "contributors": ""})
        self.client.force_login(self.contrib)
        self.assertEqual(self.client.get(edit).status_code, 403)
        self.assertEqual(self.client.get(reverse("statmaps:edit_image", args=[image_id])).status_code, 403)
        self.assertEqual(self.client.get(reverse("statmaps:delete_image", args=[image_id])).status_code, 403)

        # owner deletes the collection
        self.client.force_login(self.owner)
        r = self.client.get(reverse("statmaps:delete_collection", args=[cid]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/api/collections/%s/" % cid).status_code, 404)

    def test_upload_single_file_creates_invalid_statmap_and_processes_it(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        r = self.upload(cid, data_file("statmaps/motor_lips.nii.gz", "spmT_0001.nii.gz"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("bulk=True", r["Location"])
        self.assertIn("/edit", r["Location"])

        [img] = self.images(cid)
        self.assertEqual(img["image_type"], "statistic_map")
        self.assertEqual(img["name"], "spmT 0001")
        self.assertEqual(img["map_type"], "T map")
        self.assertFalse(img["is_valid"])
        # process_map ran: thumbnail and surface projections exist
        self.assertRegex(img["thumbnail"], r"glass_brain_\d+\.jpg$")
        self.assertRegex(img["surface_left_file"], r"\.L\.func\.gii$")
        self.assertRegex(img["surface_right_file"], r"\.R\.func\.gii$")
        self.assertGreater(img["file_size"], 0)

    def test_upload_zip_of_maps_and_atlas(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.write(os.path.join(DATA, "statmaps/motor_lips.nii.gz"), "maps/motor_lips.nii.gz")
            zf.write(os.path.join(DATA, "statmaps/beta_0001.nii.gz"), "maps/spmF_0002.nii.gz")
        r = self.upload(cid, SimpleUploadedFile("maps.zip", buf.getvalue()))
        self.assertEqual(r.status_code, 302)
        got = sorted((i["name"], i["map_type"], i["is_valid"]) for i in self.images(cid))
        self.assertEqual(got, [("motor lips", "other", False), ("spmF 0002", "F map", False)])

    @unittest.expectedFailure  # master: populate_nidm_results mutates the immutable request.POST
    def test_upload_nidm_through_upload_folder(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        r = self.upload(cid, data_file("nidm/spm_example.nidm.zip"))
        self.assertEqual(r.status_code, 302)
        [bundle] = self.api("/api/collections/%s/nidm_results/" % cid)["results"]
        self.assertEqual(bundle["name"], "spm_example.nidm")
        self.assertEqual(len(bundle["statmaps"]), 1)
        self.assertEqual(bundle["statmaps"][0]["image_type"], "NIDM results statistic map")
        # NIDM statmaps are served from the bundle directory
        self.assertEqual(self.client.get(bundle["statmaps"][0]["url"]).status_code, 200)

    def test_edit_image_completes_metadata(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        [img] = self.images(cid)
        r = self.client.post(
            reverse("statmaps:edit_image", args=[img["id"]]),
            {
                "name": "edited map", "description": "edited", "collection": cid,
                "map_type": "T", "modality": "fMRI-BOLD", "target_template_image": "GenericMNI",
                "analysis_level": "S", "number_of_subjects": "", "cognitive_task_choice": "yes_other",
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
                "cognitive_contrast_cogatlas": "cnt_4e08fefbf0382",
                "ignore_file_warning": False, "is_valid": True, "data_origin": "volume",
                "tags": "Motor, LIPS", "submit_save": "Save and Exit",
            },
        )
        self.assertEqual(r.status_code, 302, form_errors(r))
        got = self.api("/api/images/%s/" % img["id"])
        self.assertEqual(got["name"], "edited map")
        self.assertTrue(got["is_valid"])
        self.assertEqual(got["number_of_subjects"], 1)  # single-subject forces 1
        self.assertEqual(got["analysis_level"], "single-subject")
        self.assertEqual(got["cognitive_paradigm_cogatlas"], "action observation task")
        page = self.client.get(reverse("statmaps:images_by_tag", args=["motor"]))
        self.assertContains(page, "edited map")

    def test_edit_image_rejects_thresholded_map(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        [img] = self.images(cid)
        r = self.client.post(
            reverse("statmaps:edit_image", args=[img["id"]]),
            {
                "name": "thresholded", "collection": cid, "map_type": "T", "modality": "fMRI-BOLD",
                "target_template_image": "GenericMNI", "analysis_level": "G",
                "number_of_subjects": 10, "cognitive_task_choice": "none",
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
                "file": self.thresholded_file(), "submit_save": "Save and Exit",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("seems to be thresholded", r.context["form"].errors["file"][0])
        self.assertEqual(self.api("/api/images/%s/" % img["id"])["name"], "motor lips")

    @unittest.expectedFailure  # master: Image.save() getattr()s reverse relations ('metaanalysis')
    def test_move_image_between_collections(self):
        self.create_collection("First")
        self.create_collection("Second")
        first, second = self.collection_id("First"), self.collection_id("Second")
        self.upload(first, data_file("statmaps/motor_lips.nii.gz"))
        [img] = self.images(first)
        r = self.client.post(
            reverse("statmaps:edit_image", args=[img["id"]]),
            {
                "name": "moved", "collection": second, "map_type": "T", "modality": "fMRI-BOLD",
                "target_template_image": "GenericMNI", "analysis_level": "G",
                "number_of_subjects": 10, "cognitive_task_choice": "none",
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011", "submit_save": "Save and Exit",
            },
        )
        self.assertEqual(r.status_code, 302, form_errors(r))
        self.assertEqual(self.images(first), [])
        [moved] = self.images(second)
        self.assertIn("/images/%s/" % second, moved["file"])
        self.assertEqual(self.client.get(moved["file"].replace("http://testserver", "")).status_code, 200)

    @unittest.expectedFailure  # master: EditAtlasForm sets fields["collection"], absent from its fields
    def test_move_atlas_between_collections(self):
        self.create_collection("First")
        self.create_collection("Second")
        first, second = self.collection_id("First"), self.collection_id("Second")
        atlas = self.upload_atlas_via_api(first)
        r = self.client.post(
            reverse("statmaps:edit_image", args=[atlas["id"]]),
            {"name": "moved atlas", "collection": second, "description": "",
             "submit_save": "Save and Exit"},
        )
        self.assertEqual(r.status_code, 302, form_errors(r))
        self.assertEqual(self.api("/api/collections/%s/atlases/" % first)["results"], [])
        [moved] = self.api("/api/collections/%s/atlases/" % second)["results"]
        for key in ("file", "label_description_file", "thumbnail"):
            self.assertIn("/images/%s/" % second, moved[key])
            self.assertEqual(self.client.get(moved[key].replace("http://testserver", "")).status_code, 200)

    def test_delete_image(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        [img] = self.images(cid)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(reverse("statmaps:delete_image", args=[img["id"]])).status_code, 403)
        self.client.force_login(self.owner)
        r = self.client.get(reverse("statmaps:delete_image", args=[img["id"]]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.images(cid), [])

    def test_pages_render(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        self.create_collection("With others")
        mixed = self.collection_id("With others")
        self.upload(mixed, data_file("statmaps/motor_lips.nii.gz"))
        self.upload_nidm_via_api(mixed)
        atlas = self.upload_atlas_via_api(mixed)
        [statmap] = self.images(cid)
        [nidm_map] = [i for i in self.images(mixed) if i["image_type"] == "NIDM results statistic map"]
        expected = {
            reverse("statmaps:collection_details", args=[cid]): 200,
            reverse("statmaps:collection_details", args=[mixed]): 200,
            reverse("statmaps:image_details", args=[statmap["id"]]): 200,
            reverse("statmaps:image_details", args=[nidm_map["id"]]): 200,
            reverse("statmaps:image_details", args=[atlas["id"]]): 200,
            reverse("statmaps:edit_image", args=[statmap["id"]]): 200,
            reverse("statmaps:my_collections"): 200,
            reverse("statmaps:collections_list"): 200,
            reverse("statmaps:edit_metadata", args=[cid]): 200,
            reverse("statmaps:edit_metadata", args=[mixed]): 403,  # only for statmap-only collections
            reverse("statmaps:atlases_and_parcellations"): 200,
            reverse("statmaps:my_metaanalyses"): 200,
            reverse("statmaps:search"): 200,
        }
        for url, status in expected.items():
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, status)

        tables = {
            "/collections/%s/json" % cid: 1,
            "/collections/%s/ojson" % cid: 1,
            "/my_collections/json": 2,
            "/collections/json": 2,
        }
        for url, rows in tables.items():
            with self.subTest(url):
                r = self.client.get(url, {"draw": 1, "start": 0, "length": 10})
                self.assertEqual(r.status_code, 200)
                self.assertEqual(len(json.loads(r.content)["data"]), rows)

    @unittest.expectedFailure  # master: nidmresults.Graph(zip path) raises with the installed rdflib
    def test_collection_table_with_nidm_bundle(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload_nidm_via_api(cid)
        r = self.client.get("/collections/%s/json" % cid, {"draw": 1, "start": 0, "length": 10})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(json.loads(r.content)["data"]), 2)

    def test_private_collection_access(self):
        self.create_collection("Hidden", private=True)
        cid = self.collection_id("Hidden")
        token = [c for c in self.api("/api/my_collections/")["results"] if c["id"] == cid][0]["url"]
        token = token.rstrip("/").split("/")[-1]
        self.assertRegex(token, r"^[A-Z]{8}$")
        self.upload(token, data_file("statmaps/motor_lips.nii.gz"))
        self.assertEqual(len(self.images(token)), 1)
        self.assertEqual(self.client.get(reverse("statmaps:collection_details", args=[token])).status_code, 200)
        # strangers get 403 by id, 200 by token
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(reverse("statmaps:collection_details", args=[cid])).status_code, 403)
        self.assertEqual(self.client.get(reverse("statmaps:collection_details", args=[token])).status_code, 200)

    @unittest.expectedFailure  # master: HttpRedirectException escapes; its middleware is not installed
    def test_private_collection_owner_redirect(self):
        self.create_collection("Hidden", private=True)
        cid = self.collection_id("Hidden")
        r = self.client.get(reverse("statmaps:collection_details", args=[cid]))
        self.assertEqual(r.status_code, 302)

    def test_add_image_for_neurosynth(self):
        self.assertEqual(self.client.get(reverse("statmaps:add_for_neurosynth")).status_code, 200)
        temp_id = self.collection_id("owner's temporary collection")
        r = self.client.post(
            reverse("statmaps:add_for_neurosynth"),
            {
                "collection": temp_id,
                "name": "for neurosynth", "map_type": "T", "modality": "fMRI-BOLD",
                "target_template_image": "GenericMNI", "cognitive_task_choice": "none",
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
                "file": data_file("statmaps/motor_lips.nii.gz"),
            },
        )
        self.assertEqual(r.status_code, 302, form_errors(r))
        self.assertRegex(r["Location"], r"^http://neurosynth.org/decode/\?neurovault=[A-Z]{8}-\d+$")
        temp = [c for c in self.api("/api/my_collections/")["results"]
                if c["name"] == "owner's temporary collection"]
        self.assertEqual(len(temp), 1)
        self.assertEqual(temp[0]["number_of_images"], 1)

    def test_metaanalysis_selection(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        [img] = self.images(cid)
        self.client.post(
            reverse("statmaps:edit_image", args=[img["id"]]),
            {
                "name": "group map", "collection": cid, "map_type": "T", "modality": "fMRI-BOLD",
                "target_template_image": "GenericMNI", "analysis_level": "G",
                "number_of_subjects": 10, "cognitive_task_choice": "none",
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011", "submit_save": "Save and Exit",
            },
        )
        r = self.client.post(reverse("statmaps:new_metaanalysis"), {"name": "meta one", "description": "m"})
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse("statmaps:new_metaanalysis"), {"name": "meta two", "description": "m"})
        self.assertEqual(r.status_code, 302)
        toggle = reverse("statmaps:toggle_active_metaanalysis", args=[img["id"]])
        self.assertEqual(json.loads(self.client.get(toggle).content), {"new_status": "in"})
        self.assertEqual(json.loads(self.client.get(toggle).content), {"new_status": "out"})
        listing = json.loads(self.client.get("/my_metaanalyses/json?draw=1&start=0&length=10").content)
        strip = lambda html: re.sub(r"<[^>]+>", "", str(html))
        statuses = sorted((strip(row[0]), strip(row[3])) for row in listing["data"])
        self.assertEqual(statuses, [("meta one", "inactive"), ("meta two", "active")])

    def test_metadata_grid_marks_images_valid(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        grid = [
            ["Filename", "name", "map_type", "analysis_level", "number_of_subjects", "modality",
             "cognitive_paradigm_cogatlas", "extra"],
            ["motor_lips.nii.gz", "grid name", "T map", "group", "11", "fMRI-BOLD",
             "action observation task", "x"],
        ]
        r = self.client.post(reverse("statmaps:edit_metadata", args=[cid]), json.dumps(grid),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        [img] = self.images(cid)
        self.assertEqual((img["name"], img["map_type"], img["is_valid"], img["extra"]),
                         ("grid name", "T map", True, "x"))

    def test_download_collection(self):
        self.create_collection()
        cid = self.collection_id("Web Collection")
        self.upload(cid, data_file("statmaps/motor_lips.nii.gz"))
        self.upload_nidm_via_api(cid)
        r = self.client.get(reverse("statmaps:download_collection", args=[cid]))
        self.assertEqual(r.status_code, 200)
        names = sorted(zipfile.ZipFile(io.BytesIO(b"".join(r.streaming_content))).namelist())
        self.assertEqual(names, ["Web Collection/motor_lips.nii.gz", "Web Collection/spm_example.nidm.zip"])
