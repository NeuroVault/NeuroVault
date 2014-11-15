# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0015_fixed_typo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clusterlabelmap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='clusterlabelmap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='contrastmap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='contrastmap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='contraststandarderrormap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='contraststandarderrormap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='excursionset',
            name='file',
        ),
        migrations.RemoveField(
            model_name='maskmap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='maskmap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='parameterestimatemap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='parameterestimatemap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='reselspervoxelmap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='reselspervoxelmap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='residualmeansquaresmap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='residualmeansquaresmap',
            name='id',
        ),
        migrations.RemoveField(
            model_name='searchspacemap',
            name='file',
        ),
        migrations.RemoveField(
            model_name='searchspacemap',
            name='id',
        ),
        migrations.AddField(
            model_name='clusterlabelmap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contrastmap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contraststandarderrormap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='maskmap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='parameterestimatemap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reselspervoxelmap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='residualmeansquaresmap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='searchspacemap',
            name='image_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, default=0, serialize=False, to='statmaps.Image'),
            preserve_default=False,
        ),
    ]
