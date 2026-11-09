from rest_framework.permissions import SAFE_METHODS, BasePermission, DjangoObjectPermissions

from neurovault.adapters.http import actor
from neurovault.config.bootstrap import services


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
        return services().collections.can_change(actor(request), obj.collection_id)
