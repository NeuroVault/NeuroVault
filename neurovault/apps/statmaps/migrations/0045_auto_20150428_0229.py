# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0044_auto_20150423_2134'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nidmresultstatisticmap',
            name='transform',
        ),
        migrations.RemoveField(
            model_name='statisticmap',
            name='transform',
        ),
        migrations.AddField(
            model_name='image',
            name='reduced_representation',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.DoubleExtensionStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, blank=True, help_text=b'Binary file with the vector of in brain values resampled to lower resolution', null=True, verbose_name=b'Reduced representation of the image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='image',
            name='thumbnail',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.DoubleExtensionStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, blank=True, help_text=b'The orthogonal view thumbnail path of the nifti image', null=True, verbose_name=b'Image orthogonal view thumbnail 2D bitmap'),
            preserve_default=True,
        ),
    ]
