from django.conf.urls import patterns, include, url
from django.conf import settings

from django.contrib import admin
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView
from .views import view_profile
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^studies/', include('statmaps.urls', namespace="statmaps")),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('social_auth.urls')),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/create/$',
        CreateView.as_view(
            form_class=UserCreationForm,
            template_name='registration/create_user.html'),
        name='create_user'),
    url(r'^users/(?P<username>[a-z]+)/$',
        view_profile,
        name="profile"
        ),                  
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))