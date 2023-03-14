import os
from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap, index

from neurovault.api.sitemap import (
    CollectionSitemap,
    ImageSitemap,
    CognitiveAtlasTaskSitemap,
)

admin.autodiscover()

sitemaps = {
    "Collections": CollectionSitemap,
    "Images": ImageSitemap,
    "CognitiveAtlasTasks": CognitiveAtlasTaskSitemap,
}

""" Do these need to live outside o/* oauth urls included below?
oauth_urlpatterns = [
    re_path(r'^authorize/$', oauth_view.AuthorizationView.as_view(),
        name="authorize"),
    re_path(r'^token/$', oauth_view.TokenView.as_view(),
        name="token"),
    re_path(r'^revoke_token/$', oauth_view.RevokeTokenView.as_view(),
        name="revoke-token"),
]
"""

urlpatterns = [
    re_path("", include("social_django.urls", namespace="social")),
    re_path(r"^", include("neurovault.apps.main.urls")),
    re_path(r"^", include("neurovault.apps.statmaps.urls", namespace="statmaps")),
    re_path(r"^accounts/", include("neurovault.apps.users.urls", namespace="users")),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^api/", include("neurovault.api.urls", namespace="api")),
    re_path(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    re_path(r"^sitemap\.xml$", index, {"sitemaps": sitemaps}),
    re_path(r"^sitemap-(?P<section>.+)\.xml$", sitemap, {"sitemaps": sitemaps}),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]
