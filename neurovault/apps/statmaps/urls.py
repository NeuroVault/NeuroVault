from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, TemplateView
from django.views.generic.base import RedirectView

from neurovault import settings
from neurovault.apps.statmaps.models import KeyValueTag
from neurovault.apps.statmaps.views import ImagesInCollectionJson,\
    PublicCollectionsJson, MyCollectionsJson, AtlasesAndParcellationsJson, \
    ImagesByTaskJson, GroupImagesInCollectionJson, SingleSubjectImagesInCollectionJson, \
    OtherImagesInCollectionJson, AllDOIPublicGroupImages, MyMetaanalysesJson
from .views import edit_collection, view_image, delete_image, edit_image, \
                view_collection, delete_collection, download_collection, upload_folder, add_image_for_neurosynth, \
                serve_image, serve_pycortex, view_collection_with_pycortex, add_image, \
                papaya_js_embed, view_images_by_tag, add_image_for_neuropower, \
                view_image_with_pycortex, stats_view, serve_nidm, serve_nidm_image, \
                view_nidm_results, find_similar, find_similar_json, compare_images, edit_metadata, \
                export_images_filenames, delete_nidm_results, view_task, search, gene_expression_json, \
                gene_expression, serve_surface_archive, edit_metaanalysis


urlpatterns = patterns('',
    url(r'^metaanalysis_selection/$',
       TemplateView.as_view(
           template_name='statmaps/metaanalysis_selection.html.haml'),
       name='metaanalysis_selection'),
    url(r'^my_metaanalyses/$',
        login_required(TemplateView.as_view(
           template_name='statmaps/my_metaanalyses.html.haml')),
        name='my_metaanalyses'),
    url(r'^my_metaanalyses/new$',
        edit_metaanalysis,
       name='new_metaanalysis'),
    url(r'^metaanalyses/(?P<cid>\d+)/edit$',
        edit_metaanalysis,
       name='edit_metaanalysis'),
    url(r'^my_metaanalyses/json$',
        login_required(MyMetaanalysesJson.as_view()),
        name='my_metaanalyses_json'),
    url(r'^metaanalysis_selection/json$',
        AllDOIPublicGroupImages.as_view(),
       name='metaanalysis_selection_json'),
    url(r'^my_collections/$',
        login_required(TemplateView.as_view(template_name='statmaps/my_collections.html.haml')),
        name='my_collections'),
    url(r'^my_collections/json$',
        login_required(MyCollectionsJson.as_view()),
        name='my_collections_json'),
    url(r'^collections/$',
        TemplateView.as_view(template_name='statmaps/collections_index.html.haml'),
        name='collections_list'),
    url(r'^collections/json$',
        PublicCollectionsJson.as_view(),
        name='collections_list_json'),
    url(r'^collections/stats$',
        stats_view,
        name='collections_stats'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/$',
        view_collection,
        name='collection_details'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/json$',
        ImagesInCollectionJson.as_view(),
        name='collection_images_json'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/gjson$',
        GroupImagesInCollectionJson.as_view(),
        name='collection_gimages_json'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/sjson$',
        SingleSubjectImagesInCollectionJson.as_view(),
        name='collection_simages_json'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/ojson$',
        OtherImagesInCollectionJson.as_view(),
        name='collection_oimages_json'),
    url(r'^collections/new$',
        edit_collection,
        name='new_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/edit$',
        edit_collection,
        name='edit_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/delete$',
        delete_collection,
        name='delete_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/download$',
       download_collection,
       name='download_collection'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/addimage',
        add_image,
        name="add_image"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/upload_folder$',
        upload_folder,
        name="upload_folder"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/$',
        view_image,
        name="private_image_details"),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/pycortex$',
        view_collection_with_pycortex,
        name='view_collection_pycortex'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/export/imagesfilenames$',
        export_images_filenames,
        name="export_images_filenames"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/editmetadata$',
        edit_metadata,
        name="edit_metadata"),
    url(r'^atlases/$', TemplateView.as_view(template_name="statmaps/atlases.html"),
        name="atlases_and_parcellations"),
    url(r'^atlases2/$', TemplateView.as_view(template_name="statmaps/atlases2.html"),
        name="atlases_and_parcellations2"),
    url(r'^atlases/json$',
        AtlasesAndParcellationsJson.as_view(),
        name='atlases_and_parcellations_json'),
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
    url(r'^images/add_for_neuropower$',
        add_image_for_neuropower,
        name='add_for_neuropower'),
    url(r'^images/(?P<pk>\d+)/js/embed$',
        papaya_js_embed,
        name='papaya_js_embed'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidm_name>[A-Za-z0-9\.\+\-\_\s\[\]\(\)]+\.nidm\_?[0-9]*)/?$',
        view_nidm_results,
        name='view_nidm_results'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidm_name>[A-Za-z0-9\.\+\-\_\s\[\]\(\)]+\.nidm\_?[0-9]*)/delete$',
        delete_nidm_results,
        name='delete_nidm_results'),

    url(r'^images/(?P<pk>\d+)/papaya/embedview$',
        papaya_js_embed,
        {'iframe':True},name='papaya_iframe_embed'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<img_name>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+)$',
        serve_image,
        name='serve_image'),

    url(r'^images/(?P<pk>\d+)/download_surfaces$',
        serve_surface_archive,
        name='serve_surface_archive'),

    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/download_surfaces$',
        serve_surface_archive,
        name='serve_surface_archive'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidmdir>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+\.nidm\_?[0-9]*)(?P<sep>\.|/)(?P<path>.*)$',
        serve_nidm_image,
        name='serve_nidm_images'),

    # redirect dynamically loaded pycortex scripts
    url(r'^media/images/(\d+|[A-Z]{8})/(.*_pycortex|pycortex_all)/resources/(?P<path>.*).js$',
        RedirectView.as_view(url='{0}pycortex-resources/%(path)s.js'.format(settings.STATIC_URL)),
        name='redirect_pycortex_js'),

    # redirect cached ctm assets
    url(r'^media/images/(\d+|[A-Z]{8})/(.*_pycortex|pycortex_all)/(?P<ctmfile>fsaverage.*).(?P<ext>json|svg|ctm)$',
        RedirectView.as_view(url='{0}pycortex-ctmcache/%(ctmfile)s.%(ext)s'.format(settings.STATIC_URL)),
        name='redirect_pycortex_ctm'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<pycortex_dir>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+\_pycortex/)(?P<path>.*)$',
        serve_pycortex,
        name='serve_pycortex'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/pycortex_all/(?P<path>.*)$',
        serve_pycortex,
        name='serve_pycortex_collection'),

    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/(?P<nidmdir>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+\.nidm\_?[0-9]*)(?P<sep>\.|/)(?P<path>.*)$',
        serve_nidm,
        name='serve_nidm_files'),

    # Compare images and search
    url(r'^images/compare/(?P<pk1>\d+)/(?P<pk2>\d+)$',
        compare_images,
        name='compare_images'),
    url(r'^images/(?P<pk>\d+)/find_similar$',
        find_similar,
        name='find_similar'),
    url(r'^images/(?P<pk>\d+)/find_similar/json/$',
        find_similar_json,
        name='find_similar_json'),

    url(r'^images/(?P<pk>\d+)/gene_expression$',
        gene_expression,
        name='gene_expression'),
    url(r'^images/(?P<pk>\d+)/gene_expression/json$',
        gene_expression_json,
        name='gene_expression_json'),
    url(r'^search$',
        search,
        name='search'),


    # Cognitive Atlas
    url(r'^tasks/(?P<cog_atlas_id>[A-Za-z0-9].*)/json$',
        ImagesByTaskJson.as_view(),
        name='task_images_json'),
    url(r'^tasks/(?P<cog_atlas_id>[A-Za-z0-9].*)$',
        view_task,
        name='view_task'),
    url(r'^tasks$',
        view_task,
        name='view_task')

)
