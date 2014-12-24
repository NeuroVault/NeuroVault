# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import neurovault.apps.statmaps.models
import taggit.managers
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0014_auto_20141219_1116'),
    ]

    operations = [
        migrations.CreateModel(
            name='NIDMResults',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('add_date', models.DateTimeField(auto_now_add=True, verbose_name=b'date published')),
                ('modify_date', models.DateTimeField(auto_now=True, verbose_name=b'date modified')),
                ('ttl_file', models.FileField(storage=neurovault.apps.statmaps.storage.NIDMStorage(), upload_to=neurovault.apps.statmaps.models.upload_nidm_to, null=True, verbose_name=b'Turtle serialization of NIDM Results (.ttl)', blank=True)),
                ('provn_file', models.FileField(upload_to=neurovault.apps.statmaps.models.upload_nidm_to, storage=neurovault.apps.statmaps.storage.NIDMStorage(), verbose_name=b'Provenance store serialization of NIDM Results (.provn)', blank=True)),
                ('zip_file', models.FileField(upload_to=neurovault.apps.statmaps.models.upload_nidm_to, storage=neurovault.apps.statmaps.storage.NIDMStorage(), verbose_name=b'NIDM Results zip file')),
                ('collection', models.ForeignKey(to='statmaps.Collection')),
                ('tags', taggit.managers.TaggableManager(to='statmaps.KeyValueTag', through='statmaps.ValueTaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
            options={
                'verbose_name_plural': 'NIDMResults',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NIDMResultStatisticMap',
            fields=[
                ('image_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='statmaps.Image')),
                ('map_type', models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'Other', b'Other')])),
                ('nidm_results', models.ForeignKey(to='statmaps.NIDMResults')),
            ],
            options={
                'abstract': False,
            },
            bases=('statmaps.image',),
        ),
        migrations.AlterUniqueTogether(
            name='nidmresults',
            unique_together=set([('collection', 'name')]),
        ),
        migrations.AlterModelOptions(
            name='atlas',
            options={'verbose_name_plural': 'Atlases'},
        ),
        migrations.AlterUniqueTogether(
            name='image',
            unique_together=set([]),
        ),
    ]
