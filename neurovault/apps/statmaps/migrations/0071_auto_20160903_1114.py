# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0070_auto_20160526_2216'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticmap',
            name='cognitive_paradigm_description_url',
            field=models.URLField(help_text=b'Link to a paper, poster, abstract or other form text describing in detail the task performed by the subject(s) in the scanner.', null=True, verbose_name=b'Cognitive Paradigm Description URL', blank=True),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Cognitive Atlas Paradigm', to='statmaps.CognitiveAtlasTask', help_text=b"Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/' target='_blank'>Cognitive Atlas</a> terms", null=True),
        ),
    ]
