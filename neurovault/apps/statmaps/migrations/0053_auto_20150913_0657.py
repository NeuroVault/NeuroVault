# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from neurovault.apps.statmaps.tasks import repopulate_cognitive_atlas

class Migration(migrations.Migration):

    def repopulate_cogatlas(apps, schema_editor):
        CognitiveAtlasTask = apps.get_model("statmaps", "CognitiveAtlasTask")
        CognitiveAtlasContrast = apps.get_model("statmaps", "CognitiveAtlasContrast")

        repopulate_cognitive_atlas(CognitiveAtlasTask,CognitiveAtlasContrast)

    dependencies = [
        ('statmaps', '0052_statisticmap_cognitive_contrast_cogatlas'),
    ]

    operations = [
        migrations.RunPython(repopulate_cogatlas)
    ]
