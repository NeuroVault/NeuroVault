# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0009_add_contenttype'),
    ]

    operations = [
        migrations.RenameField(
            model_name='statisticmap',
            old_name='map_type',
            new_name='statisticType',
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='effectDegreesOfFreedom',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='errorDegreesOfFreedom',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='sha512',
            field=models.CharField(max_length=200, null=True),
            preserve_default=True,
        ),
    ]
