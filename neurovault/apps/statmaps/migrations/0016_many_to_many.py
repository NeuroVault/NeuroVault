# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0015_fixed_typo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contrastestimation',
            name='parameterEstimateMap',
        ),
        migrations.AddField(
            model_name='contrastestimation',
            name='parameterEstimateMap',
            field=models.ManyToManyField(to='statmaps.ParameterEstimateMap', null=True, blank=True),
        ),
    ]
