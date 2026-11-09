from django.http import HttpResponseRedirect
from neurovault.adapters.http import HttpRedirectException


class CollectionRedirectMiddleware:
    def process_exception(self, request, exception):
        if isinstance(exception, HttpRedirectException):
            return HttpResponseRedirect(exception.args[0])


class DomainErrorMiddleware:
    """Turn the use cases' PermissionDenied and NotFound into 403 and 404."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        from django.http import Http404, HttpResponseForbidden

        from neurovault.core.domain.errors import NotFound, PermissionDenied

        if isinstance(exception, PermissionDenied):
            return HttpResponseForbidden()
        if isinstance(exception, NotFound):
            raise Http404(str(exception))
        return None
