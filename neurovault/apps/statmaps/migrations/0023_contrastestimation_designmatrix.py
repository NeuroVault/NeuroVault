# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0022_residualmeansquaresmap_designmatrix'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrastestimation',
            name='designMatrix',
            field=models.ForeignKey(blank=True, to='statmaps.DesignMatrix', null=True),
            preserve_default=True,
        ),
    ]
