# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0024_auto_20150219_2047'),
    ]

    operations = [
        migrations.CreateModel(
            name='CognitiveAtlasContrast',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('cog_atlas_id', models.CharField(max_length=200)),
                ('task', models.ForeignKey(to='statmaps.CognitiveAtlasTask')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
