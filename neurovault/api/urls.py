from rest_framework import routers

from .views import (ImageViewSet, AtlasViewSet, CollectionViewSet,
                    NIDMResultsViewSet)

router = routers.DefaultRouter()
router.register(r'images', ImageViewSet)
router.register(r'atlases', AtlasViewSet)
router.register(r'collections', CollectionViewSet)
router.register(r'nidm_results', NIDMResultsViewSet)
