from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from .models import Study
from .views import edit_study, edit_statmaps, view_statmap
from neurovault.apps.statmaps.views import view_statmaps_by_tag

urlpatterns = patterns('',
    url(r'^$',
        ListView.as_view(
            queryset=Study.objects.all(),
            context_object_name='all_studies_list',
            template_name='statmaps/studies_index.html'),
        name='studies_list'),
    url(r'^(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Study,
            template_name='statmaps/study_details.html'),
        name='study_details'),
    url(r'^statmap/tag/(?P<tag>[A-Za-z0-9@/./+/-/_]+)/$',
        view_statmaps_by_tag,
        name='statmaps_by_tag'),
    url(r'^statmap/(?P<pk>\d+)/$',
        view_statmap,
        name='statmap_details'),
    url(r'^new$',
        edit_study,
        name='new_study'),
    url(r'^(?P<study_id>\d+)/edit$',
        edit_study,
        name='edit_study'),                   
    url(r'^(?P<study_id>\d+)/editstatmaps$', 
        edit_statmaps, 
        name="edit_statmaps"),
)