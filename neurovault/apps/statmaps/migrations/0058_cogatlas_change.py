# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def cogatlas_change(apps, schema_editor):
    CognitiveAtlasTask = apps.get_model("statmaps", "CognitiveAtlasTask")
    CognitiveAtlasTask.objects.update_or_create(name="None / Other",
                                                defaults={cog_atlas_id:"other"})

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0057c_populate_permissions'),
    ]

    operations = [
        migrations.RunPython(cogatlas_change),
    ]
