"""Use cases for images: add, change, move, delete, and background processing."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from neurovault.core.domain import map_quality, vocabulary as v
from neurovault.core.domain.errors import DomainValidationError, PermissionDenied
from neurovault.core.domain.items import CollectionItem, apply_changes, new_item

from ..layout import bundle_dir, collection_dir
from ..ports import SurfaceInputError

THRESHOLDED_MSG = (
    "This map seems to be thresholded (%.4g%% of voxels are zeros). "
    "Please use an unthresholded version of the map if possible."
)
NOT_MNI_MSG = (
    "This map seems not to be in the MNI space (%.4g%% of meaningful "
    "voxels are outside of the brain). Please transform your data to MNI space."
)


@dataclass
class ImageFilesInput:
    """Uploaded files for an image; None leaves the stored file unchanged."""

    file: Optional[object] = None
    surface_left_file: Optional[object] = None
    surface_right_file: Optional[object] = None
    label_description_file: Optional[object] = None

    def uploads(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__ if getattr(self, k) is not None}


@dataclass
class QualityReport:
    is_thresholded: Optional[bool] = None
    perc_bad_voxels: Optional[float] = None
    not_mni: Optional[bool] = None
    brain_coverage: Optional[float] = None
    perc_voxels_outside: Optional[float] = None
    error: Optional[str] = None
    values: dict = field(default_factory=dict)


class ItemService:
    def __init__(self, items, bundles, collections, access, store, queue, masks,
                 thumbnails, surfaces, projector, reducer, clock, uow):
        self.items = items
        self.bundles = bundles
        self.collections = collections
        self.access = access
        self.store = store
        self.queue = queue
        self.masks = masks
        self.thumbnails = thumbnails
        self.surfaces = surfaces
        self.projector = projector
        self.reducer = reducer
        self.clock = clock
        self.uow = uow

    # ------------------------------------------------------------ queries

    def get(self, item_id) -> CollectionItem:
        return self.items.get(item_id)

    def directory_of(self, item: CollectionItem):
        if item.is_statmap and item.payload.from_nidm:
            bundle = self.bundles.get(item.payload.source.bundle_id)
            return bundle_dir(item.collection_id, bundle.zip_file)
        return collection_dir(item.collection_id)

    # --------------------------------------------------------- validation

    def check_map_file(self, upload, map_type, template, ignore_warning) -> QualityReport:
        """The upload-time quality checks of a statistic map (thresholded, outside MNI)."""
        upload.open()
        from io import BytesIO

        fileobj = BytesIO(upload.read())
        upload.seek(0)
        nii = map_quality.load_gzipped(upload.name, fileobj)
        report = QualityReport()
        report.is_thresholded, ratio_bad = map_quality.is_thresholded(nii)
        report.perc_bad_voxels = ratio_bad * 100.0
        report.values = {"is_thresholded": report.is_thresholded, "perc_bad_voxels": report.perc_bad_voxels}
        if report.is_thresholded and not ignore_warning and map_type != v.R:
            report.error = THRESHOLDED_MSG % report.perc_bad_voxels
            return report
        report.not_mni, report.brain_coverage, report.perc_voxels_outside = map_quality.not_in_mni(
            nii, self.masks.mask(template)
        )
        report.values.update(
            not_mni=report.not_mni,
            brain_coverage=report.brain_coverage,
            perc_voxels_outside=report.perc_voxels_outside,
        )
        if report.not_mni and not ignore_warning and map_type != v.R:
            report.error = NOT_MNI_MSG % report.perc_voxels_outside
        return report

    def project_surfaces(self, left, right, name):
        """fsaverage hemispheres -> (volume, left, right) uploads; field errors raise."""
        try:
            projected = self.projector.project(left, right, name)
        except SurfaceInputError as e:
            raise DomainValidationError({e.field: [e.message]})
        return projected

    # ---------------------------------------------------------- commands

    def require_change(self, actor, collection_id):
        if not self.access.can_change(actor, collection_id):
            raise PermissionDenied("cannot change collection %s" % collection_id)

    def add(self, actor, collection_id, kind, changes, files: ImageFilesInput, tags=None,
            bundle_id=None, check_access=True):
        """Store a new image and queue its processing; returns the new id."""
        if check_access:
            self.require_change(actor, collection_id)
        item = new_item(kind, collection_id, changes, bundle_id=bundle_id)
        if tags is not None:
            item.header.tags = frozenset(tags)
        directory = self.directory_of(item)
        self._store_uploads(item, files, directory)
        if item.is_statmap:
            self._complete_quality_metrics(item)
        item.ensure_species()
        with self.uow.atomic():
            item_id = self.items.add(item)
            self.collections.touch(collection_id, self.clock.now())
        self.queue.process_item(item_id)
        return item_id

    def change(self, actor, item_id, changes, files: Optional[ImageFilesInput] = None, tags=None,
               data_updates=None, check_access=True):
        """Change an image's fields and files; moving collections moves its files."""
        item = self.items.get(item_id)
        if check_access:
            self.require_change(actor, item.collection_id)
        old_collection = item.collection_id
        old_file = item.files.file
        apply_changes(item, changes)
        if data_updates:
            item.data = {**(item.data or {}), **data_updates}
        if tags is not None:
            item.header.tags = frozenset(tags)

        replaced = self._store_uploads(item, files or ImageFilesInput(), self._dir_for(item, old_collection))
        file_changed = item.files.file != old_file

        if file_changed and item.files.reduced_representation:
            self.store.delete(item.files.reduced_representation)
            item.with_files(reduced_representation=None)
            if item.is_statmap:
                self.items.delete_comparisons(item.id)

        if item.is_statmap:
            self._complete_quality_metrics(item)
        item.ensure_species()

        if item.collection_id != old_collection:
            self._move_files(item)

        with self.uow.atomic():
            self.items.save(item)
            self.collections.touch(item.collection_id, self.clock.now())
        for ref in replaced:
            self.store.delete(ref)
        if file_changed:
            self.queue.process_item(item.id)
        return item

    def delete(self, actor, item_id, check_access=True):
        item = self.items.get(item_id)
        if check_access:
            self.require_change(actor, item.collection_id)
        self._delete(item)

    def _delete(self, item):
        with self.uow.atomic():
            self.collections.touch(item.collection_id, self.clock.now())
            self.items.delete(item.id)
        for ref in item.file_refs().values():
            self.store.delete(ref)

    # --------------------------------------------------------- processing

    def process(self, item_id):
        """Render the glass-brain thumbnail and the fsaverage surface projections."""
        item = self.items.get(item_id)
        directory = self.directory_of(item)
        old_thumbnail = item.files.thumbnail
        with self.store.local_path(item.files.file) as path:
            jpg = self.thumbnails.glass_brain(path)
        item.with_files(
            thumbnail=self.store.save(directory, "glass_brain_%s.jpg" % item.id, jpg)
        )
        self._save_processed(item, [old_thumbnail])

        item = self.items.get(item_id)
        if (
            item.space.target_template_image in v.SURFACE_PROJECTION_TEMPLATES
            and item.space.data_origin == "volume"
        ):
            nearest = item.kind == "atlas" or (item.is_statmap and item.stats.map_type in (v.Pa, v.R))
            with self.store.local_path(item.files.file) as path:
                surfaces = self.surfaces.sample(path, nearest)
            old = [item.files.surface_left_file, item.files.surface_right_file]
            item.with_files(
                surface_left_file=self.store.save(directory, "%s.L.func.gii" % item.id, surfaces["lh"]),
                surface_right_file=self.store.save(directory, "%s.R.func.gii" % item.id, surfaces["rh"]),
            )
            self._save_processed(item, old)
            print("Surface image generation done.")

    def ensure_reduced_representation(self, item_id):
        item = self.items.get(item_id)
        ref = item.files.reduced_representation
        if ref and self.store.exists(ref):
            return item
        with self.store.local_path(item.files.file) as path:
            vector = self.reducer.reduce(path)
        item.with_files(
            reduced_representation=self.store.save(
                collection_dir(item.collection_id), "transform_4mm_%s.npy" % item.id, vector, overwrite=True
            )
        )
        self._save_processed(item, [])
        return item

    def _save_processed(self, item, superseded):
        if item.is_statmap:
            self._complete_quality_metrics(item)
        with self.uow.atomic():
            self.items.save(item)
            self.collections.touch(item.collection_id, self.clock.now())
        for ref in superseded:
            current = item.files.refs().values()
            if ref and ref not in current:
                self.store.delete(ref)

    # ------------------------------------------------------------ helpers

    def _dir_for(self, item, collection_id):
        if item.is_statmap and item.payload.from_nidm:
            return self.directory_of(item)
        return collection_dir(collection_id)

    def _store_uploads(self, item, files: ImageFilesInput, directory):
        """Save uploads in field order; returns the refs they superseded."""
        replaced = []
        for name, upload in files.uploads().items():
            ref = self.store.save(directory, upload.name, upload)
            if name == "label_description_file":
                replaced.append(item.payload.label_description_file)
                apply_changes(item, {"label_description_file": ref})
            else:
                replaced.append(getattr(item.files, name))
                item.with_files(**{name: ref})
        return [r for r in replaced if r]

    def _complete_quality_metrics(self, item):
        """Fill QA metrics the map lacks, and infer an 'Other' map type."""
        stats = item.stats
        if not item.files.file:
            return
        need_threshold = stats.perc_bad_voxels is None
        need_mni = stats.brain_coverage is None
        need_type = stats.map_type == v.OTHER
        if not (need_threshold or need_mni or need_type):
            return
        with self.store.open(item.files.file) as f:
            from io import BytesIO

            nii = map_quality.load_gzipped(item.files.file, BytesIO(f.read()))
        changes = {}
        if need_threshold:
            is_thr, ratio_bad = map_quality.is_thresholded(nii)
            changes.update(is_thresholded=is_thr, perc_bad_voxels=ratio_bad * 100.0)
        if need_mni:
            not_mni, coverage, outside = map_quality.not_in_mni(
                nii, self.masks.mask(item.space.target_template_image)
            )
            changes.update(not_mni=not_mni, brain_coverage=coverage, perc_voxels_outside=outside)
        if need_type:
            changes["map_type"] = map_quality.infer_map_type(nii)
        item.with_stats(**changes)

    def _move_files(self, item):
        directory = collection_dir(item.collection_id)
        moved = {name: self.store.move(ref, directory) for name, ref in item.files.refs().items()}
        item.with_files(**moved)
        if item.kind == "atlas" and item.payload.label_description_file:
            apply_changes(
                item, {"label_description_file": self.store.move(item.payload.label_description_file, directory)}
            )
