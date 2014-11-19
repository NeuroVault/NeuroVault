# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0013_add_blanks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='statisticmap',
            name='modelParametersEstimation',
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='contrastEstimation',
            field=models.ForeignKey(blank=True, to='statmaps.ContrastEstimation', null=True),
            preserve_default=True,
        ),
    ]
