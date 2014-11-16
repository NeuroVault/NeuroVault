# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0018_inference_maskmap'),
    ]

    operations = [
        migrations.AddField(
            model_name='cluster',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contrastestimation',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contrastweights',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='coordinate',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='coordinatespace',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='data',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='designmatrix',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='excursionset',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='extentthreshold',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='heightthreshold',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='inference',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='map',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='modelparametersestimation',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='noisemodel',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='peak',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='provimage',
            name='collection',
            field=models.ForeignKey(default=0, to='statmaps.Collection'),
            preserve_default=False,
        ),
    ]
