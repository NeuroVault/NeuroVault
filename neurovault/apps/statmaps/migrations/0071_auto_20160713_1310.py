# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0070_auto_20160526_2216'),
    ]

    operations = [
        migrations.DeleteModel('Similarity'),
        migrations.DeleteModel('Comparison'),
        migrations.AddField(
            model_name='image',
            name='reduced_representation_engine',
            field=models.FileField(
                help_text=("Binary file with the vector of in brain values resampled to lower resolution to be used in the Engine"),
                verbose_name="Reduced representation of the image, 16x16x16",
                null=True, blank=True, upload_to=neurovault.apps.statmaps.models.upload_img_to,
                storage=neurovault.apps.statmaps.storage.OverwriteStorage()),
            preserve_default=True,
        ),
    ]
