# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0002_auto_20141001_2036'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='journal_name',
            field=models.CharField(default=None, max_length=200, null=True, blank=True),
            preserve_default=True,
        ),
    ]
