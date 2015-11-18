# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth import get_user_model
from django.conf import settings


def get_or_create_user(user_id, username):
    User = get_user_model()
    try:
        u = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        u = User.objects.create(pk=user_id, username=username)

    return u


def create_default_oauth_app(apps, schema_editor):
    Application = apps.get_model('oauth2_provider', 'Application')

    default_user = get_or_create_user(
        settings.DEFAULT_OAUTH_APP_OWNER_ID,
        settings.DEFAULT_OAUTH_APP_OWNER_USERNAME)

    Application.objects.create(
        pk=settings.DEFAULT_OAUTH_APPLICATION_ID,
        name=settings.DEFAULT_OAUTH_APP_NAME,
        redirect_uris="http://localhost http://example.com",
        user=default_user,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE
    )


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2_provider', '0002_08_updates'),
    ]

    operations = [
        migrations.RunPython(create_default_oauth_app),
    ]
