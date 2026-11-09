"""Composition root: builds the application services from their adapters.

Driving adapters (views, API, tasks, commands) call `services()`; tests can
build their own services with the fakes in core/application/tests/fakes.py.
"""
from dataclasses import dataclass
from functools import lru_cache

from neurovault.core.application.services.bundles import BundleService
from neurovault.core.application.services.collections import CollectionService
from neurovault.core.application.services.items import ItemService
from neurovault.core.application.services.metaanalyses import MetaanalysisService
from neurovault.core.application.services.uploads import UploadService


@dataclass
class Services:
    collections: CollectionService
    items: ItemService
    bundles: BundleService
    uploads: UploadService
    metaanalyses: MetaanalysisService


def build():
    from neurovault.adapters.external.clock import DjangoClock
    from neurovault.adapters.external.crossref import CrossRefLookup
    from neurovault.adapters.external.mail import EmailNotifier
    from neurovault.adapters.neuroimaging.freesurfer import FreeSurferProjector
    from neurovault.adapters.neuroimaging.nidm_upload import RdflibNIDMParser
    from neurovault.adapters.neuroimaging.nimare import NiMAREEngine
    from neurovault.adapters.neuroimaging.rendering import (
        FsaverageSurfaceSampler,
        NilearnMapReducer,
        NilearnThumbnailRenderer,
        StaticTemplateMasks,
    )
    from neurovault.adapters.neuroimaging.workspace import UploadWorkspace
    from neurovault.adapters.persistence.access import GuardianAccessGrants
    from neurovault.adapters.persistence.directory import DjangoDirectory
    from neurovault.adapters.persistence.repositories import (
        DjangoBundleRepository,
        DjangoCollectionRepository,
        DjangoItemRepository,
        DjangoMetaanalysisRepository,
        DjangoUnitOfWork,
    )
    from neurovault.adapters.queue.celery import CeleryTaskQueue
    from neurovault.adapters.storage.local import LocalMapStore

    uow, clock, store = DjangoUnitOfWork(), DjangoClock(), LocalMapStore()
    access, directory = GuardianAccessGrants(), DjangoDirectory()
    collections, items, bundles = (
        DjangoCollectionRepository(), DjangoItemRepository(), DjangoBundleRepository()
    )
    item_service = ItemService(
        items, bundles, collections, access, store, CeleryTaskQueue(), StaticTemplateMasks(),
        NilearnThumbnailRenderer(), FsaverageSurfaceSampler(), FreeSurferProjector(),
        NilearnMapReducer(), clock, uow,
    )
    bundle_service = BundleService(
        bundles, items, collections, item_service, store, RdflibNIDMParser(), clock, uow,
        directory,
    )
    collection_service = CollectionService(
        collections, items, bundles, access, store, CrossRefLookup(), EmailNotifier(), clock, uow,
        item_service, bundle_service, directory,
    )
    return Services(
        collections=collection_service,
        items=item_service,
        bundles=bundle_service,
        uploads=UploadService(item_service, bundle_service, UploadWorkspace),
        metaanalyses=MetaanalysisService(
            DjangoMetaanalysisRepository(), items, collection_service, item_service, store,
            NiMAREEngine(), uow,
        ),
    )


@lru_cache(maxsize=None)
def services() -> Services:
    return build()
