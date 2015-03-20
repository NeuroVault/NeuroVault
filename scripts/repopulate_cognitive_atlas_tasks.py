import os
import json
from neurovault.apps.statmaps.models import CognitiveAtlasTask,\
    CognitiveAtlasContrast
    
dir = os.path.abspath(os.path.dirname(__file__))

json_content = open(os.path.join(dir, "../neurovault/apps/statmaps/migrations/cognitiveatlas_tasks.json")).read()
json_content = json_content.decode("utf-8").replace('\t', '').replace("&#39;", "'")
data = json.loads(json_content)
for item in data:
    task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=item["id"], defaults={"name":item["name"]})
    task.save()
    for contrast in item["contrasts"]:
        contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id=contrast["conid"], defaults={"name":contrast["conname"], "task":task})
        contrast.save()