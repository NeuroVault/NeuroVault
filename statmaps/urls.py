from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from .models import Study, StatMap
from .views import edit_study

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
    url(r'^statmap/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=StatMap,
            template_name='statmaps/statmap_details.html'),
        name='statmap_details'),
    url(r'^new$',
        edit_study,
        name='new_study'),
    url(r'^(?P<study_id>\d+)/edit$',
        edit_study,
        name='edit_study'),                   
    url(r'^(?P<study_id>\d+)/editstatmaps$', 
        "statmaps.views.edit_statmaps", 
        name="edit_statmaps"),
)