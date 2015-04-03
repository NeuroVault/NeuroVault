# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_hstore.fields


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0037_auto_20150307_0222'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='data',
            field=django_hstore.fields.DictionaryField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
