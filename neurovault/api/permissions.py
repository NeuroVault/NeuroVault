from rest_framework.permissions import DjangoObjectPermissions


class ObjectOnlyPermissions(DjangoObjectPermissions):

    def has_permission(self, request, view):
        return True
