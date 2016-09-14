# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0043_auto_20150423_2059'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='thumbnail',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.DoubleExtensionStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, blank=True, help_text=b'The orthogonal view thumbnail path of the nifti image', null=True, verbose_name=b'Image orthogonal view thumbnail (.png)'),
            preserve_default=True,
        ),
    ]
