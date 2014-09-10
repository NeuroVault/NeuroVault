from django.http import HttpResponseRedirect
from neurovault.apps.statmaps.utils import HttpRedirectException

class CollectionRedirectMiddleware:
    def process_exception(self, request, exception):
        if isinstance(exception, HttpRedirectException):
            return HttpResponseRedirect(exception.args[0])
