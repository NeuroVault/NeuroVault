# -*- coding: utf-8 -*-


from django.db import models, migrations
import json, os
dir = os.path.abspath(os.path.dirname(__file__))

def migrate_cogatlas_ids(apps, schema_editor):
    CognitiveAtlasTask = apps.get_model("statmaps", "CognitiveAtlasTask")
    StatisticMap = apps.get_model("statmaps", "StatisticMap")
    for smap in StatisticMap.objects.all():
        if smap.cognitive_paradigm_cogatlas_id:
            smap.cognitive_paradigm_cogatlas_id =  CognitiveAtlasTask.objects.filter(name=smap.cognitive_paradigm_cogatlas_id)[0].pk
            smap.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0031_auto_20150228_0153'),
    ]

    operations = [
        migrations.RunPython(migrate_cogatlas_ids),
    ]
