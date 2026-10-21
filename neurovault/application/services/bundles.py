"""Use cases for NIDM-Results bundles."""
from __future__ import annotations

import os

from neurovault.domain import nidm
from neurovault.domain.errors import DomainValidationError
from neurovault.domain.items import ItemHeader, NIDMBundle

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
                 public_url):
        self.bundles = bundles
        self.items = items
        self.collections = collections
        self.item_service = item_service
        self.store = store
        self.parser = parser
        self.clock = clock
        self.uow = uow
        self.public_url = public_url  # callable(collection_id, bundle_name) -> absolute url prefix

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
        directory = bundle_dir(collection_id, prepared.zip_upload.name)
        zip_ref = self.store.save(directory, prepared.zip_upload.name, prepared.zip_upload)
        ttl_ref = self.store.save(directory, package.ttl_filename, package.ttl_text().encode("utf-8"))

        if replacing_id is None:
            bundle = NIDMBundle(
                header=ItemHeader(id=None, collection_id=collection_id, name=prepared.name,
                                  description=description, tags=frozenset(tags)),
                zip_file=zip_ref,
                ttl_file=ttl_ref,
            )
            with self.uow.atomic():
                bundle_id = self.bundles.add(bundle)
                self.collections.touch(collection_id, self.clock.now())
        else:
            bundle = self.bundles.get(replacing_id)
            bundle.header.name, bundle.header.description = prepared.name, description
            bundle.zip_file, bundle.ttl_file = zip_ref, ttl_ref
            with self.uow.atomic():
                self.bundles.save(bundle)
                self.collections.touch(collection_id, self.clock.now())
            bundle_id = bundle.id

        map_ids = []
        for s in package.statmaps:
            with open(s["file"], "rb") as f:
                upload = NamedBytes(os.path.split(s["file"])[-1], f.read())
            map_ids.append(
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
                    ImageFilesInput(file=upload),
                    bundle_id=bundle_id,
                    check_access=False,
                )
            )

        for filename, path in package.bundled_files():
            if not self.store.exists(os.path.join(directory, filename)):
                if os.path.isfile(path):
                    self.store.save_local(directory, filename, path)
        package.cleanup()

        if map_ids:
            self._rewrite_ttl(bundle_id, map_ids[0])
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
            self.public_url(bundle.collection_id, bundle.header.name),
        )
        with self.store.local_path(bundle.ttl_file) as path:
            with open(path, "w") as ttlf:
                ttlf.write(updated)


class PreparedBundle:
    def __init__(self, name, zip_upload, package):
        self.name = name
        self.zip_upload = zip_upload
        self.package = package
