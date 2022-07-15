from django.urls import re_path
from django.contrib import admin
from .views import index_view, community_view
from django.views.generic.base import TemplateView
admin.autodiscover()

app_name = "main"

urlpatterns = [
    re_path(r'^$', index_view,
        name="index"),
    re_path(r'^cite', TemplateView.as_view(template_name="cite.html"),
        name="cite"),
    re_path(r'^FAQ', TemplateView.as_view(template_name="FAQ.html"),
        name="FAQ"),
    re_path(r'^api-docs', TemplateView.as_view(template_name="api-docs.html"), 
        name="api-docs"),
   re_path(r'^communities/(?P<community_label>[a-z]+)/$',
       community_view,
       name='view_community')
]
