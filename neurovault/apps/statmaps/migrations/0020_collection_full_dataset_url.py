# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0019_auto_20150131_0038'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='full_dataset_url',
            field=models.URLField(help_text=b'Link to an external dataset the maps in this collection have been generated from (for example: \"https://openfmri.org/dataset/ds000001\" or \"http://dx.doi.org/10.15387/fcp_indi.corr.mpg1\")', null=True, verbose_name=b'Full dataset URL', blank=True),
            preserve_default=True,
        ),
    ]
