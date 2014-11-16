# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0020_auto_20141116_0350'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticmap',
            name='contrastName',
            field=models.CharField(max_length=200, null=True, blank=True),
            preserve_default=True,
        ),
    ]
