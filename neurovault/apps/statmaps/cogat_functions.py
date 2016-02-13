from neurovault.apps.statmaps.models import CognitiveAtlasTask, CognitiveAtlasContrast
from cognitiveatlas.api import get_task, get_concept
import numpy as np

# Function to make a node
def make_node(nid,name,color):
    return {"nid":str(nid),"name":str(name),"color":color}

def get_task_graph(task_id):
    '''get_task_graph will return a tree for a single cognitive atlas tasks defined in NeuroVault
    '''
    # Get all contrasts defined for Cognitive Atlas
    task = CognitiveAtlasTask.objects.filter(cog_atlas_id=task_id)[0]

    task_node = make_node(task.cog_atlas_id,task.name,"#63506d")
    task_contrasts = CognitiveAtlasContrast.objects.filter(task=task)
    task_concepts = []
    for contrast in task_contrasts:
        try:
            contrast_node = make_node(contrast.cog_atlas_id,contrast.name,"#d89013")
            contrast_concepts = get_concept(contrast_id=contrast.cog_atlas_id)
            children = []
            current_names = []
            for concept in contrast_concepts.json:
                if concept["name"] not in current_names:
                    children.append(make_node(concept["id"],concept["name"],"#3c7263"))
                    current_names.append(concept["name"])
                contrast_node["children"] = children
            # Only append contrast if it has children
            if len(children) > 0:
                task_concepts.append(contrast_node)
        except:
            pass
    task_node["children"] = task_concepts    
    return task_node

