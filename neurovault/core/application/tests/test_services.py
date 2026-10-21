"""Use-case tests over in-memory adapters: no database, Celery, FreeSurfer or disk layout.

Run without Django: python -m unittest neurovault.core.application.tests.test_services
"""
import itertools
import os
import tempfile
import unittest
from datetime import date, datetime, timezone

import nibabel as nb
import numpy as np

from neurovault.core.application.tests import fakes
from neurovault.core.application.ports import Actor, PaperProperties, SYSTEM
from neurovault.core.application.services.bundles import BundleService, NamedBytes
from neurovault.core.application.services.collections import CollectionService
from neurovault.core.application.services.items import ImageFilesInput, ItemService
from neurovault.core.application.services.metaanalyses import MetaanalysisService
from neurovault.core.application.services.uploads import UploadService
from neurovault.core.domain.errors import DomainValidationError, PermissionDenied
from neurovault.core.domain.items import Atlas, NIDMProvenance

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
OWNER, CONTRIB, STRANGER = Actor(1), Actor(2), Actor(3)


def nifti_bytes(data, name="map.nii.gz"):
    path = os.path.join(tempfile.mkdtemp(), name)
    nb.save(nb.Nifti1Image(np.asarray(data, dtype=np.float32), np.eye(4)), path)
    with open(path, "rb") as f:
        return NamedBytes(name, f.read())


def statistic_volume(name="map.nii.gz"):
    rng = np.random.default_rng(0)
    return nifti_bytes(rng.normal(size=(8, 8, 8)), name)


class Fixture:
    def __init__(self, papers=None, nidm_package=None):
        ids = itertools.count(1)  # items and bundles share one id sequence, as in the database
        self.collections = fakes.InMemoryCollectionRepository()
        self.items = fakes.InMemoryItemRepository(ids)
        self.bundles = fakes.InMemoryBundleRepository(ids)
        self.metaanalyses = fakes.InMemoryMetaanalysisRepository()
        self.access = fakes.FakeAccess(self.collections)
        self.store = fakes.InMemoryMapStore()
        self.queue = fakes.RecordingQueue()
        self.notifier = fakes.RecordingNotifier()
        uow, clock = fakes.FakeUnitOfWork(), fakes.FixedClock(NOW)
        self.item_service = ItemService(
            self.items, self.bundles, self.collections, self.access, self.store, self.queue,
            fakes.NoMasks(), fakes.FakeThumbnails(), fakes.FakeSurfaces(), fakes.FakeProjector(),
            fakes.FakeReducer(), clock, uow,
        )
        self.bundle_service = BundleService(
            self.bundles, self.items, self.collections, self.item_service, self.store,
            fakes.FakeNIDMParser(nidm_package), clock, uow,
            lambda cid, name: "https://neurovault.org/collections/%s/%s/" % (cid, name),
        )
        self.collection_service = CollectionService(
            self.collections, self.items, self.bundles, self.access, self.store,
            fakes.FakeLookup(papers), self.notifier, clock, uow, self.item_service,
            self.bundle_service, lambda user_id: "user%s" % user_id,
        )
        self.uploads = UploadService(self.item_service, self.bundle_service, _Workspace)
        self.meta = MetaanalysisService(
            self.metaanalyses, self.items, self.collection_service, self.item_service,
            self.store, None, uow,
        )

    def collection(self, owner=OWNER, **changes):
        return self.collection_service.save(owner, None, {"name": "c", **changes})

    def statmap(self, collection_id, **changes):
        return self.item_service.add(
            OWNER, collection_id, "statmap",
            {"name": "map", "map_type": "T", "modality": "fMRI-BOLD", **changes},
            ImageFilesInput(file=statistic_volume()),
        )


class _Workspace:
    """Minimal UploadWorkspace: a single uploaded NIfTI file."""

    def __enter__(self):
        self.root = tempfile.mkdtemp()
        return self

    def __exit__(self, *exc):
        pass

    def write(self, upload):
        with open(os.path.join(self.root, upload.name), "wb") as f:
            f.write(upload.read())

    def collect(self, allowed):
        return [(n, os.path.join(self.root, n), None) for n in sorted(os.listdir(self.root))]

    @staticmethod
    def squeezed_volume(path):
        nii = nb.load(path)
        if len(nii.shape) > 3 and nii.shape[3] > 1:
            raise ValueError("4D file detected.")
        base = os.path.basename(path).replace(".nii.gz", "")
        with open(path, "rb") as f:
            return base, f.read()


class ItemUseCases(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.cid = self.f.collection()

    def test_add_stores_file_fills_quality_metrics_and_queues_processing(self):
        item_id = self.f.statmap(self.cid)
        item = self.f.items.get(item_id)
        self.assertEqual(item.files.file, "images/%s/map.nii.gz" % self.cid)
        self.assertFalse(item.stats.is_thresholded)
        self.assertEqual(item.stats.perc_bad_voxels, 0.0)
        self.assertEqual((item.stats.not_mni, item.stats.brain_coverage), (False, 100.0))
        self.assertEqual(item.space.subject_species, "homo sapiens")
        self.assertEqual(self.f.queue.processed, [item_id])
        self.assertIn(self.cid, self.f.collections.touched)

    def test_other_map_type_is_inferred(self):
        mask = np.zeros((8, 8, 8))
        mask[2:5, 2:5, 2:5] = 1
        item_id = self.f.item_service.add(
            OWNER, self.cid, "statmap", {"name": "roi", "map_type": "Other"},
            ImageFilesInput(file=nifti_bytes(mask, "roi.nii.gz")),
        )
        self.assertEqual(self.f.items.get(item_id).stats.map_type, "R")

    def test_strangers_cannot_add(self):
        with self.assertRaises(PermissionDenied):
            self.f.item_service.add(STRANGER, self.cid, "statmap", {"name": "x"}, ImageFilesInput())

    def test_contributors_can_change(self):
        self.f.collection_service.save(OWNER, self.cid, {}, contributor_ids=[CONTRIB.user_id])
        item_id = self.f.statmap(self.cid)
        self.f.item_service.change(CONTRIB, item_id, {"name": "renamed"})
        self.assertEqual(self.f.items.get(item_id).header.name, "renamed")

    def test_change_without_new_file_does_not_reprocess(self):
        item_id = self.f.statmap(self.cid)
        self.f.queue.processed.clear()
        self.f.item_service.change(OWNER, item_id, {"description": "d"})
        self.assertEqual(self.f.queue.processed, [])

    def test_new_file_replaces_old_and_drops_reduced_representation(self):
        item_id = self.f.statmap(self.cid)
        self.f.item_service.ensure_reduced_representation(item_id)
        old = self.f.items.get(item_id)
        self.f.queue.processed.clear()
        self.f.item_service.change(OWNER, item_id, {}, ImageFilesInput(file=statistic_volume()))
        new = self.f.items.get(item_id)
        self.assertEqual(new.files.file, "images/%s/map_1.nii.gz" % self.cid)
        self.assertFalse(self.f.store.exists(old.files.file))
        self.assertFalse(self.f.store.exists(old.files.reduced_representation))
        self.assertIsNone(new.files.reduced_representation)
        self.assertEqual(self.f.items.comparisons_deleted, [item_id])
        self.assertEqual(self.f.queue.processed, [item_id])

    def test_moving_collections_moves_every_file(self):
        other = self.f.collection(name="other")
        item_id = self.f.statmap(self.cid)
        self.f.item_service.process(item_id)
        self.f.item_service.change(OWNER, item_id, {"collection_id": other})
        item = self.f.items.get(item_id)
        refs = item.files.refs()
        self.assertEqual(set(refs), {"file", "thumbnail", "surface_left_file", "surface_right_file"})
        for ref in refs.values():
            self.assertTrue(ref.startswith("images/%s/" % other), ref)
            self.assertTrue(self.f.store.exists(ref))
        self.assertFalse(any(n.startswith("images/%s/" % self.cid) for n in self.f.store.files))

    def test_moving_an_atlas_moves_its_label_file(self):
        other = self.f.collection(name="other")
        item_id = self.f.item_service.add(
            OWNER, self.cid, "atlas", {"name": "atlas"},
            ImageFilesInput(file=statistic_volume("a.nii.gz"),
                            label_description_file=NamedBytes("a.xml", b"<atlas/>")),
        )
        self.f.item_service.change(OWNER, item_id, {"collection_id": other})
        payload = self.f.items.get(item_id).payload
        self.assertIsInstance(payload, Atlas)
        self.assertEqual(payload.label_description_file, "images/%s/a.xml" % other)

    def test_process_renders_thumbnail_and_surfaces(self):
        item_id = self.f.statmap(self.cid)
        self.f.item_service.process(item_id)
        files = self.f.items.get(item_id).files
        self.assertEqual(files.thumbnail, "images/%s/glass_brain_%s.jpg" % (self.cid, item_id))
        self.assertEqual(files.surface_left_file, "images/%s/%s.L.func.gii" % (self.cid, item_id))
        self.f.item_service.process(item_id)  # reprocessing supersedes the old outputs
        again = self.f.items.get(item_id).files
        self.assertFalse(self.f.store.exists(files.thumbnail))
        self.assertTrue(self.f.store.exists(again.thumbnail))

    def test_no_surfaces_outside_mni_or_for_surface_data(self):
        item_id = self.f.statmap(self.cid, target_template_image="Dorr2008")
        self.f.item_service.process(item_id)
        self.assertIsNone(self.f.items.get(item_id).files.surface_left_file)

    def test_delete_removes_files(self):
        item_id = self.f.statmap(self.cid)
        self.f.item_service.process(item_id)
        self.f.item_service.delete(OWNER, item_id)
        self.assertEqual(self.f.store.files, {})
        self.assertNotIn(item_id, self.f.items.rows)

    def test_thresholded_upload_is_reported(self):
        data = np.zeros((8, 8, 8))
        data[0, 0, 0] = 1
        report = self.f.item_service.check_map_file(nifti_bytes(data), "T", "GenericMNI", False)
        self.assertTrue(report.is_thresholded)
        self.assertIn("seems to be thresholded", report.error)
        ignored = self.f.item_service.check_map_file(nifti_bytes(data), "T", "GenericMNI", True)
        self.assertIsNone(ignored.error)


class CollectionUseCases(unittest.TestCase):
    def setUp(self):
        paper = PaperProperties("A paper", "A and B", "http://paper", date(2020, 1, 1), "J")
        self.f = Fixture(papers={"10.1/x": paper})

    def test_create_grants_owner_and_generates_token_when_private(self):
        cid = self.f.collection(private=True)
        c = self.f.collections.get(cid)
        self.assertRegex(c.private_token, r"^[A-Z]{8}$")
        self.assertTrue(self.f.access.can_delete(OWNER, cid))

    def test_doi_fills_publication_and_date(self):
        changes = self.f.collection_service.complete_publication({"DOI": " 10.1/x ", "name": ""})
        self.assertEqual((changes["DOI"], changes["name"], changes["journal_name"]), ("10.1/x", "A paper", "J"))
        cid = self.f.collection_service.save(OWNER, None, changes)
        self.assertEqual(self.f.collections.get(cid).publication.doi_add_date, NOW)

    def test_unresolvable_doi_and_missing_name(self):
        with self.assertRaises(DomainValidationError) as e:
            self.f.collection_service.complete_publication({"DOI": "10.1/missing"})
        self.assertEqual(e.exception.errors, {"DOI": ["Could not resolve DOI"]})
        with self.assertRaises(DomainValidationError) as e:
            self.f.collection_service.complete_publication({"DOI": " ", "name": None})
        self.assertEqual(set(e.exception.errors), {"name", "DOI"})

    def test_new_contributors_get_change_rights_and_one_email(self):
        cid = self.f.collection()
        url = lambda c: "http://x/collections/%s/" % c
        self.f.collection_service.save(OWNER, cid, {}, contributor_ids=[2], absolute_url=url)
        self.f.collection_service.save(OWNER, cid, {}, contributor_ids=[2, 3], absolute_url=url)
        self.assertTrue(self.f.access.can_change(Actor(3), cid))
        self.assertFalse(self.f.access.can_delete(Actor(3), cid))
        self.assertEqual([s[2] for s in self.f.notifier.sent], [[2], [3]])
        self.f.collection_service.save(OWNER, cid, {}, contributor_ids=[])
        self.assertFalse(self.f.access.can_change(Actor(2), cid))

    def test_delete_removes_items_bundles_and_directory(self):
        cid = self.f.collection()
        self.f.statmap(cid)
        with self.assertRaises(PermissionDenied):
            self.f.collection_service.delete(CONTRIB, cid)
        self.f.collection_service.delete(OWNER, cid)
        self.assertEqual((self.f.items.rows, self.f.store.files), ({}, {}))
        self.assertNotIn(cid, self.f.collections.rows)

    def test_temporary_collection_is_reused(self):
        first = self.f.collection_service.temporary_for(1, "neuro", private=True)
        second = self.f.collection_service.temporary_for(1, "neuro", private=False)
        self.assertEqual(first, second)
        self.assertEqual(self.f.collections.get(first).name, "neuro's temporary collection")


class BundleUseCases(unittest.TestCase):
    TTL = 'prov:atLocation "file:///tmp/x/TStatistic.nii.gz"^^xsd:anyURI ;'

    def setUp(self):
        map_path = os.path.join(tempfile.mkdtemp(), "TStatistic.nii.gz")
        with open(map_path, "wb") as f:
            f.write(statistic_volume().read())
        self.package = fakes.FakeNIDMPackage(
            [{"name": "contrast", "type": "T", "file": map_path}], self.TTL
        )
        self.f = Fixture(nidm_package=self.package)
        self.cid = self.f.collection()

    def ingest(self):
        prepared = self.f.bundle_service.prepare(self.cid, NamedBytes("spm.nidm.zip", b"zip"))
        return self.f.bundle_service.ingest(OWNER, self.cid, prepared, description="d")

    def test_ingest_stores_bundle_maps_and_rewrites_ttl(self):
        bundle_id = self.ingest()
        bundle = self.f.bundles.get(bundle_id)
        self.assertEqual(bundle.header.name, "spm.nidm")
        self.assertEqual(bundle.zip_file, "images/%s/spm.nidm/spm.nidm.zip" % self.cid)
        [map_id] = self.f.items.ids_from_bundle(bundle_id)
        statmap = self.f.items.get(map_id)
        self.assertEqual(statmap.payload.source, NIDMProvenance(bundle_id))
        self.assertIsNone(statmap.payload.annotation)
        self.assertEqual(statmap.files.file, "images/%s/spm.nidm/TStatistic.nii.gz" % self.cid)
        ttl = self.f.store.files[bundle.ttl_file].decode()
        self.assertIn('"https://neurovault.org/collections/%s/spm.nidm/TStatistic.nii.gz"' % self.cid, ttl)
        self.assertTrue(self.package.cleaned)

    def test_second_upload_of_same_name_is_numbered(self):
        self.ingest()
        second = self.f.bundles.get(self.ingest())
        self.assertEqual(second.header.name, "spm_1.nidm")

    def test_delete_removes_maps_and_directory(self):
        bundle_id = self.ingest()
        self.f.bundle_service.delete(OWNER, bundle_id)
        self.assertEqual((self.f.items.rows, self.f.bundles.rows, self.f.store.files), ({}, {}, {}))


class UploadUseCases(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.cid = self.f.collection()

    def test_spm_names_set_the_map_type_and_maps_need_metadata(self):
        result = self.f.uploads.ingest(OWNER, self.cid, upload=statistic_volume("spmT_0001.nii.gz"))
        item = self.f.items.get(result.item_ids[0])
        self.assertEqual((item.header.name, item.stats.map_type, item.header.is_valid),
                         ("spmT 0001", "T", False))

    def test_4d_volumes_are_skipped_with_a_warning(self):
        upload = nifti_bytes(np.ones((4, 4, 4, 2)), "series.nii.gz")
        result = self.f.uploads.ingest(OWNER, self.cid, upload=upload)
        self.assertEqual(result.item_ids, [])
        self.assertEqual(result.warnings, ["Skipping series.nii.gz: Skipping series.nii.gz: 4D file detected."])


class MetaanalysisUseCases(unittest.TestCase):
    def test_one_active_meta_analysis_per_owner(self):
        f = Fixture()
        first = f.meta.save(OWNER, None, "one", "")
        second = f.meta.save(OWNER, None, "two", "")
        self.assertEqual(f.metaanalyses.get(first).status, "inactive")
        f.meta.activate(OWNER, first)
        self.assertEqual(f.metaanalyses.get(second).status, "inactive")
        with self.assertRaises(PermissionDenied):
            f.meta.activate(STRANGER, first)

    def test_toggle_map(self):
        f = Fixture()
        f.meta.save(OWNER, None, "one", "")
        self.assertEqual(f.meta.toggle_map(OWNER, 7), "in")
        self.assertEqual(f.meta.toggle_map(OWNER, 7), "out")


if __name__ == "__main__":
    unittest.main()
