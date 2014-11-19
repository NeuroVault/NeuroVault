# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0011_migrate_to_nidm2'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticmap',
            name='atCoordinateSpace',
            field=models.ForeignKey(related_name='+', to='statmaps.CoordinateSpace', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='map',
            field=models.OneToOneField(null=True, to='statmaps.Map'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='modelParametersEstimation',
            field=models.ForeignKey(to='statmaps.ModelParametersEstimation', null=True),
            preserve_default=True,
        ),
    ]
