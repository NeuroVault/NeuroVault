# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0058_cogatlas_change'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_contrast_cogatlas',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='statmaps.CognitiveAtlasContrast', help_text=b"Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast", null=True, verbose_name=b'Cognitive Atlas Contrast'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Cognitive Paradigm', to='statmaps.CognitiveAtlasTask', help_text=b"Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/' target='_blank'>Cognitive Atlas</a> terms", null=True),
            preserve_default=True,
        ),
    ]
