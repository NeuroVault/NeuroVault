from django.urls import re_path
from rest_framework import routers

from .views import (
    AuthUserView,
    ImageViewSet,
    AtlasViewSet,
    CollectionViewSet,
    NIDMResultsViewSet,
    MyCollectionsViewSet,
)

app_name = "api"

router = routers.DefaultRouter()
router.register(r"images", ImageViewSet)
router.register(r"atlases", AtlasViewSet)
router.register(
    r"collections",
    CollectionViewSet,
)
router.register(r"my_collections", MyCollectionsViewSet, "")
router.register(r"nidm_results", NIDMResultsViewSet)

urlpatterns = router.urls + [
    re_path(r"^user/?$", AuthUserView.as_view(), name="api-auth-user")
]
