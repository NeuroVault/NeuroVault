"""Request-level helpers shared by the web and API adapters: who is acting, and
which collection or image a URL names, with the private-collection rules."""
import re

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from neurovault.adapters.persistence.models import Collection, Item
from neurovault.config.bootstrap import services
from neurovault.core.application.ports import Actor


class HttpRedirectException(Exception):
    """A private collection or image was addressed by id instead of its token."""


def actor(request):
    if not request.user.is_authenticated:
        return Actor(None)
    return Actor(request.user.pk, request.user.is_superuser)


def can_change(request, collection):
    """Owner, contributor or administrator of `collection`."""
    return services().collections.can_change(actor(request), collection.pk)


def can_delete(request, collection):
    """Owner or administrator of `collection`."""
    return services().collections.can_delete(actor(request), collection.pk)


def get_collection(cid, request, mode=None):
    """The collection named by a primary key or private token.

    A private collection addressed by its id: members are redirected to the
    token URL (or refused, for files and the API); everyone else is refused.
    """
    keyargs = {"pk": cid}
    private_url = re.match(r"^[A-Z]{8}$", cid)
    if private_url is not None:
        keyargs = {"private_token": cid}
    try:
        collection = Collection.objects.get(**keyargs)
    except Collection.DoesNotExist:
        raise Http404
    if private_url is None and collection.private:
        if can_change(request, collection) and mode not in ["file", "api"]:
            raise HttpRedirectException(collection.get_absolute_url())
        raise PermissionDenied()
    return collection


def get_image(pk, collection_cid, request, mode=None):
    """The image `pk`, applying the same private-collection rules."""
    image = get_object_or_404(Item, pk=pk)
    if image.collection.private and image.collection.private_token != collection_cid:
        if can_change(request, image.collection) and mode != "api":
            raise HttpRedirectException(image.get_absolute_url())
        raise PermissionDenied()
    return image
