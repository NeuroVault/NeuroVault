from django.conf.urls import patterns, url
from django.contrib import admin
from .views import index_view
from django.views.generic.base import TemplateView
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', index_view,
        name="index"),
    url(r'^FAQ', TemplateView.as_view(template_name="FAQ.html.haml"), 
        name="FAQ"),
    url(r'^api-docs', TemplateView.as_view(template_name="api-docs.html.haml"), 
        name="api-docs"),
)