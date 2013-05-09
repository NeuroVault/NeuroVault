from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from .views import view_profile, edit_user
admin.autodiscover()

urlpatterns = patterns('',
    url(r'', include('social_auth.urls')),
    url(r'^login/$', 'django.contrib.auth.views.login', 
        {'template_name': 'registration/login.html'}, name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', 
        {'template_name': 'registration/logout.html', 'next_page': '/'}, name="logout"),
    url(r'^create/$',
        edit_user,
        name="create_user"),
    url(r'^profile/.*$',
        view_profile,
        name="my_profile"
        ),    
    url(r'^(?P<username>[A-Za-z0-9@/./+/-/_]+)/edit$',
        edit_user,
        name="edit_user"
        ),
    url(r'^(?P<username>[A-Za-z0-9@/./+/-/_]+)/$',
        view_profile,
        name="profile"
        ),
                  
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))