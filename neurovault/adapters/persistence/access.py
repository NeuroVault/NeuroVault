"""Collection-level permissions stored with django-guardian."""
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm

from neurovault.adapters.persistence.models import Collection


class GuardianAccessGrants:
    def _user(self, actor):
        if actor.user_id is None:
            return None
        return User.objects.filter(pk=actor.user_id).first()

    def can_change(self, actor, collection_id):
        return self._check(actor, collection_id, "statmaps.change_collection")

    def can_delete(self, actor, collection_id):
        return self._check(actor, collection_id, "statmaps.delete_collection")

    def _check(self, actor, collection_id, perm):
        if actor.is_superuser:
            return True
        user = self._user(actor)
        if user is None:
            return False
        collection = Collection.objects.filter(pk=collection_id).first()
        return collection is not None and user.has_perm(perm, collection)

    def grant_owner(self, collection_id, user_id):
        collection = Collection.objects.get(pk=collection_id)
        owner = User.objects.get(pk=user_id)
        assign_perm("delete_collection", owner, collection)
        assign_perm("change_collection", owner, collection)

    def sync_contributors(self, collection_id, user_ids):
        """Owner and `user_ids` can change the collection; nobody else can."""
        collection = Collection.objects.get(pk=collection_id)
        current = set(u.pk for u in get_users_with_perms(collection))
        wanted = set(user_ids) | ({collection.owner_id} if collection.owner_id else set())
        for user in User.objects.filter(pk__in=wanted - current):
            assign_perm("change_collection", user, collection)
        for user in User.objects.filter(pk__in=current - wanted):
            remove_perm("change_collection", user, collection)
