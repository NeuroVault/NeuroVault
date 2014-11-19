# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0021_statisticmap_contrastname'),
    ]

    operations = [
        migrations.AddField(
            model_name='residualmeansquaresmap',
            name='designMatrix',
            field=models.ForeignKey(blank=True, to='statmaps.DesignMatrix', null=True),
            preserve_default=True,
        ),
    ]
