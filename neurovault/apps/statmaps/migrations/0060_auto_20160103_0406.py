# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0059_auto_20160101_0410'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='DOI',
            field=models.CharField(null=True, default=None, max_length=200, blank=True, unique=True, verbose_name=b'DOI of the corresponding paper (required if you want your maps to be archived in Stanford Digital Repository)'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='analysis_level',
            field=models.CharField(choices=[(b'S', b'single-subject'), (b'G', b'group'), (b'M', b'meta-analysis'), (b'Other', b'other')], max_length=200, blank=True, help_text=b'What level of summary data was used as the input to this analysis?', null=True, verbose_name=b'Analysis level'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'M', b'multivariate-beta map'), (b'U', b'univariate-beta map'), (b'R', b'ROI/mask'), (b'Pa', b'parcellation'), (b'A', b'anatomical'), (b'Other', b'other')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='analysis_level',
            field=models.CharField(choices=[(b'S', b'single-subject'), (b'G', b'group'), (b'M', b'meta-analysis'), (b'Other', b'other')], max_length=200, blank=True, help_text=b'What level of summary data was used as the input to this analysis?', null=True, verbose_name=b'Analysis level'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'M', b'multivariate-beta map'), (b'U', b'univariate-beta map'), (b'R', b'ROI/mask'), (b'Pa', b'parcellation'), (b'A', b'anatomical'), (b'Other', b'other')]),
            preserve_default=True,
        ),
    ]
