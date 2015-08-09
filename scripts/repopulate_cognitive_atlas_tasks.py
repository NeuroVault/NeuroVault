import os
import json
from neurovault.apps.statmaps.models import CognitiveAtlasTask, CognitiveAtlasContrast

# not required, will be: pip install cognitiveatlas 
# https://cogat-python.readthedocs.org
from cognitiveatlas.api import get_task
tasks = get_task()

# Update tasks
for t in range(0,len(tasks.json)):
    task = tasks.json[t]
    print "%s of %s" %(t,len(tasks.json)) 
    if tasks.json[t]["name"]:
        task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=task["id"], defaults={"name":task["name"]})
        task.save()
        if tasks.json[t]["id"]:
            task_details = get_task(id=tasks.json[t]["id"])
            if task_details.json[0]["contrasts"]:
                print "Found %s contrasts!" %(len(task_details.json[0]["contrasts"]))
                for contrast in task_details.json[0]["contrasts"]:
                   contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id=contrast["id"], defaults={"name":contrast["contrast_text"], "task":task})
                   contrast.save() 

