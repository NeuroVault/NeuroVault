# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def move_statmaps(apps, schema_editor):
    Image = apps.get_model("statmaps", "Image")
    StatisticMap = apps.get_model("statmaps", "StatisticMap")
    for image in Image.objects.all():
        statisticmap = StatisticMap(image_ptr_id=image.pk)
        statisticmap.__dict__.update(image.__dict__)
        statisticmap.save() # save first time
        statisticmap.__dict__.update(image.__dict__)
        statisticmap.tmp_map_type = image.map_type
        statisticmap.tmp_statistic_parameters = image.statistic_parameters
        statisticmap.tmp_smoothness_fwhm = image.smoothness_fwhm
        statisticmap.tmp_contrast_definition = image.contrast_definition
        statisticmap.tmp_contrast_definition_cogatlas = image.contrast_definition_cogatlas
        statisticmap.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0004_add_statisticmap'),
    ]

    operations = [
        migrations.RunPython(move_statmaps),
    ]
