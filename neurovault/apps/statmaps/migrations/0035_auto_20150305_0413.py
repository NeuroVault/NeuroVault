# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0034_auto_20150305_0406'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='perc_bad_voxels',
            field=models.FloatField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='perc_bad_voxels',
            field=models.FloatField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
