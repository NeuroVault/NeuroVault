from rest_framework.permissions import (DjangoObjectPermissions,
                                        SAFE_METHODS, Http404)
from guardian.ctypes import get_ctype_from_polymorphic


class ObjectOnlyPermissions(DjangoObjectPermissions):

    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated()
        )


class ObjectOnlyPolymorphicPermissions(ObjectOnlyPermissions):

    def has_object_permission(self, request, view, obj):
        ctype = get_ctype_from_polymorphic(obj)

        model_cls = ctype.model_class()
        user = request.user

        perms = self.get_required_object_permissions(request.method, model_cls)

        if not user.has_perms(perms, obj):
            if request.method in SAFE_METHODS:
                raise Http404

            read_perms = self.get_required_object_permissions('GET', model_cls)
            if not user.has_perms(read_perms, obj):
                raise Http404

            return False

        return True
