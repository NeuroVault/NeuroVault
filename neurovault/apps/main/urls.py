from django.conf.urls import patterns, url
from django.contrib import admin
from .views import index_view
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', index_view,
        name="index"),
)