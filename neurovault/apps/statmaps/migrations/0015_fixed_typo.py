# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0014_add_contrast_estimation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='parameterestimatemap',
            old_name='modelParameterEstimation',
            new_name='modelParametersEstimation',
        ),
    ]
