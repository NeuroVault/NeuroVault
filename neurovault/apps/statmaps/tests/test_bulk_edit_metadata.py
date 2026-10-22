"""
Reproduce https://neurostars.org/t/neurovault-cannot-edit-and-save-metadata/35430

Users bulk upload a folder of maps, then fill in metadata (often with the
"Copy image meta-data" button). For some batches the save silently fails:
the edit page re-renders and no visible field explains why.
"""
import json
import os
import re
import shutil
import tempfile
import unittest
from html.parser import HTMLParser
from zipfile import ZipFile

import nibabel as nb
import numpy as np
from django.test import TestCase, Client
from django.urls import reverse

from neurovault.api.tests.utils import _setup_test_cognitive_atlas
from neurovault.apps.statmaps.models import Collection, StatisticMap, User
from neurovault.apps.statmaps.views import _serialize_collection
from .utils import clearDB

TEST_PATH = os.path.abspath(os.path.dirname(__file__))
MOTOR_LIPS = os.path.join(TEST_PATH, "test_data/statmaps/motor_lips.nii.gz")
COPY_MD_TEMPLATE = os.path.join(
    TEST_PATH, "..", "templates", "statmaps", "_copy_md.html"
)


def _copy_md_js_transform(data_values):
    """Python port of the JSON munging done in _copy_md.html before JSON.parse."""
    json_string = data_values.replace("'", '"')
    json_string = json_string.replace("True", "true").replace("False", "false")
    return json.loads(json_string)


class _FormValuesParser(HTMLParser):
    """Collect what a browser would submit from the first <form> on a page."""

    def __init__(self):
        super().__init__()
        self.values = {}
        self.selected_labels = {}
        self._in_form = False
        self._select = None
        self._option = None
        self._first_option = None
        self._textarea = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and a.get("method", "").lower() == "post":
            self._in_form = True
        if not self._in_form:
            return
        name = a.get("name")
        if tag == "input" and name:
            kind = a.get("type", "text").lower()
            if kind in ("submit", "button", "file"):
                return
            if kind in ("radio", "checkbox") and "checked" not in a:
                return
            self.values[name] = a.get("value", "on" if kind == "checkbox" else "")
        elif tag == "select" and name:
            self._select = name
            self._first_option = None
            self.values.setdefault(name, None)
        elif tag == "option" and self._select:
            self._option = (a.get("value", ""), "selected" in a)
            self._option_text = ""
        elif tag == "textarea" and name:
            self._textarea = name
            self.values[name] = ""

    def handle_data(self, data):
        if self._option is not None:
            self._option_text += data
        if self._textarea:
            self.values[self._textarea] += data

    def handle_endtag(self, tag):
        if tag == "form":
            self._in_form = False
        elif tag == "option" and self._option is not None:
            value, selected = self._option
            if self._first_option is None:
                self._first_option = (value, self._option_text.strip())
            if selected:
                self.values[self._select] = value
                self.selected_labels[self._select] = self._option_text.strip()
            self._option = None
        elif tag == "select" and self._select:
            if self.values[self._select] is None:
                value, text = self._first_option or ("", "")
                self.values[self._select] = value
                self.selected_labels[self._select] = text
            self._select = None
        elif tag == "textarea":
            if self._textarea:
                self.values[self._textarea] = self.values[self._textarea].lstrip("\n")
            self._textarea = None


class BulkEditMetadataTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.user = User.objects.create_user("NeuroGuy", password="1234")
        self.client = Client()
        self.assertTrue(self.client.login(username="NeuroGuy", password="1234"))
        self.coll = Collection(owner=self.user, name="Bulk Collection")
        self.coll.save()
        self.task, self.contrast = _setup_test_cognitive_atlas()

    def tearDown(self):
        clearDB()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # helpers

    def _make_thresholded_nifti(self, name):
        """A map where >85% of voxels are zero, like a corrected/thresholded output."""
        nii = nb.load(MOTOR_LIPS)
        data = np.asanyarray(nii.dataobj).astype(np.float32)
        data[np.abs(data) < np.percentile(np.abs(data), 95)] = 0
        path = os.path.join(self.tmpdir, name)
        nb.Nifti1Image(data, nii.affine).to_filename(path)
        return path

    def _bulk_upload(self, *paths):
        zip_path = os.path.join(self.tmpdir, "batch_%d.zip" % len(os.listdir(self.tmpdir)))
        with ZipFile(zip_path, "w") as zf:
            for p in paths:
                zf.write(p, os.path.basename(p))
        with open(zip_path, "rb") as fp:
            response = self.client.post(
                reverse("statmaps:upload_folder", kwargs={"collection_cid": self.coll.id}),
                {"collection_cid": self.coll.id, "file": fp},
            )
        self.assertEqual(response.status_code, 302)
        return response["Location"]

    def _batch_images(self, redirect_url):
        """Images created by an upload, recovered from the bulk-edit redirect."""
        min_id = int(re.search(r"min_image=(\d+)", redirect_url).group(1))
        max_id = int(re.search(r"max_image=(\d+)", redirect_url).group(1))
        return list(
            StatisticMap.objects.filter(pk__gte=min_id, pk__lte=max_id).order_by("pk")
        )

    def _edit_url(self, image, redirect_url):
        query = redirect_url.split("?", 1)[1].replace("show_instructions=True&", "")
        return reverse("statmaps:edit_image", kwargs={"pk": image.pk}) + "?" + query

    def _rendered_form_post(self, edit_url):
        """GET the edit page and return the POST body the browser would send unchanged,
        built from the rendered HTML rather than the form's Python values."""
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        parser = _FormValuesParser()
        parser.feed(response.content.decode())
        post = parser.values
        # set_cog_toggle_state() runs on page load and picks the task radio from the
        # selected paradigm's label.
        label = parser.selected_labels.get("cognitive_paradigm_cogatlas", "")
        post["cognitive_task_choice"] = {
            "rest eyes open": "rest_open",
            "rest eyes closed": "rest_closed",
            "None / Other": "none",
        }.get(label, "yes_other")
        return response, post

    def _manual_metadata(self):
        return {
            "name": "manually entered",
            "map_type": "T",
            "modality": "fMRI-BOLD",
            "analysis_level": "G",
            "number_of_subjects": 20,
            "target_template_image": "GenericMNI",
            "cognitive_task_choice": "yes_other",
            "cognitive_paradigm_cogatlas": self.task.cog_atlas_id,
            "cognitive_contrast_cogatlas": self.contrast.cog_atlas_id,
            "description": "first-stage results",
        }

    def _save_first_batch(self, **overrides):
        """Batch 1: an unthresholded map whose metadata is filled in by hand."""
        redirect_url = self._bulk_upload(MOTOR_LIPS)
        [image] = self._batch_images(redirect_url)
        edit_url = self._edit_url(image, redirect_url)
        _, post = self._rendered_form_post(edit_url)
        post.update(self._manual_metadata())
        post.update(overrides)
        post["submit_save"] = "Save and Exit"
        response = self.client.post(edit_url, post)
        self.assertEqual(response.status_code, 302, "first batch should save")
        image.refresh_from_db()
        self.assertTrue(image.is_valid)
        return image

    def _apply_copy_md(self, post, source_image):
        """Apply the field assignments _copy_md.html makes from the selected image."""
        [source] = [
            d for d in _serialize_collection(StatisticMap.objects.filter(pk=source_image.pk))
        ]
        image_data = _copy_md_js_transform(source["json_data"])
        with open(COPY_MD_TEMPLATE) as f:
            js = f.read()
        # document.querySelector("#id_<field>").value = imageData.<key>;
        for field, key in re.findall(
            r'querySelector\("#id_(\w+)"\)\.value = imageData\.(\w+);', js
        ):
            value = image_data.get(key)  # undefined in JS -> select cleared
            post[field] = "" if value is None else value
        # updateRadioButton("<name>", imageData.<key>);
        for field, key in re.findall(r'updateRadioButton\("(\w+)", imageData\.(\w+)\)', js):
            if image_data.get(key) not in (None, ""):
                post[field] = image_data[key]
        # set_cog_toggle_state() runs on the paradigm "change" event
        post["cognitive_task_choice"] = "yes_other"
        return post

    # tests

    def test_bulk_edit_unthresholded_map_saves(self):
        """Baseline: the first batch saves fine (matches the user report)."""
        self._save_first_batch()

    def test_bulk_edit_copy_metadata_saves_second_batch(self):
        """Second batch: copy metadata from batch 1, then Save and Exit."""
        source = self._save_first_batch()
        redirect_url = self._bulk_upload(self._make_thresholded_nifti("stage2_map.nii.gz"))
        [image] = self._batch_images(redirect_url)
        edit_url = self._edit_url(image, redirect_url)

        _, post = self._rendered_form_post(edit_url)
        post = self._apply_copy_md(post, source)
        post["name"] = "stage 2 map"
        post["submit_save"] = "Save and Exit"
        response = self.client.post(edit_url, post)

        image.refresh_from_db()
        if response.status_code != 302:
            self.fail("Save failed: %s" % response.context["form"].errors.as_data())
        self.assertTrue(image.is_valid)

    def test_edit_page_warns_about_thresholded_map(self):
        """File QA results from upload are shown as a warning, not a blocking error."""
        redirect_url = self._bulk_upload(self._make_thresholded_nifti("stage2_map.nii.gz"))
        [image] = self._batch_images(redirect_url)
        self.assertTrue(image.is_thresholded)
        response = self.client.get(self._edit_url(image, redirect_url))
        self.assertContains(response, "This map seems to be thresholded")

    def test_edit_page_warns_about_map_outside_mni(self):
        path = os.path.join(TEST_PATH, "test_data/statmaps/motor_lips_nan.nii.gz")
        redirect_url = self._bulk_upload(path)
        [image] = self._batch_images(redirect_url)
        self.assertTrue(image.not_mni)
        response = self.client.get(self._edit_url(image, redirect_url))
        self.assertContains(response, "This map seems not to be in the MNI space")

    def test_errors_on_unrendered_fields_are_visible(self):
        """An error on a field the layout doesn't show must still reach the user."""
        redirect_url = self._bulk_upload(MOTOR_LIPS)
        [image] = self._batch_images(redirect_url)
        edit_url = self._edit_url(image, redirect_url)
        _, post = self._rendered_form_post(edit_url)
        post.update(self._manual_metadata())
        post["perc_bad_voxels"] = "not a number"  # hidden input
        post["submit_save"] = "Save and Exit"
        response = self.client.post(edit_url, post)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("perc_bad_voxels", form.errors)
        for message in form.errors["perc_bad_voxels"]:
            self.assertContains(response, message)

    @unittest.expectedFailure  # known bug: copy-metadata JS reads keys the view never serializes
    def test_copy_metadata_copies_cognitive_contrast(self):
        """Every imageData.<key> read by _copy_md.html must exist in the serialized data."""
        source = self._save_first_batch()
        [data] = _serialize_collection(StatisticMap.objects.filter(pk=source.pk))
        image_data = _copy_md_js_transform(data["json_data"])
        with open(COPY_MD_TEMPLATE) as f:
            keys = set(re.findall(r"imageData\.(\w+)", f.read()))
        missing = sorted(k for k in keys if k not in image_data)
        self.assertEqual(missing, [], "copy button reads keys that are never serialized")

    @unittest.expectedFailure  # known bug: copy-metadata JS mangles quotes before JSON.parse
    def test_copy_metadata_json_survives_apostrophes(self):
        """A description like "Participants' ..." must not break the copy button."""
        source = self._save_first_batch(description="Participants' first-stage results")
        [data] = _serialize_collection(StatisticMap.objects.filter(pk=source.pk))
        try:
            _copy_md_js_transform(data["json_data"])
        except json.JSONDecodeError as e:
            self.fail("copy button's JSON.parse would throw: %s" % e)

    def test_single_edit_save_does_not_warn_about_unprocessed_upload(self):
        """Outside bulk mode there is no upload in progress, so Save must not be
        guarded by the 'images in upload are not yet processed' confirm."""
        image = self._save_first_batch()
        response = self.client.get(reverse("statmaps:edit_image", kwargs={"pk": image.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "not yet processed")

    def test_copy_metadata_second_batch_real_maps(self):
        """Batch 2 with a range of real maps: copy from batch 1 and save."""
        source = self._save_first_batch()
        for fname in ["motor_lips.nii.gz", "beta_0001.nii.gz", "WA3.nii.gz",
                      "saccade.I_C.MNI.nii.gz", "motor_lips_nan.nii.gz", "all.nii.gz"]:
            with self.subTest(fname=fname):
                path = os.path.join(TEST_PATH, "test_data/statmaps", fname)
                redirect_url = self._bulk_upload(path)
                images = self._batch_images(redirect_url)
                if not images:
                    self.skipTest("%s was not imported by bulk upload" % fname)
                image = images[0]
                edit_url = self._edit_url(image, redirect_url)
                _, post = self._rendered_form_post(edit_url)
                post = self._apply_copy_md(post, source)
                post["submit_save"] = "Save and Exit"
                response = self.client.post(edit_url, post)
                if response.status_code != 302:
                    self.fail("%s: %s\nPOST: %s" % (
                        fname, response.context["form"].errors.as_data(), post))
                image.refresh_from_db()
                self.assertTrue(image.is_valid)

    def test_next_image_after_successful_save(self):
        """Saving image 1 of 2 and clicking Next goes to image 2."""
        redirect_url = self._bulk_upload(MOTOR_LIPS, os.path.join(TEST_PATH, "test_data/statmaps/beta_0001.nii.gz"))
        first, second = self._batch_images(redirect_url)
        edit_url = self._edit_url(first, redirect_url)
        response, post = self._rendered_form_post(edit_url)
        post.update(self._manual_metadata())
        post["submit_next"] = "Next Image"
        response = self.client.post(edit_url, post, follow=True)
        self.assertEqual(response.redirect_chain[-1][0].split("?")[0],
                         reverse("statmaps:edit_image", kwargs={"pk": second.pk}))

    @unittest.expectedFailure  # known bug: show_instructions is honoured on POST
    def test_rejected_save_does_not_reshow_upload_successful_popup(self):
        """The form posts back to the upload redirect URL, which still carries
        show_instructions=True, so a rejected save re-renders the page with the
        'Upload successful' modal."""
        redirect_url = self._bulk_upload(MOTOR_LIPS)
        [image] = self._batch_images(redirect_url)
        self.assertIn("show_instructions=True", redirect_url)
        response, post = self._rendered_form_post(redirect_url)
        self.assertContains(response, "Upload successful")
        post.update(self._manual_metadata())
        post["name"] = ""
        post["submit_save"] = "Save and Exit"
        response = self.client.post(redirect_url, post)
        self.assertEqual(response.status_code, 200)  # rejected
        self.assertNotContains(response, "Upload successful")
