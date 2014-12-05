# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0009_add_contenttype'),
    ]

    operations = [
        migrations.CreateModel(
            name='Atlas',
            fields=[
                ('image_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='statmaps.Image')),
                ('label_description_file', models.FileField(upload_to=neurovault.apps.statmaps.models.upload_to, storage=neurovault.apps.statmaps.storage.NiftiGzStorage(), verbose_name=b'FSL compatible label description file (.xml)')),
            ],
            options={
                'abstract': False,
            },
            bases=('statmaps.image',),
        ),
    ]
