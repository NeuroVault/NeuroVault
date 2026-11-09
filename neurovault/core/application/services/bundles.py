"""Use cases for NIDM-Results bundles."""
from __future__ import annotations

import os

from neurovault.core.domain import nidm
from neurovault.core.domain.errors import DomainValidationError
from neurovault.core.domain.items import ItemHeader, NIDMBundle

from ..layout import bundle_dir
from .items import ImageFilesInput


class NamedBytes:
    """A file-like upload built from bytes."""

    def __init__(self, name, content):
        from io import BytesIO

        self.name = name
        self._buf = BytesIO(content)
        self.size = len(content)

    def open(self, *args):
        self._buf.seek(0)
        return self

    def read(self, *args):
        return self._buf.read(*args)

    def seek(self, pos):
        self._buf.seek(pos)

    def chunks(self, chunk_size=None):
        self._buf.seek(0)
        yield self._buf.read()


class BundleService:
    def __init__(self, bundles, items, collections, item_service, store, parser, clock, uow,
                 directory):
        self.bundles = bundles
        self.items = items
        self.collections = collections
        self.item_service = item_service
        self.store = store
        self.parser = parser
        self.clock = clock
        self.uow = uow
        self.directory = directory

    def get(self, bundle_id) -> NIDMBundle:
        return self.bundles.get(bundle_id)

    def prepare(self, collection_id, zip_upload, replacing_id=None):
        """Name the bundle, parse the zip and validate its maps.

        Returns a `PreparedBundle` that `ingest` stores; parse errors raise
        DomainValidationError.
        """
        base = nidm.base_name(zip_upload.name)
        count = self.bundles.count_named_like(collection_id, base + ".nidm")
        name = nidm.bundle_name(zip_upload.name, count, replacing=replacing_id is not None)
        zip_upload.name = name + ".zip"
        try:
            package = self.parser.parse(zip_upload)
        except Exception as e:
            raise DomainValidationError("The NIDM file was not readable: {0}".format(e))
        return PreparedBundle(name=name, zip_upload=zip_upload, package=package)

    def ingest(self, actor, collection_id, prepared, description="", tags=(), replacing_id=None,
               check_access=True):
        """Store a prepared bundle and its statistic maps; returns the bundle id."""
        if check_access:
            self.item_service.require_change(actor, collection_id)
        if replacing_id is not None:
            self._remove_contents(self.bundles.get(replacing_id))

        package = prepared.package
        bundle_id = None
        try:
            bundle_id = self._store_bundle(collection_id, prepared, description, tags, replacing_id)
            directory = bundle_dir(collection_id, prepared.zip_upload.name)
            map_ids = [
                self.item_service.add(
                    actor,
                    collection_id,
                    "statmap",
                    {
                        "name": s["name"],
                        "description": description,
                        "map_type": s["type"],
                        "analysis_level": "Other",
                        "number_of_subjects": 0,
                    },
                    ImageFilesInput(file=NamedBytes(s["filename"], package.read_map(s))),
                    bundle_id=bundle_id,
                    check_access=False,
                )
                for s in package.statmaps
            ]
            for filename, content in package.bundled_files():
                if not self.store.exists(os.path.join(directory, filename)):
                    self.store.save(directory, filename, content)
            if map_ids:
                self._rewrite_ttl(bundle_id, map_ids[0])
        except Exception:
            # leave no half-stored bundle behind
            if bundle_id is not None:
                self.delete(None, bundle_id, check_access=False)
            raise
        finally:
            package.cleanup()
        return bundle_id

    def _store_bundle(self, collection_id, prepared, description, tags, replacing_id):
        package = prepared.package
        directory = bundle_dir(collection_id, prepared.zip_upload.name)
        zip_ref = self.store.save(directory, prepared.zip_upload.name, prepared.zip_upload)
        ttl_ref = self.store.save(directory, package.ttl_filename, package.ttl_text().encode("utf-8"))
        with self.uow.atomic():
            if replacing_id is None:
                bundle_id = self.bundles.add(NIDMBundle(
                    header=ItemHeader(id=None, collection_id=collection_id, name=prepared.name,
                                      description=description, tags=frozenset(tags)),
                    zip_file=zip_ref,
                    ttl_file=ttl_ref,
                ))
            else:
                bundle = self.bundles.get(replacing_id)
                bundle.header.name, bundle.header.description = prepared.name, description
                bundle.zip_file, bundle.ttl_file = zip_ref, ttl_ref
                self.bundles.save(bundle)
                bundle_id = bundle.id
            self.collections.touch(collection_id, self.clock.now())
        return bundle_id

    def change(self, actor, bundle_id, changes, tags=None, check_access=True):
        """Change a bundle's description or name without a new zip."""
        bundle = self.bundles.get(bundle_id)
        if check_access:
            self.item_service.require_change(actor, bundle.collection_id)
        for key in ("name", "description", "is_valid"):
            if key in changes:
                setattr(bundle.header, key, changes[key])
        if tags is not None:
            bundle.header.tags = frozenset(tags)
        with self.uow.atomic():
            self.bundles.save(bundle)
            self.collections.touch(bundle.collection_id, self.clock.now())
        return bundle

    def delete(self, actor, bundle_id, check_access=True):
        bundle = self.bundles.get(bundle_id)
        if check_access:
            self.item_service.require_change(actor, bundle.collection_id)
        self._remove_contents(bundle)
        with self.uow.atomic():
            self.collections.touch(bundle.collection_id, self.clock.now())
            self.bundles.delete(bundle.id)
        self.store.delete_tree(bundle_dir(bundle.collection_id, bundle.zip_file))

    def _remove_contents(self, bundle):
        for item_id in self.items.ids_from_bundle(bundle.id):
            self.item_service.delete(None, item_id, check_access=False)
        self.store.delete_tree(bundle_dir(bundle.collection_id, bundle.zip_file))

    def _rewrite_ttl(self, bundle_id, first_map_id):
        bundle = self.bundles.get(bundle_id)
        first_map = self.items.get(first_map_id)
        with self.store.open(bundle.ttl_file) as f:
            ttl = f.read().decode("utf-8")
        updated = nidm.rewrite_ttl_locations(
            ttl,
            os.path.basename(first_map.files.file),
            self.directory.bundle_url(bundle.collection_id, bundle.header.name),
        )
        self.store.save(
            os.path.dirname(bundle.ttl_file), os.path.basename(bundle.ttl_file),
            updated.encode("utf-8"), overwrite=True,
        )


class PreparedBundle:
    def __init__(self, name, zip_upload, package):
        self.name = name
        self.zip_upload = zip_upload
        self.package = package
