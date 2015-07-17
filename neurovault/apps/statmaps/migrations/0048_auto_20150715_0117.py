# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0047_auto_20150619_0049'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'M', b'multivariate-beta map'), (b'U', b'univariate-beta map'), (b'R', b'ROI/mask'), (b'Pa', b'parcellation'), (b'Other', b'Other')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'M', b'multivariate-beta map'), (b'U', b'univariate-beta map'), (b'R', b'ROI/mask'), (b'Pa', b'parcellation'), (b'Other', b'Other')]),
            preserve_default=True,
        ),
    ]
