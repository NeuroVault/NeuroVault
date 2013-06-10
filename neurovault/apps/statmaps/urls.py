from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from .models import Collection
from .views import edit_collection, edit_images, view_image, edit_image, view_collection
from neurovault.apps.statmaps.views import view_images_by_tag
from neurovault.apps.statmaps.models import KeyValueTag
from django.db.models import Count

urlpatterns = patterns('',
    url(r'^collections/$',
        ListView.as_view(
            queryset=Collection.objects.all().annotate(n_images=Count('image')),
            context_object_name='collections',
            template_name='statmaps/collections_index.html.haml'),
        name='collections_list'),
    url(r'^collections/(?P<pk>\d+)/$',
        view_collection,
        name='collection_details'),
    url(r'^collections/new$',
        edit_collection,
        name='new_collection'),
    url(r'^collections/(?P<pk>\d+)/edit$',
        edit_collection,
        name='edit_collection'), 
    url(r'^collections/(?P<collection_pk>\d+)/editimages$', 
        edit_images, 
        name="edit_images"),
                       
    url(r'^images/tags/$',
        ListView.as_view(
            queryset=KeyValueTag.objects.all(),
            context_object_name='tags',
            template_name='statmaps/tags_index.html.haml'),
        name='tags_list'),
    url(r'^images/tags/(?P<tag>[A-Za-z0-9@\.\+\-\_\s]+)/$',
        view_images_by_tag,
        name='images_by_tag'),
    url(r'^images/(?P<pk>\d+)/$',
        view_image,
        name='image_details'),
    url(r'^images/(?P<pk>\d+)/edit$',
        edit_image,
        name='edit_image')
                       
    
)
