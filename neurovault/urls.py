from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^studies/', include('statmaps.urls', namespace="statmaps")),
    url(r'^admin/', include(admin.site.urls)),
)