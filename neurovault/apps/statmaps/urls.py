from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from .models import Collection
from .views import edit_collection, edit_statmaps, view_statmap
from neurovault.apps.statmaps.views import view_statmaps_by_tag

urlpatterns = patterns('',
    url(r'^collections/$',
        ListView.as_view(
            queryset=Collection.objects.all(),
            context_object_name='all_studies_list',
            template_name='statmaps/collections_index.html'),
        name='collections_list'),
    url(r'^collections/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Collection,
            template_name='statmaps/collection_details.html'),
        name='collection_details'),
    url(r'^collections/new$',
        edit_collection,
        name='new_collection'),
    url(r'^collections/(?P<pk>\d+)/edit$',
        edit_collection,
        name='edit_collection'), 
    url(r'^statmap/tag/(?P<tag>[A-Za-z0-9@/./+/-/_]+)/$',
        view_statmaps_by_tag,
        name='statmaps_by_tag'),
    url(r'^statmap/(?P<pk>\d+)/$',
        view_statmap,
        name='statmap_details'),
                  
    url(r'^(?P<collection_pk>\d+)/editstatmaps$', 
        edit_statmaps, 
        name="edit_statmaps"),
)