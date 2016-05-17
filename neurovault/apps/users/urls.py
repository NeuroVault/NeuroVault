from django.conf.urls import patterns, url
from django.conf import settings
from django.contrib import admin
from .views import (view_profile, edit_user, create_user,
                    password_change_done, delete_profile)
from django.contrib.auth.views import login
from django.contrib.auth import views as auth_views
from oauth2_provider.views.application import ApplicationList
from .views import (ApplicationRegistration, ApplicationUpdate,
                    ApplicationDelete, ConnectionList,
                    ConnectionDelete, PersonalTokenList,
                    PersonalTokenCreate, PersonalTokenDelete)

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^login/$', login,
        {'extra_context': {'plus_id': getattr(settings, 'SOCIAL_AUTH_GOOGLE_PLUS_KEY', None),
                           'plus_scope': 'profile email'}},
        name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout',
        {'template_name': 'registration/logout.html', 'next_page': '/'}, name="logout"),
    url(r'^create/$',
        create_user,
        name="create_user"),
    url(r'^profile/password/$',
                    auth_views.password_change,
                    name='password_change'),
    url(r'^password/change/done/$',
                    password_change_done,
                    name='password_change_done'),
    url(r'^password/reset/$',
                    auth_views.password_reset,
                    name='password_reset'),
    url(r'^password/reset/done/$',
                    auth_views.password_reset_done,
                    name='password_reset_done'),
    url(r'^password/reset/complete/$',
                    auth_views.password_reset_complete,
                    name='password_reset_complete'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                    auth_views.password_reset_confirm,
                    name='password_reset_confirm'),
    url(r'^profile/edit$',
        edit_user,
        name="edit_user"
        ),
    url(r'^profile/delete$',
        delete_profile,
        name="delete_profile"
        ),
    url(r'^profile/.*$',
        view_profile,
        name="my_profile"
        ),

    url(r'^tokens/$', PersonalTokenList.as_view(),
        name="token_list"),
    url(r'^tokens/new$', PersonalTokenCreate.as_view(),
        name="token_create"),
    url(r'^tokens/(?P<pk>\d+)/delete/$', PersonalTokenDelete.as_view(),
        name="token_delete"),

    url(r'^connections/$', ConnectionList.as_view(),
        name="connection_list"),
    url(r'^connections/(?P<pk>\d+)/revoke/$', ConnectionDelete.as_view(),
        name="connection_revoke"),

    url(r'^applications/$', ApplicationList.as_view(),
        name="developerapps_list"),
    url(r'^applications/register/$', ApplicationRegistration.as_view(),
        name="developerapps_register"),
    url(r'^applications/(?P<pk>\d+)/$', ApplicationUpdate.as_view(),
        name="developerapps_update"),
    url(r'^applications/(?P<pk>\d+)/delete/$', ApplicationDelete.as_view(),
        name="developerapps_delete"),

    url(r'^(?P<username>[A-Za-z0-9@/./+/-/_]+)/$',
        view_profile,
        name="profile"
        ),
)


# if settings.DEBUG:
#     # static files (images, css, javascript, etc.)
#     urlpatterns += patterns('',
#         (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
#         'document_root': settings.MEDIA_ROOT}))
