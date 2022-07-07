# -*- coding: utf-8 -*-


from django.db import models, migrations
import json, os
dir = os.path.abspath(os.path.dirname(__file__))

def populate_cogatlas(apps, schema_editor):
    CognitiveAtlasTask = apps.get_model("statmaps", "CognitiveAtlasTask")
    CognitiveAtlasContrast = apps.get_model("statmaps", "CognitiveAtlasContrast")
    json_content = open(os.path.join(dir, "cognitiveatlas_tasks.json")).read()
    json_content = json_content.decode("utf-8").replace('\t', '')
    data = json.loads(json_content)
    for item in data:
        task = CognitiveAtlasTask(name=item["name"], cog_atlas_id=item["id"])
        task.save()
        for contrast in item["contrasts"]:
            contrast = CognitiveAtlasContrast(name=contrast["conname"], cog_atlas_id=contrast["conid"], task=task)
            contrast.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0025_cognitiveatlascontrast'),
    ]

    operations = [
        migrations.RunPython(populate_cogatlas),
    ]
