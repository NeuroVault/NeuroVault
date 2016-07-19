# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from neurovault.apps.statmaps.tasks import save_resampled_transformation_single
import os


def change_resample_dim(apps, schema_editor):
    Image = apps.get_model("statmaps", "Image")
    count = Image.objects.count()
    for i, image in enumerate(Image.objects.all()):
        print "Fixing image %d (%d/%d)"%(image.pk, i+1, count)

        try:
            os.path.exists(str(image.reduced_representation.file))
            image.reduced_representation = save_resampled_transformation_single(image.pk,  resample_dim=[16, 16, 16])
            os.remove(str(image.reduced_representation.file))
        except ValueError:
            print "This image needs no resampling due to not previous resampled transformation"



class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0070_auto_20160526_2216'),
    ]

    operations = [
        migrations.RunPython(change_resample_dim),
    ]
