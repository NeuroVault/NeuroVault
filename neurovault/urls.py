from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', include('neurovault.apps.main.urls', namespace="main", app_name="main")),
    url(r'^studies/', include('neurovault.apps.statmaps.urls', namespace="statmaps", app_name="statmaps")),
    url(r'^accounts/', include('neurovault.apps.users.urls', namespace="users", app_name="users")),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))