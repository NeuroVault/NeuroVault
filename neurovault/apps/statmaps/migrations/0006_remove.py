# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations



class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0005_move_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='contrast_definition',
        ),
        migrations.RemoveField(
            model_name='image',
            name='contrast_definition_cogatlas',
        ),
        migrations.RemoveField(
            model_name='image',
            name='map_type',
        ),
        migrations.RemoveField(
            model_name='image',
            name='smoothness_fwhm',
        ),
        migrations.RemoveField(
            model_name='image',
            name='statistic_parameters',
        ),
    ]
