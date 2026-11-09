"""Driven ports: what the use cases need from the outside world.

Adapters in neurovault/adapters implement these; neurovault/bootstrap.py wires
them. Tests substitute the in-memory fakes in core/application/tests/fakes.py.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional, Protocol

from neurovault.core.domain.collection import Collection
from neurovault.core.domain.items import CollectionItem, MapRef, NIDMBundle
from neurovault.core.domain.metaanalysis import Metaanalysis


class Upload(Protocol):
    """An uploaded file: Django's UploadedFile satisfies this."""

    name: str

    def read(self, *args) -> bytes: ...

    def chunks(self) -> Iterable[bytes]: ...


@dataclass(frozen=True)
class Actor:
    user_id: Optional[int]
    is_superuser: bool = False

    @property
    def is_authenticated(self):
        return self.user_id is not None


SYSTEM = Actor(user_id=None, is_superuser=True)


# ---------------------------------------------------------------- persistence


class UnitOfWork(Protocol):
    def atomic(self) -> AbstractContextManager: ...

    def on_commit(self, fn) -> None: ...


class CollectionRepository(Protocol):
    def get(self, collection_id: int) -> Collection: ...

    def find_by_token(self, token: str) -> Optional[Collection]: ...

    def find_by_name(self, name: str) -> Optional[Collection]: ...

    def add(self, collection: Collection) -> int: ...

    def save(self, collection: Collection) -> None: ...

    def delete(self, collection_id: int) -> None: ...

    def token_exists(self, token: str) -> bool: ...

    def touch(self, collection_id: int, when: datetime) -> None: ...


class ItemRepository(Protocol):
    def get(self, item_id: int) -> CollectionItem: ...

    def add(self, item: CollectionItem) -> int: ...

    def save(self, item: CollectionItem) -> None: ...

    def delete(self, item_id: int) -> None: ...

    def ids_in_collection(self, collection_id: int) -> list: ...

    def ids_from_bundle(self, bundle_id: int) -> list: ...

    def delete_comparisons(self, item_id: int) -> None: ...


class BundleRepository(Protocol):
    def get(self, bundle_id: int) -> NIDMBundle: ...

    def add(self, bundle: NIDMBundle) -> int: ...

    def save(self, bundle: NIDMBundle) -> None: ...

    def delete(self, bundle_id: int) -> None: ...

    def ids_in_collection(self, collection_id: int) -> list: ...

    def count_named_like(self, collection_id: int, prefix: str) -> int: ...


class MetaanalysisRepository(Protocol):
    def get(self, metaanalysis_id: int) -> Metaanalysis: ...

    def add(self, metaanalysis: Metaanalysis) -> int: ...

    def save(self, metaanalysis: Metaanalysis) -> None: ...

    def active_for(self, owner_id: int) -> list: ...


# -------------------------------------------------------------------- access


class AccessGrants(Protocol):
    """Collection-level permissions (owner: change+delete, contributors: change)."""

    def can_change(self, actor: Actor, collection_id: int) -> bool: ...

    def can_delete(self, actor: Actor, collection_id: int) -> bool: ...

    def grant_owner(self, collection_id: int, user_id: int) -> None: ...

    def sync_contributors(self, collection_id: int, user_ids: Iterable[int]) -> None: ...


# ------------------------------------------------------------------- storage


class MapStore(Protocol):
    def save(self, directory: str, filename: str, content, overwrite: bool = False) -> MapRef: ...

    def save_local(self, directory: str, filename: str, path: str) -> MapRef: ...

    def open(self, ref: MapRef): ...

    def local_path(self, ref: MapRef) -> AbstractContextManager:
        """A path to read the file at, for tools that need one (read-only)."""

    def exists(self, ref: MapRef) -> bool: ...

    def delete(self, ref: MapRef) -> None: ...

    def delete_tree(self, directory: str) -> None: ...

    def move(self, ref: MapRef, directory: str) -> MapRef: ...


# --------------------------------------------------------------------- tasks


class TaskQueue(Protocol):
    def process_item(self, item_id: int) -> None: ...


# --------------------------------------------------------------- neuroimaging


class TemplateMasks(Protocol):
    def mask(self, template: str): ...


@dataclass(frozen=True)
class ProjectedSurface:
    volume_name: str
    volume: bytes
    left_name: str
    left: bytes
    right_name: str
    right: bytes


class SurfaceInputError(Exception):
    def __init__(self, field, message):
        self.field, self.message = field, message
        super().__init__(message)


class SurfaceProjector(Protocol):
    """fsaverage surface maps -> MNI volume (FreeSurfer)."""

    def project(self, left: Upload, right: Upload, name: str) -> ProjectedSurface: ...


class SurfaceSampler(Protocol):
    """MNI volume -> fsaverage surface maps for the viewer."""

    def sample(self, volume_path: str, nearest: bool) -> dict: ...


class ThumbnailRenderer(Protocol):
    def glass_brain(self, volume_path: str) -> bytes: ...


class MapReducer(Protocol):
    def reduce(self, volume_path: str) -> bytes: ...


@dataclass(frozen=True)
class MetaAnalysisInput:
    path: str
    map_type: str
    number_of_subjects: Optional[int]


@dataclass(frozen=True)
class MetaAnalysisResult:
    images: dict  # name -> gzipped NIfTI bytes ("z", "p", "ffx_stat")
    n_maps: int
    weighted: bool


class MetaAnalysisEngine(Protocol):
    def run(self, maps: list) -> MetaAnalysisResult: ...


class NIDMPackage(Protocol):
    statmaps: list  # [{"name", "type", "filename"}]
    ttl_filename: str
    ttl_size: int

    def ttl_text(self) -> str: ...

    def read_map(self, statmap: dict) -> bytes: ...

    def bundled_files(self) -> list: ...  # [(filename, bytes)]

    def cleanup(self) -> None: ...


class NIDMParser(Protocol):
    def parse(self, zip_upload: Upload) -> NIDMPackage: ...


class UploadWorkspace(Protocol):
    """A scratch area for an uploaded archive or folder; a context manager."""

    def __enter__(self) -> "UploadWorkspace": ...

    def __exit__(self, *exc) -> None: ...

    def extract(self, archive: Upload) -> None: ...

    def write(self, upload: Upload) -> None: ...

    def write_tree(self, uploads: list, relative_paths: list) -> None: ...

    def collect(self, allowed_extensions: list) -> list: ...  # [(label, path, atlas xml path or None)]

    def squeezed_volume(self, path: str) -> tuple: ...  # (base name, .nii.gz bytes)

    def read(self, path: str) -> bytes: ...


# ------------------------------------------------------------------ external


@dataclass(frozen=True)
class PaperProperties:
    title: str
    authors: str
    url: str
    publication_date: date
    journal_name: str


class PublicationLookup(Protocol):
    def lookup(self, doi: str) -> PaperProperties: ...


class Notifier(Protocol):
    def notify(self, kind: str, subject: str, user_ids: Iterable[int], context: dict) -> None: ...


class Directory(Protocol):
    """Facts outside the aggregates: user names and public URLs."""

    def username(self, user_id: int) -> str: ...

    def bundle_url(self, collection_id: int, bundle_name: str) -> str: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
