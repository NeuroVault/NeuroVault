import os
from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap, index
from oauth2_provider import views as oauth_views

from neurovault.api.sitemap import CollectionSitemap, ImageSitemap, CognitiveAtlasTaskSitemap
from neurovault.api.urls import api_urls

admin.autodiscover()

sitemaps = {"Collections":CollectionSitemap,
            "Images":ImageSitemap,
            "CognitiveAtlasTasks":CognitiveAtlasTaskSitemap}

oauth_urlpatterns = [
    re_eath(r'^authorize/$', oauth_views.AuthorizationView.as_view(),
        name="authorize"),
    re_path(r'^token/$', oauth_views.TokenView.as_view(),
        name="token"),
    re_path(r'^revoke_token/$', oauth_views.RevokeTokenView.as_view(),
        name="revoke-token"),
]

urlpatterns = [
    re_path('', include('social_django.urls', namespace='social')),
    re_path(r'^', include('neurovault.apps.main.urls')),
    re_path(r'^', include('neurovault.apps.statmaps.urls')),
    re_path(r'^accounts/', include('neurovault.apps.users.urls')),
    re_path(r'^admin/', include(admin.site.urls)),
    re_path(r'^api/', include(api_urls)),
    re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^sitemap\.xml$', index, {'sitemaps': sitemaps}),
    re_path(r'^sitemap-(?P<section>.+)\.xml$', sitemap, {'sitemaps': sitemaps}),
    re_path(r'^o/', include((oauth_urlpatterns, 'oauth2_provider', 'oauth2_provider'))),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^(?P<path>favicon\.ico)$', 'django.views.static.serve', {
            'document_root': os.path.join(settings.STATIC_ROOT, 'images')}),
    ]
