# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0017_all_maps_are_images'),
    ]

    operations = [
        migrations.AddField(
            model_name='inference',
            name='maskMap',
            field=models.ForeignKey(blank=True, to='statmaps.MaskMap', null=True),
            preserve_default=True,
        ),
    ]
