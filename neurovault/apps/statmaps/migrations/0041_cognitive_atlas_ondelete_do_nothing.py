# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0040_add_comparison_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, verbose_name=b'Cognitive Paradigm', to='statmaps.CognitiveAtlasTask', help_text=b"Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> terms", null=True),
            preserve_default=True,
        ),
    ]
