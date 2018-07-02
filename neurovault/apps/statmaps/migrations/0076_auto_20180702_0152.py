# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0075_auto_20180416_0413'),
    ]

    operations = [
        migrations.CreateModel(
            name='Community',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(unique=True, max_length=200, verbose_name=b'Lexical label of the community')),
                ('short_desc', models.CharField(max_length=200, verbose_name=b'Short description of the community')),
            ],
        ),
        migrations.AddField(
            model_name='collection',
            name='communities',
            field=models.ManyToManyField(related_query_name=b'community', related_name='collection_communities', default=None, to='statmaps.Community', blank=True, help_text=b'Is this collection part of any special Communities?', verbose_name=b'Communities'),
        ),
    ]
