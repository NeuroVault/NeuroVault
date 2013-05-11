from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from .views import view_profile, edit_user
from .forms import BlankPasswordChangeForm
from django.contrib.auth.views import password_change, password_change_done
admin.autodiscover()

urlpatterns = patterns('',
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
    url(r'^[A-Za-z0-9@/./+/-/_]+/password/done$',
        password_change_done,
        name="password_change_done"
        ),        
    url(r'^[A-Za-z0-9@/./+/-/_]+/password/$',
        password_change,
        {'post_change_redirect': "done", "password_change_form":BlankPasswordChangeForm},
        name="password_change"
        ),   
    url(r'^(?P<username>[A-Za-z0-9@/./+/-/_]+)/$',
        view_profile,
        name="profile"
        )        
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))