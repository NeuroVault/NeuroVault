# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from neurovault.apps.statmaps.tasks import repopulate_cognitive_atlas
from django.db import models, migrations
import os
dir = os.path.abspath(os.path.dirname(__file__))


# COGNITIVE ATLAS
###########################################################################
def populate_cogatlas(apps, schema_editor):
    CognitiveAtlasTask = apps.get_model("statmaps", "CognitiveAtlasTask")
    CognitiveAtlasContrast = apps.get_model("statmaps", "CognitiveAtlasContrast")
    repopulate_cognitive_atlas(CognitiveAtlasTask,CognitiveAtlasContrast)

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0025_cognitiveatlascontrast'),
    ]

    operations = [
        migrations.RunPython(populate_cogatlas),
    ]
