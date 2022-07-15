from django.urls import re_path
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, TemplateView
from django.views.generic.base import RedirectView

from neurovault import settings
from neurovault.apps.statmaps.models import KeyValueTag
from neurovault.apps.statmaps.views import ImagesInCollectionJson, \
    PublicCollectionsJson, MyCollectionsJson, AtlasesAndParcellationsJson, \
    ImagesByTaskJson, GroupImagesInCollectionJson, SingleSubjectImagesInCollectionJson, \
    OtherImagesInCollectionJson, AllDOIPublicGroupImages, MyMetaanalysesJson, \
    toggle_active_metaanalysis
from .views import edit_collection, view_image, delete_image, edit_image, \
                view_collection, delete_collection, download_collection, upload_folder, add_image_for_neurosynth, \
                serve_image, serve_pycortex, view_collection_with_pycortex, add_image, \
                papaya_js_embed, view_images_by_tag, add_image_for_neuropower, \
                view_image_with_pycortex, stats_view, serve_nidm, serve_nidm_image, \
                view_nidm_results, find_similar, find_similar_json, compare_images, edit_metadata, \
                export_images_filenames, delete_nidm_results, view_task, search, gene_expression_json, \
                gene_expression, serve_surface_archive, edit_metaanalysis, view_metaanalysis, \
                activate_metaanalysis, finalize_metaanalysis

app_name = 'statmaps'

urlpatterns = [
    re_path(r'^metaanalysis_selection/$',
       TemplateView.as_view(
           template_name='statmaps/metaanalysis_selection.html'),
       name='metaanalysis_selection'),
    re_path(r'^my_metaanalyses/$',
        login_required(TemplateView.as_view(
           template_name='statmaps/my_metaanalyses.html')),
        name='my_metaanalyses'),
    re_path(r'^my_metaanalyses/new$',
        edit_metaanalysis,
       name='new_metaanalysis'),
    re_path(r'^metaanalyses/(?P<metaanalysis_id>\d+)/edit$',
        edit_metaanalysis,
       name='edit_metaanalysis'),
    re_path(r'^metaanalyses/(?P<metaanalysis_id>\d+)/activate$',
        activate_metaanalysis,
       name='activate_metaanalysis'),
    re_path(r'^metaanalyses/(?P<metaanalysis_id>\d+)/finalize$',
        finalize_metaanalysis,
       name='finalize_metaanalysis'),
    re_path(r'^metaanalyses/(?P<metaanalysis_id>\d+)$',
       view_metaanalysis,
       name='view_metaanalysis'),
    re_path(r'^metaanalyses/(?P<metaanalysis_id>\d+)/images_json',
        AllDOIPublicGroupImages.as_view(),
       name='metaanalysis_images_json'),
    re_path(r'^my_metaanalyses/json$',
        login_required(MyMetaanalysesJson.as_view()),
        name='my_metaanalyses_json'),
    re_path(r'^metaanalysis_selection/json$',
        AllDOIPublicGroupImages.as_view(),
       name='metaanalysis_selection_json'),
    re_path(r'^my_collections/$',
        login_required(TemplateView.as_view(template_name='statmaps/my_collections.html')),
        name='my_collections'),
    re_path(r'^my_collections/json$',
        login_required(MyCollectionsJson.as_view()),
        name='my_collections_json'),
    re_path(r'^collections/$',
        TemplateView.as_view(template_name='statmaps/collections_index.html'),
        name='collections_list'),
    re_path(r'^collections/json$',
        PublicCollectionsJson.as_view(),
        name='collections_list_json'),
    re_path(r'^collections/stats$',
        stats_view,
        name='collections_stats'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/$',
        view_collection,
        name='collection_details'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/json$',
        ImagesInCollectionJson.as_view(),
        name='collection_images_json'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/gjson$',
        GroupImagesInCollectionJson.as_view(),
        name='collection_gimages_json'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/sjson$',
        SingleSubjectImagesInCollectionJson.as_view(),
        name='collection_simages_json'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/ojson$',
        OtherImagesInCollectionJson.as_view(),
        name='collection_oimages_json'),
    re_path(r'^collections/new$',
        edit_collection,
        name='new_collection'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/edit$',
        edit_collection,
        name='edit_collection'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/delete$',
        delete_collection,
        name='delete_collection'),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/download$',
       download_collection,
       name='download_collection'),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/addimage',
        add_image,
        name="add_image"),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/upload_folder$',
        upload_folder,
        name="upload_folder"),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/$',
        view_image,
        name="private_image_details"),
    re_path(r'^collections/(?P<cid>\d+|[A-Z]{8})/pycortex$',
        view_collection_with_pycortex,
        name='view_collection_pycortex'),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/export/imagesfilenames$',
        export_images_filenames,
        name="export_images_filenames"),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/editmetadata$',
        edit_metadata,
        name="edit_metadata"),
    re_path(r'^atlases/$', TemplateView.as_view(template_name="statmaps/atlases.html"),
        name="atlases_and_parcellations"),
    re_path(r'^atlases/json$',
        AtlasesAndParcellationsJson.as_view(),
        name='atlases_and_parcellations_json'),
    re_path(r'^images/tags/$',
        ListView.as_view(
            queryset=KeyValueTag.objects.all(),
            context_object_name='tags',
            template_name='statmaps/tags_index.html'),
        name='tags_list'),
    re_path(r'^images/tags/(?P<tag>[A-Za-z0-9@\.\+\-\_\s]+)/$',
        view_images_by_tag,
        name='images_by_tag'),
    re_path(r'^images/(?P<pk>\d+)/$',
        view_image,
        name='image_details'),
    re_path(r'^images/(?P<pk>\d+)/toggle_active_meta$',
        toggle_active_metaanalysis,
        name='toggle_active_metaanalysis'),
    re_path(
        r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/toggle_active_meta$',
        toggle_active_metaanalysis,
        name="private_toggle_active_metaanalysis"),
    re_path(r'^images/(?P<pk>\d+)/pycortex$',
        view_image_with_pycortex,
        name='pycortex_view_image'),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/pycortex$',
        view_image_with_pycortex,
        name="private_pycortex_view_image"),
    re_path(r'^images/(?P<pk>\d+)/edit$',
        edit_image,
        name='edit_image'),
    re_path(r'^images/(?P<pk>\d+)/delete$',
        delete_image,
        name='delete_image'),
    re_path(r'^images/add_for_neurosynth$',
        add_image_for_neurosynth,
        name='add_for_neurosynth'),
    re_path(r'^images/add_for_neuropower$',
        add_image_for_neuropower,
        name='add_for_neuropower'),
    re_path(r'^images/(?P<pk>\d+)/js/embed$',
        papaya_js_embed,
        name='papaya_js_embed'),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidm_name>[A-Za-z0-9\.\+\-\_\s\[\]\(\)]+\.nidm\_?[0-9]*)/?$',
        view_nidm_results,
        name='view_nidm_results'),
    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidm_name>[A-Za-z0-9\.\+\-\_\s\[\]\(\)]+\.nidm\_?[0-9]*)/delete$',
        delete_nidm_results,
        name='delete_nidm_results'),

    re_path(r'^images/(?P<pk>\d+)/papaya/embedview$',
        papaya_js_embed,
        {'iframe':True},name='papaya_iframe_embed'),

    re_path(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<img_name>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+)$',
        serve_image,
        name='serve_image'),

    re_path(r'^images/(?P<pk>\d+)/download_surfaces$',
        serve_surface_archive,
        name='serve_surface_archive'),

    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/download_surfaces$',
        serve_surface_archive,
        name='serve_surface_archive'),

    re_path(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidmdir>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+\.nidm\_?[0-9]*)(?P<sep>\.|/)(?P<path>.*)$',
        serve_nidm_image,
        name='serve_nidm_images'),

    # redirect dynamically loaded pycortex scripts
    re_path(r'^media/images/(\d+|[A-Z]{8})/(.*_pycortex|pycortex_all)/resources/(?P<path>.*).js$',
        RedirectView.as_view(url='{0}pycortex-resources/%(path)s.js'.format(settings.STATIC_URL)),
        name='redirect_pycortex_js'),

    # redirect cached ctm assets
    re_path(r'^media/images/(\d+|[A-Z]{8})/(.*_pycortex|pycortex_all)/(?P<ctmfile>fsaverage.*).(?P<ext>json|svg|ctm)$',
        RedirectView.as_view(url='{0}pycortex-ctmcache/%(ctmfile)s.%(ext)s'.format(settings.STATIC_URL)),
        name='redirect_pycortex_ctm'),

    re_path(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<pycortex_dir>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+\_pycortex/)(?P<path>.*)$',
        serve_pycortex,
        name='serve_pycortex'),

    re_path(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/pycortex_all/(?P<path>.*)$',
        serve_pycortex,
        name='serve_pycortex_collection'),

    re_path(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidmdir>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+\.nidm\_?[0-9]*)(?P<sep>\.|/)(?P<path>.*)$',
        serve_nidm,
        name='serve_nidm_files'),

    # Compare images and search
    re_path(r'^images/compare/(?P<pk1>\d+)/(?P<pk2>\d+)$',
        compare_images,
        name='compare_images'),
    re_path(r'^images/(?P<pk>\d+)/find_similar$',
        find_similar,
        name='find_similar'),
    re_path(r'^images/(?P<pk>\d+)/find_similar/json/$',
        find_similar_json,
        name='find_similar_json'),

    re_path(r'^images/(?P<pk>\d+)/gene_expression$',
        gene_expression,
        name='gene_expression'),
    re_path(r'^images/(?P<pk>\d+)/gene_expression/json$',
        gene_expression_json,
        name='gene_expression_json'),
    re_path(r'^search$',
        search,
        name='search'),


    # Cognitive Atlas
    re_path(r'^tasks/(?P<cog_atlas_id>[A-Za-z0-9].*)/json$',
        ImagesByTaskJson.as_view(),
        name='task_images_json'),
    re_path(r'^tasks/(?P<cog_atlas_id>[A-Za-z0-9].*)$',
        view_task,
        name='view_task'),
    re_path(r'^tasks$',
        view_task,
        name='view_task')
]

