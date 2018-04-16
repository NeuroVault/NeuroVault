# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0074_auto_20170919_2026'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='subject_species',
            field=models.CharField(default=b'homo sapiens', max_length=200,
                                   null=True, blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='target_template_image',
            field=models.CharField(default=b'GenericMNI',
                                   help_text=b'Name of target template image',
                                   max_length=200,
                                   verbose_name=b'Target template image',
                                   choices=[(b'MNI152NLin2009cAsym',
                                             b'Human (MNI152 NLin 2009c Asym)'),
                                            (b'GenericMNI',
                                             b'Human (Generic/Unknown MNI)'), (
                                            b'NMT',
                                            b'Rhesus - macacca mulatta (NMT)'),
                                            (b'Dorr2008',
                                             b'Mouse (Dorr 2008 space)')]),
        ),
    ]
