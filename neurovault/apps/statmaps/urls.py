from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from .models import Collection
from .views import edit_collection, edit_images, view_image, delete_image, edit_image, \
                    view_collection, delete_collection, upload_folder, add_image_for_neurosynth, \
                    serve_image, serve_pycortex
from neurovault.apps.statmaps.views import view_images_by_tag,\
    view_image_with_pycortex
from neurovault.apps.statmaps.models import KeyValueTag
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from neurovault import settings


class MyCollectionsListView(ListView):
    template_name='statmaps/my_collections.html.haml'
    context_object_name = 'collections'

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user).annotate(n_images=Count('image'))

urlpatterns = patterns('',
    url(r'^my_collections/$',
        login_required(MyCollectionsListView.as_view()),
        name='my_collections'),
    url(r'^collections/$',
        ListView.as_view(
            queryset=Collection.objects.filter(private=False).annotate(n_images=Count('image')),
            context_object_name='collections',
            template_name='statmaps/collections_index.html.haml'),
        name='collections_list'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/$',
        view_collection,
        name='collection_details'),
    url(r'^collections/new$',
        edit_collection,
        name='new_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/edit$',
        edit_collection,
        name='edit_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/delete$',
        delete_collection,
        name='delete_collection'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/editimages$',
        edit_images,
        name="edit_images"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/upload_folder$',
        upload_folder,
        name="upload_folder"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/$',
        view_image,
        name="private_image_details"),

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
    url(r'^images/(?P<pk>\d+)/pycortex$',
        view_image_with_pycortex,
        name='pycortex_view_image'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/pycortex$',
        view_image_with_pycortex,
        name="private_pycortex_view_image"),
    url(r'^images/(?P<pk>\d+)/edit$',
        edit_image,
        name='edit_image'),
    url(r'^images/(?P<pk>\d+)/delete$',
        delete_image,
        name='delete_image'),
    url(r'^images/add_for_neurosynth$',
        add_image_for_neurosynth,
        name='add_for_neurosynth'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<img_name>[A-Za-z0-9\.\+\-\_\s]+)$',
        serve_image,
        name='serve_image'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<pycortex_dir>[A-Za-z0-9\.\+\-\_\s]+\_pycortex/)(?P<path>.*)$',
        serve_pycortex,
        name='serve_pycortex'),

)
