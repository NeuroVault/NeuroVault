# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0045_auto_20150428_0229'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='reduced_representation',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.OverwriteStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, blank=True, help_text=b'Binary file with the vector of in brain values resampled to lower resolution', null=True, verbose_name=b'Reduced representation of the image'),
            preserve_default=True,
        ),
    ]
