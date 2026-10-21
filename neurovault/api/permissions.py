from rest_framework.permissions import SAFE_METHODS, BasePermission, DjangoObjectPermissions

from neurovault.application.ports import Actor
from neurovault.bootstrap import services


class ObjectOnlyPermissions(DjangoObjectPermissions):
    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS
            or request.user
            and request.user.is_authenticated
        )


class CollectionItemPermissions(BasePermission):
    """Reads are open; changing or deleting an item needs change rights on its collection."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        actor = Actor(request.user.pk, request.user.is_superuser)
        return services().items.access.can_change(actor, obj.collection_id)
