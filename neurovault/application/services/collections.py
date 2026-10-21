"""Use cases for collections: create, change, share, delete."""
from __future__ import annotations

from typing import Callable, Iterable, Optional

from neurovault.domain.collection import Collection
from neurovault.domain.errors import DomainValidationError, PermissionDenied

from ..layout import collection_dir

NEW_CONTRIBUTOR_SUBJECT = "%s has added you to a NeuroVault collection"


class CollectionService:
    def __init__(self, collections, items, bundles, access, store, lookup, notifier, clock, uow,
                 item_service, bundle_service, owner_name: Callable[[int], str]):
        self.collections = collections
        self.items = items
        self.bundles = bundles
        self.access = access
        self.store = store
        self.lookup = lookup
        self.notifier = notifier
        self.clock = clock
        self.uow = uow
        self.item_service = item_service
        self.bundle_service = bundle_service
        self.owner_name = owner_name

    def get(self, collection_id) -> Collection:
        return self.collections.get(collection_id)

    def complete_publication(self, changes: dict, require_name=True) -> dict:
        """Fill name, authors, paper URL and journal from the DOI, if any.

        A blank DOI becomes None. Without a DOI a name is required.
        """
        changes = dict(changes)
        doi = changes.get("DOI")
        if doi is not None and doi.strip() == "":
            changes["DOI"] = doi = None
        if doi:
            changes["DOI"] = doi = doi.strip()
            try:
                paper = self.lookup.lookup(doi)
            except Exception:
                raise DomainValidationError({"DOI": ["Could not resolve DOI"]})
            changes.update(
                name=paper.title, authors=paper.authors, paper_url=paper.url,
                journal_name=paper.journal_name,
            )
        elif require_name and not changes.get("name"):
            msg = ["You need to set the name or the DOI"]
            raise DomainValidationError({"name": msg, "DOI": msg})
        return changes

    def save(self, actor, collection_id: Optional[int], changes: dict,
             contributor_ids: Optional[Iterable[int]] = None,
             community_ids: Optional[Iterable[int]] = None,
             absolute_url: Optional[Callable[[int], str]] = None,
             owner_id: Optional[int] = None):
        """Create (collection_id None) or change a collection.

        Contributors added here are emailed when `absolute_url` is given.
        Returns the collection id.
        """
        creating = collection_id is None
        if creating:
            collection = Collection(id=None, owner_id=owner_id or actor.user_id, name=None)
        else:
            collection = self.collections.get(collection_id)
            if not self.access.can_change(actor, collection_id):
                raise PermissionDenied("cannot change collection %s" % collection_id)
        previous = set(collection.contributor_ids)

        collection.apply(changes)
        if contributor_ids is not None:
            collection.contributor_ids = frozenset(contributor_ids)
        if community_ids is not None:
            collection.community_ids = frozenset(community_ids)
        collection.ensure_token(self.collections.token_exists)
        collection.normalize(self.clock.now())

        with self.uow.atomic():
            if creating:
                collection_id = self.collections.add(collection)
                self.access.grant_owner(collection_id, collection.owner_id)
            else:
                self.collections.save(collection)
            if contributor_ids is not None:
                self.access.sync_contributors(collection_id, collection.contributor_ids)

        added = set(collection.contributor_ids) - previous
        if contributor_ids is not None and absolute_url is not None and added:
            owner = self.owner_name(collection.owner_id)
            self.notifier.notify(
                "new_contributor",
                NEW_CONTRIBUTOR_SUBJECT % owner,
                sorted(added),
                {"owner": owner, "collection": collection.name, "url": absolute_url(collection_id)},
            )
        return collection_id

    def refresh_journal_name(self, collection_id):
        """Look up and store the journal of a collection's DOI; returns it."""
        from ..ports import SYSTEM

        journal = self.lookup.lookup(self.collections.get(collection_id).DOI).journal_name
        self.save(SYSTEM, collection_id, {"journal_name": journal})
        return journal

    def temporary_for(self, user_id, username, private):
        """The per-user collection that Neurosynth and Neuropower uploads land in."""
        name = "%s's temporary collection" % username
        existing = self.collections.find_by_name(name)
        if existing is not None:
            return existing.id
        collection = Collection(id=None, owner_id=user_id, name=name, private=private)
        from neurovault.domain.collection import generate_token

        collection.private_token = generate_token(self.collections.token_exists)
        collection.normalize(self.clock.now())
        with self.uow.atomic():
            collection_id = self.collections.add(collection)
            self.access.grant_owner(collection_id, user_id)
        return collection_id

    def delete(self, actor, collection_id, check_access=True):
        if check_access and not self.access.can_delete(actor, collection_id):
            raise PermissionDenied("cannot delete collection %s" % collection_id)
        for item_id in self.items.ids_in_collection(collection_id):
            self.item_service.delete(None, item_id, check_access=False)
        for bundle_id in self.bundles.ids_in_collection(collection_id):
            self.bundle_service.delete(None, bundle_id, check_access=False)
        with self.uow.atomic():
            self.collections.delete(collection_id)
        self.store.delete_tree(collection_dir(collection_id))
