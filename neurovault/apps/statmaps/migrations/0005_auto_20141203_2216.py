# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0004_collection_contributors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='contributors',
            field=models.ManyToManyField(related_query_name=b'contributor', related_name=b'collection_contributors', to=settings.AUTH_USER_MODEL, blank=True, help_text=b'Select other NeuroVault users to add as contributes to the collection.  Contributors can add, edit and delete images in the collection.', verbose_name=b'Contributors'),
        ),
    ]
