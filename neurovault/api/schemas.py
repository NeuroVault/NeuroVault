from drf_spectacular.contrib.django_oauth_toolkit import DjangoOAuthToolkitScheme
from rest_framework.permissions import SAFE_METHODS

class JankyAuth(DjangoOAuthToolkitScheme):
    target_class = 'oauth2_provider.contrib.rest_framework.authentication.OAuth2Authentication'
    name = 'bearerAuth'  # name used in the schema
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            }

    def get_security_requirement(self, auto_schema):
        from neurovault.api.permissions import ObjectOnlyPermissions, ObjectOnlyPolymorphicPermissions
        from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope

        view = auto_schema.view
        request = view.request

        for permission in auto_schema.view.get_permissions():
            if isinstance(permission, (ObjectOnlyPolymorphicPermissions, ObjectOnlyPermissions)):
                if not permission.has_permission(request, view):
                    return {self.name: []}
            if isinstance(permission, IsAuthenticatedOrTokenHasScope):
                return {self.name: []}
        return
