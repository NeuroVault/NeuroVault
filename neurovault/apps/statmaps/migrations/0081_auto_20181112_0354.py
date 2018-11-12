# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0080_metaanalysis'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metaanalysis',
            name='maps',
            field=models.ManyToManyField(to='statmaps.StatisticMap', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='metaanalysis',
            name='output_maps',
            field=models.ForeignKey(blank=True, to='statmaps.Collection', null=True),
        ),
    ]
