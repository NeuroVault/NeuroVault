from rest_framework.pagination import LimitOffsetPagination


# Pagination Custom Function to modify LimitedResultPagination
class StandardResultPagination(LimitOffsetPagination):
    PAGE_SIZE = 100  # this also sets default_limit to same value
    max_limit = 1000  # we need to set this, default is None
    default_limit = 100
