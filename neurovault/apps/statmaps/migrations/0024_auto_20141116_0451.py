# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0023_contrastestimation_designmatrix'),
    ]

    operations = [
        migrations.AddField(
            model_name='inference',
            name='extentThreshold',
            field=models.ForeignKey(blank=True, to='statmaps.ExtentThreshold', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='inference',
            name='heightThreshold',
            field=models.ForeignKey(blank=True, to='statmaps.HeightThreshold', null=True),
            preserve_default=True,
        ),
    ]
