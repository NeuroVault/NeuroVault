from django.urls import include, path, re_path
from django.conf import settings
from django.contrib import admin
from .views import (
    view_profile,
    edit_user,
    create_user,
    password_change_done,
    delete_profile,
    view_token
)
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views

admin.autodiscover()

app_name = "users"

""" old manual way
    re_path(r'^profile/password/$',
                    auth_views.password_change,
                    name='password_change'),
    re_path(r'^password/change/done/$',
                    password_change_done,
                    name='password_change_done'),
    re_path(r'^password/reset/$',
                    auth_views.password_reset,
                    name='password_reset'),
    re_path(r'^password/reset/done/$',
                    auth_views.password_reset_done,
                    name='password_reset_done'),
    re_path(r'^password/reset/complete/$',
                    auth_views.password_reset_complete,
                    name='password_reset_complete'),
    re_path(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                    auth_views.password_reset_confirm,
                    name='password_reset_confirm'),
"""

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    re_path(
        r"^login/$",
        LoginView.as_view(
            template_name="users/login.html",
            extra_context={
                "plus_id": getattr(settings, "SOCIAL_AUTH_GOOGLE_PLUS_KEY", None),
                "plus_scope": "profile email",
            },
        ),
        name="login",
    ),
    re_path(
        r"^logout/$",
        LogoutView.as_view(template_name="registration/logout.html", next_page="/"),
        name="logout",
    ),
    re_path(r"^create/$", create_user, name="create_user"),
    re_path(r"^profile/edit$", edit_user, name="edit_user"),
    re_path(r"^profile/delete$", delete_profile, name="delete_profile"),
    re_path(r"^profile/.*$", view_profile, name="my_profile"),
    re_path(r"^token/$", view_token, {'regenerate': False}, name="token_list"),
    re_path(r"^token/new$", view_token, {'regenerate': True}, name="token_create"),
    re_path(r"^(?P<username>[A-Za-z0-9@/./+/-/_]+)/$", view_profile, name="profile"),
]


# if settings.DEBUG:
#     # static files (images, css, javascript, etc.)
#     urlpatterns += patterns('',
#         (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
#         'document_root': settings.MEDIA_ROOT}))
