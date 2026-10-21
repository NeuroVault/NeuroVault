"""In-memory implementations of the ports, for use-case tests without Django."""
import copy
import itertools
import os
import tempfile
from contextlib import contextmanager, nullcontext
from io import BytesIO

from neurovault.domain.errors import NotFound

from .ports import ProjectedSurface


class _Repository:
    def __init__(self):
        self.rows = {}
        self._ids = itertools.count(1)

    def get(self, key):
        if key not in self.rows:
            raise NotFound(key)
        return copy.deepcopy(self.rows[key])

    def _store(self, entity, key):
        self.rows[key] = copy.deepcopy(entity)

    def delete(self, key):
        self.rows.pop(key, None)


class InMemoryItemRepository(_Repository):
    def __init__(self, ids=None):
        super().__init__()
        if ids is not None:
            self._ids = ids
        self.comparisons_deleted = []

    def add(self, item):
        item.header.id = next(self._ids)
        self._store(item, item.id)
        return item.id

    def save(self, item):
        if item.id not in self.rows:
            raise NotFound(item.id)
        self._store(item, item.id)

    def ids_in_collection(self, collection_id):
        return sorted(k for k, v in self.rows.items() if v.collection_id == collection_id)

    def ids_from_bundle(self, bundle_id):
        return sorted(
            k for k, v in self.rows.items()
            if v.is_statmap and v.payload.source and v.payload.source.bundle_id == bundle_id
        )

    def delete_comparisons(self, item_id):
        self.comparisons_deleted.append(item_id)


class InMemoryBundleRepository(_Repository):
    def __init__(self, ids=None):
        super().__init__()
        if ids is not None:
            self._ids = ids

    def add(self, bundle):
        bundle.header.id = next(self._ids)
        self._store(bundle, bundle.id)
        return bundle.id

    def save(self, bundle):
        self._store(bundle, bundle.id)

    def ids_in_collection(self, collection_id):
        return sorted(k for k, v in self.rows.items() if v.collection_id == collection_id)

    def count_named_like(self, collection_id, prefix):
        return sum(
            1 for v in self.rows.values()
            if v.collection_id == collection_id and v.header.name.startswith(prefix)
        )


class InMemoryCollectionRepository(_Repository):
    def __init__(self):
        super().__init__()
        self.touched = []

    def find_by_token(self, token):
        return next((copy.deepcopy(c) for c in self.rows.values() if c.private_token == token), None)

    def find_by_name(self, name):
        return next((copy.deepcopy(c) for c in self.rows.values() if c.name == name), None)

    def add(self, collection):
        collection.id = next(self._ids)
        self._store(collection, collection.id)
        return collection.id

    def save(self, collection):
        self._store(collection, collection.id)

    def token_exists(self, token):
        return any(c.private_token == token for c in self.rows.values())

    def touch(self, collection_id, when):
        self.touched.append(collection_id)
        self.rows[collection_id].modify_date = when


class InMemoryMetaanalysisRepository(_Repository):
    def add(self, m):
        m.id = next(self._ids)
        self._store(m, m.id)
        return m.id

    def save(self, m):
        self._store(m, m.id)

    def active_for(self, owner_id):
        return [copy.deepcopy(m) for k, m in sorted(self.rows.items())
                if m.owner_id == owner_id and m.status == "active"]


class FakeUnitOfWork:
    def atomic(self):
        return nullcontext()

    def on_commit(self, fn):
        fn()


class FakeAccess:
    """Owner: change and delete; contributors: change; superusers: everything."""

    def __init__(self, collections):
        self.collections = collections
        self.grants = {}

    def can_change(self, actor, collection_id):
        if actor.is_superuser:
            return True
        return actor.user_id in self.grants.get(collection_id, {}).get("change", set())

    def can_delete(self, actor, collection_id):
        if actor.is_superuser:
            return True
        return actor.user_id in self.grants.get(collection_id, {}).get("delete", set())

    def grant_owner(self, collection_id, user_id):
        g = self.grants.setdefault(collection_id, {"change": set(), "delete": set()})
        g["change"].add(user_id)
        g["delete"].add(user_id)

    def sync_contributors(self, collection_id, user_ids):
        owner = self.collections.rows[collection_id].owner_id
        g = self.grants.setdefault(collection_id, {"change": set(), "delete": set()})
        g["change"] = set(user_ids) | {owner}


class InMemoryMapStore:
    """Same naming rules as the local store: taken names get _1, _2, ...; .nii.gz kept whole."""

    def __init__(self):
        self.files = {}
        self._tmp = tempfile.mkdtemp()

    def _available(self, name):
        if name not in self.files:
            return name
        directory, base = os.path.split(name)
        root, ext = os.path.splitext(base)
        for double in (".nii", ".nidm"):
            if root.endswith(double):
                root, ext = root[: -len(double)], double + ext
        for n in itertools.count(1):
            candidate = os.path.join(directory, "%s_%s%s" % (root, n, ext))
            if candidate not in self.files:
                return candidate

    def save(self, directory, filename, content, overwrite=False):
        name = os.path.join(directory, os.path.basename(filename).replace(" ", "_"))
        if not overwrite:
            name = self._available(name)
        if hasattr(content, "read"):
            if hasattr(content, "seek"):
                content.seek(0)
            content = content.read()
        self.files[name] = content if isinstance(content, bytes) else content.encode()
        return name

    def save_local(self, directory, filename, path):
        with open(path, "rb") as f:
            return self.save(directory, filename, f.read())

    def open(self, ref):
        return BytesIO(self.files[ref])

    @contextmanager
    def local_path(self, ref):
        path = os.path.join(self._tmp, ref.replace("/", "__"))
        with open(path, "wb") as f:
            f.write(self.files[ref])
        yield path
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.files[ref] = f.read()
            os.remove(path)

    def exists(self, ref):
        return ref in self.files

    def delete(self, ref):
        self.files.pop(ref, None)

    def delete_tree(self, directory):
        prefix = directory.rstrip("/") + "/"
        for name in [n for n in self.files if n.startswith(prefix)]:
            del self.files[name]

    def move(self, ref, directory):
        new_ref = self._available(os.path.join(directory, os.path.basename(ref)))
        self.files[new_ref] = self.files.pop(ref)
        return new_ref


class RecordingQueue:
    def __init__(self):
        self.processed = []

    def process_item(self, item_id):
        self.processed.append(item_id)


class NoMasks:
    def mask(self, template):
        return None


class FakeThumbnails:
    def glass_brain(self, volume_path):
        return b"jpg"


class FakeSurfaces:
    def sample(self, volume_path, nearest):
        return {"lh": b"<lh/>", "rh": b"<rh/>"}


class FakeProjector:
    def project(self, left, right, name):
        return ProjectedSurface(name + ".nii.gz", b"vol", name + ".lh.gii", b"lh", name + ".rh.gii", b"rh")


class FakeReducer:
    def reduce(self, volume_path):
        return b"npy"


class FixedClock:
    def __init__(self, now):
        self._now = now

    def now(self):
        return self._now


class FakeLookup:
    def __init__(self, papers=None):
        self.papers = papers or {}

    def lookup(self, doi):
        if doi not in self.papers:
            raise LookupError(doi)
        return self.papers[doi]


class RecordingNotifier:
    def __init__(self):
        self.sent = []

    def notify(self, kind, subject, user_ids, context):
        self.sent.append((kind, subject, list(user_ids), context))


class FakeNIDMPackage:
    def __init__(self, statmaps, ttl, files=()):
        self.statmaps = statmaps
        self.ttl_filename = "nidm.ttl"
        self.ttl_size = len(ttl)
        self._ttl = ttl
        self._files = list(files)
        self.cleaned = False

    def ttl_text(self):
        return self._ttl

    def bundled_files(self):
        return self._files

    def cleanup(self):
        self.cleaned = True


class FakeNIDMParser:
    def __init__(self, package):
        self.package = package

    def parse(self, zip_upload):
        return self.package


