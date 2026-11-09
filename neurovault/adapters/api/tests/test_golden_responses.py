"""Golden responses for the public API.

The refactor must not change the shape or values the API returns. Each case
records the full JSON body (with ids, timestamps, tokens and the test server
host normalized) next to this file under golden/. To re-record after an
intentional API change:

    GOLDEN_UPDATE=1 python manage.py test neurovault.adapters.api.tests.test_golden_responses
"""
import json
import os
import re

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from neurovault.adapters.persistence.models import Collection
from neurovault.adapters.web.statmaps.tests.utils import clearDB, persist
from neurovault.adapters.api.tests.base import APITestCase
from neurovault.adapters.api.tests.utils import _setup_test_cognitive_atlas

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
UPDATE = os.environ.get("GOLDEN_UPDATE") == "1"
# Outputs of the asynchronous processing task. A request that stores a new
# file (POST, or PUT with a file) queues the task, and whether the response
# already shows its outputs depends on when it finishes. Other writes queue
# nothing, so their values are compared.
ASYNC_OUTPUTS = ("thumbnail", "surface_left_file", "surface_right_file", "reduced_representation")
DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?")


class GoldenResponses(APITestCase):
    maxDiff = None

    def setUp(self):
        self.user = User.objects.create_user("NeuroGuy", email="neuro@example.org")
        self.other = User.objects.create_user("OtherGuy")
        self.coll = Collection(owner=self.user, name="Golden Collection", description="d\nline")
        persist(self.coll)
        self.private = Collection(
            owner=self.user, name="Private Golden", private=True, private_token="ABCDEFGH"
        )
        persist(self.private)
        _setup_test_cognitive_atlas()
        self.client.force_authenticate(user=self.user)
        self._pending_posts = []

        self.statmap = self._post(
            "/api/collections/%s/images/" % self.coll.pk,
            {
                "name": "golden map",
                "modality": "fMRI-BOLD",
                "map_type": "T",
                "analysis_level": "G",
                "number_of_subjects": 12,
                "cognitive_paradigm_cogatlas": "trm_4f24126c22011",
                "cognitive_contrast_cogatlas": "cnt_4e08fefbf0382",
                "custom_field": "custom value",
                "file": self._file("statmaps/motor_lips.nii.gz"),
            },
            "post_statmap",
        )
        self.atlas = self._post(
            "/api/collections/%s/atlases/" % self.coll.pk,
            {
                "name": "golden atlas",
                "file": self._file("api/VentralFrontal_thr75_summaryimage_2mm.nii.gz"),
                "label_description_file": self._file(
                    "api/VentralFrontal_thr75_summaryimage_2mm.xml"
                ),
            },
            "post_atlas",
        )
        self.bundle = self._post(
            "/api/collections/%s/nidm_results/" % self.coll.pk,
            {
                "name": "golden nidm",
                "description": "golden nidm upload",
                "zip_file": self._file("nidm/spm_example.nidm.zip"),
            },
            "post_nidm",
        )
        self.bundle_statmaps = json.loads(
            self.client.get("/api/nidm_results/%s/" % self.bundle["id"]).content
        )["statmaps"]
        self.nidm_statmap_id = self.bundle_statmaps[0]["id"]
        self.private_statmap = self._post(
            "/api/collections/ABCDEFGH/images/",
            {
                "name": "private map",
                "modality": "fMRI-BOLD",
                "map_type": "Z",
                "file": self._file("statmaps/beta_0001.nii.gz"),
            },
            "post_private_statmap",
        )
        for name, response in self._pending_posts:
            self.assertGolden(name, response)

    def tearDown(self):
        clearDB()

    # ------------------------------------------------------------- helpers

    def _file(self, rel):
        path = self.abs_data_path(rel)
        with open(path, "rb") as f:
            return SimpleUploadedFile(os.path.basename(path), f.read())

    def _post(self, url, data, golden_name):
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, 201, response.content)
        body = json.loads(response.content)
        if golden_name:
            self._pending_posts.append((golden_name, response))
        return body

    def _id_maps(self):
        collections = {self.coll.pk: "COLLECTION", self.private.pk: "PRIVATE_COLLECTION"}
        users = {self.user.pk: "USER", self.other.pk: "OTHER_USER"}
        items, bundles = {}, {}
        for attr, label in (
            ("statmap", "STATMAP"),
            ("atlas", "ATLAS"),
            ("private_statmap", "PRIVATE_STATMAP"),
        ):
            if hasattr(self, attr):
                items[getattr(self, attr)["id"]] = label
        if hasattr(self, "bundle"):
            bundles[self.bundle["id"]] = "BUNDLE"
        for i, s in enumerate(getattr(self, "bundle_statmaps", [])):
            items[s["id"]] = "NIDM_STATMAP_%d" % i
        for extra in getattr(self, "extra_collections", []):
            collections[extra] = "EXTRA_COLLECTION"
        return {"collection": collections, "user": users, "item": items, "bundle": bundles}

    @staticmethod
    def _label(table, n):
        return "<%s>" % table.get(n, "UNKNOWN_ID")

    def _context(self, d):
        if "username" in d:
            return "user"
        if "owner_name" in d or "number_of_images" in d:
            return "collection"
        if "zip_file" in d:
            return "bundle"
        return "item"

    def _normalize(self, value, maps, key=None, context="item"):
        if isinstance(value, dict):
            if "aaData" in value:
                ctx = self._context({pair[0]: None for pair in value["aaData"]})
            else:
                ctx = self._context(value)
            return {k: self._normalize(v, maps, k, ctx) for k, v in value.items()}
        if isinstance(value, list):
            if len(value) == 2 and isinstance(value[0], str) and key == "pair":
                return [value[0], self._normalize(value[1], maps, value[0], context)]
            inner = "pair" if key == "aaData" else key
            return [self._normalize(v, maps, inner, context) for v in value]
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, int):
            if key == "polymorphic_ctype":
                # ids differ between databases; compare which content type it names
                from django.contrib.contenttypes.models import ContentType

                ct = ContentType.objects.get(pk=value)
                return "<CTYPE %s.%s>" % (ct.app_label, ct.model)
            if key == "id":
                return self._label(maps[context], value)
            if key in ("collection_id", "collection"):
                return self._label(maps["collection"], value)
            if key == "owner":
                return self._label(maps["user"], value)
            if key == "nidm_results":
                return self._label(maps["bundle"], value)
            return value
        if isinstance(value, str):
            value = DATETIME.sub("<DATETIME>", value)
            value = re.sub(r"(/collections/)(\d+)(/|$)", lambda m: m.group(1) + self._label(
                maps["collection"], int(m.group(2))) + m.group(3), value)
            value = re.sub(r"(/media/images/)(\d+)(/)", lambda m: m.group(1) + self._label(
                maps["collection"], int(m.group(2))) + m.group(3), value)
            value = re.sub(r"(/images/)(\d+)(/|$)", lambda m: m.group(1) + self._label(
                maps["item"], int(m.group(2))) + m.group(3), value)
            value = re.sub(r"(glass_brain_|transform_4mm_)(\d+)(\.)", lambda m: m.group(1) + self._label(
                maps["item"], int(m.group(2))) + m.group(3), value)
            value = re.sub(r"(/)(\d+)(\.[LR]\.func\.gii)", lambda m: m.group(1) + self._label(
                maps["item"], int(m.group(2))) + m.group(3), value)
            return value
        return value

    def assertGolden(self, name, response, status=None):
        if status is not None:
            self.assertEqual(response.status_code, status, response.content)
        body = json.loads(response.content) if response.content else None
        got = {"status": response.status_code, "body": self._normalize(body, self._id_maps())}
        if name.startswith(("post_", "put_")) and isinstance(got["body"], dict):
            for key in ASYNC_OUTPUTS:
                if key in got["body"]:
                    got["body"][key] = "<ASYNC_OUTPUT>"
        path = os.path.join(GOLDEN_DIR, name + ".json")
        dump_dir = os.environ.get("GOLDEN_DUMP")
        if dump_dir:
            os.makedirs(dump_dir, exist_ok=True)
            with open(os.path.join(dump_dir, name + ".json"), "w") as f:
                json.dump(got, f, indent=2, sort_keys=True)
                f.write("\n")
        if UPDATE:
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            with open(path, "w") as f:
                json.dump(got, f, indent=2, sort_keys=True)
                f.write("\n")
            return
        with open(path) as f:
            expected = json.load(f)
        self.assertEqual(json.loads(json.dumps(got)), expected)

    # --------------------------------------------------------------- reads

    def test_reads(self):
        cases = {
            "get_image_statmap": "/api/images/%s/" % self.statmap["id"],
            "get_image_atlas": "/api/images/%s/" % self.atlas["id"],
            "get_image_nidm_statmap": "/api/images/%s/" % self.nidm_statmap_id,
            "get_image_private_token": "/api/images/ABCDEFGH-%s/" % self.private_statmap["id"],
            "get_atlas": "/api/atlases/%s/" % self.atlas["id"],
            "get_nidm_results": "/api/nidm_results/%s/" % self.bundle["id"],
            "list_images": "/api/images/",
            "list_atlases": "/api/atlases/",
            "list_nidm_results": "/api/nidm_results/",
            "get_collection": "/api/collections/%s/" % self.coll.pk,
            "get_private_collection_token": "/api/collections/ABCDEFGH/",
            "list_collections": "/api/collections/",
            "list_my_collections": "/api/my_collections/",
            "collection_images": "/api/collections/%s/images/" % self.coll.pk,
            "collection_atlases": "/api/collections/%s/atlases/" % self.coll.pk,
            "collection_nidm_results": "/api/collections/%s/nidm_results/" % self.coll.pk,
            "image_datatable": "/api/images/%s/datatable/" % self.statmap["id"],
            "atlas_datatable": "/api/atlases/%s/datatable/" % self.atlas["id"],
            "atlas_regions_table": "/api/atlases/%s/regions_table/" % self.atlas["id"],
            "collection_datatable": "/api/collections/%s/datatable/" % self.coll.pk,
            "auth_user": "/api/user",
        }
        for name, url in cases.items():
            with self.subTest(name):
                self.assertGolden(name, self.client.get(url))

    def test_reads_anonymous(self):
        self.client.force_authenticate(user=None)
        cases = {
            "anon_get_image_statmap": "/api/images/%s/" % self.statmap["id"],
            "anon_get_private_image_by_id": "/api/images/%s/" % self.private_statmap["id"],
            "anon_get_private_collection_by_id": "/api/collections/%s/" % self.private.pk,
            "anon_list_images": "/api/images/",
        }
        for name, url in cases.items():
            with self.subTest(name):
                self.assertGolden(name, self.client.get(url))

    # -------------------------------------------------------------- writes

    def test_patch_statmap(self):
        response = self.client.patch(
            "/api/images/%s/" % self.statmap["id"],
            {"description": "patched", "custom_field": "patched custom", "new_field": 7},
        )
        self.assertGolden("patch_statmap", response, 200)

    def test_put_statmap(self):
        response = self.client.put(
            "/api/images/%s/" % self.statmap["id"],
            {
                "name": "golden map renamed",
                "modality": "fMRI-BOLD",
                "map_type": "Z",
                "file": self._file("statmaps/motor_lips.nii.gz"),
            },
        )
        self.assertGolden("put_statmap", response, 200)

    def test_patch_atlas(self):
        response = self.client.patch(
            "/api/atlases/%s/" % self.atlas["id"], {"description": "patched atlas"}
        )
        self.assertGolden("patch_atlas", response, 200)

    def test_patch_nidm_results(self):
        response = self.client.patch(
            "/api/nidm_results/%s/" % self.bundle["id"], {"description": "patched nidm"}
        )
        self.assertGolden("patch_nidm_results", response, 200)

    def test_create_and_patch_collection(self):
        response = self.client.post(
            "/api/collections/", {"name": "API Collection", "description": "made by api"}
        )
        created = json.loads(response.content)
        self.extra_collections = [created["id"]]
        self.assertGolden("post_collection", response, 201)
        response = self.client.patch(
            "/api/collections/%s/" % created["id"], {"description": "patched collection"}
        )
        self.assertGolden("patch_collection", response, 200)

    def test_deletes(self):
        self.assertGolden(
            "delete_image", self.client.delete("/api/images/%s/" % self.statmap["id"]), 204
        )
        self.assertGolden(
            "delete_nidm_results",
            self.client.delete("/api/nidm_results/%s/" % self.bundle["id"]),
            204,
        )
        self.assertGolden(
            "delete_collection",
            self.client.delete("/api/collections/%s/" % self.coll.pk),
            204,
        )

    # -------------------------------------------------------------- errors

    # ------------------------------------------- auth, sharing, paging

    def test_token_auth_write(self):
        from rest_framework.authtoken.models import Token

        self.client.force_authenticate(user=None)
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = self.client.patch(
            "/api/images/%s/" % self.statmap["id"], {"description": "by token"}
        )
        self.assertGolden("token_patch_statmap", response, 200)

    def test_contributor_writes(self):
        # share through the web form, as an owner does
        self.client.force_login(self.user)
        r = self.client.post(
            "/collections/%s/edit" % self.coll.pk,
            {"name": "Golden Collection", "publication_status": "in_preparation",
             "private": False, "description": "d\nline", "contributors": "OtherGuy"},
            HTTP_HOST="testserver",
        )
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        self.client.force_authenticate(user=self.other)
        self.assertGolden(
            "contributor_patch_statmap",
            self.client.patch("/api/images/%s/" % self.statmap["id"], {"description": "by contributor"}),
        )
        self.assertGolden(
            "contributor_post_statmap",
            self.client.post(
                "/api/collections/%s/images/" % self.coll.pk,
                {"name": "contributed", "modality": "fMRI-BOLD", "map_type": "T",
                 "file": self._file("statmaps/motor_lips.nii.gz")},
                format="multipart",
            ),
        )
        self.assertGolden(
            "contributor_delete_collection",
            self.client.delete("/api/collections/%s/" % self.coll.pk),
        )

    def test_paging_and_filters(self):
        cases = {
            "list_images_limit_offset": "/api/images/?limit=1&offset=1",
            "list_collections_limit": "/api/collections/?limit=1",
            "list_collections_name_filter": "/api/collections/?name=Golden%20Collection",
            "collection_images_limit": "/api/collections/%s/images/?limit=1" % self.coll.pk,
        }
        for name, url in cases.items():
            with self.subTest(name):
                self.assertGolden(name, self.client.get(url))

    def test_put_nidm_results_with_new_zip(self):
        response = self.client.put(
            "/api/nidm_results/%s/" % self.bundle["id"],
            {"name": "golden nidm", "description": "replaced",
             "zip_file": self._file("nidm/fsl_course_av.nidm.zip")},
            format="multipart",
        )
        self.assertGolden("put_nidm_results", response, 200)

    def test_errors(self):
        self.assertGolden(
            "error_missing_fields",
            self.client.post(
                "/api/collections/%s/images/" % self.coll.pk, {"name": "x"}, format="multipart"
            ),
        )
        self.assertGolden(
            "error_collection_name_and_doi_missing",
            self.client.post("/api/collections/", {"description": "no name"}),
        )
        self.client.force_authenticate(user=self.other)
        self.assertGolden(
            "error_patch_other_users_image",
            self.client.patch("/api/images/%s/" % self.statmap["id"], {"description": "x"}),
        )
        self.assertGolden(
            "error_delete_other_users_image",
            self.client.delete("/api/images/%s/" % self.statmap["id"]),
        )
        self.assertGolden(
            "error_add_to_other_users_collection",
            self.client.post(
                "/api/collections/%s/images/" % self.coll.pk,
                {"name": "x", "modality": "fMRI-BOLD", "map_type": "T",
                 "file": self._file("statmaps/motor_lips.nii.gz")},
                format="multipart",
            ),
        )
        self.client.force_authenticate(user=None)
        self.assertGolden(
            "error_anonymous_post",
            self.client.post(
                "/api/collections/%s/images/" % self.coll.pk, {"name": "x"}, format="multipart"
            ),
        )
