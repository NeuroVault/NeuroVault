# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0074_auto_20170718_1842'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collection',
            name='target_template_image',
        ),
        migrations.AddField(
            model_name='nidmresultstatisticmap',
            name='subject_species',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='subject_species',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='target_template_image',
            field=models.CharField(default=(b'MNI152', b'Human (MNI152)'), help_text=b'Name of target template image', max_length=200, verbose_name=b'Target template image', choices=[(b'MNI152NLin2009cAsym', b'Human (MNI152 NLin 2009c Asym)'), (b'MNI152', b'Human (MNI152)'), (b'NMT', b'Rhesus (macacca mulatta), NMT space'), (b'Door_2008_average', b'Mouse (Dorr 2008 space)')]),
        ),
    ]
