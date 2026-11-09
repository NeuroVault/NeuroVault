"""User names and public URLs, from the Django models and settings."""
import os

from django.conf import settings
from django.contrib.auth.models import User

from neurovault.adapters.persistence.models import Collection


class DjangoDirectory:
    def username(self, user_id):
        return User.objects.get(pk=user_id).username

    def bundle_url(self, collection_id, bundle_name):
        """Absolute URL prefix of a bundle's files, as written into its TTL."""
        collection = Collection.objects.get(pk=collection_id)
        return settings.DOMAIN_NAME + os.path.join(collection.get_absolute_url(), bundle_name) + "/"
