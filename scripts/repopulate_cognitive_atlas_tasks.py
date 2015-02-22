import os
import json
from neurovault.apps.statmaps.models import CognitiveAtlasTask,\
    CognitiveAtlasContrast
    
dir = os.path.abspath(os.path.dirname(__file__))

json_content = open(os.path.join(dir, "../neurovault/apps/statmaps/migrations/cognitiveatlas_tasks.json")).read()
json_content = json_content.decode("utf-8").replace('\t', '').replace("&#39;", "'")
data = json.loads(json_content)
CognitiveAtlasTask.objects.all().delete()
CognitiveAtlasContrast.objects.all().delete()
for item in data:
    task = CognitiveAtlasTask(name=item["name"], cog_atlas_id=item["id"])
    task.save()
    for contrast in item["contrasts"]:
        contrast = CognitiveAtlasContrast(name=contrast["conname"], cog_atlas_id=contrast["conid"], task=task)
        contrast.save()