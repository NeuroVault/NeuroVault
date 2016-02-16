import numpy as np
from cognitiveatlas.api import get_task, get_concept

from neurovault.apps.statmaps.models import CognitiveAtlasTask, CognitiveAtlasContrast, StatisticMap


# Function to make a node
def make_node(nid,name,color,url=None):
    '''make_node will return a json node for a cognitive atlas task, contrast, concept, or an image. if a url is provided, it will be included
    :param nid: the node id
    :param name: the node name
    :param color: the node color
    :param url: a url for the node to link to when clicked (be careful giving this to non base nodes)
    '''
    if url == None:
        return {"nid":str(nid),"name":str(name),"color":color}
    else:
        return {"nid":str(nid),"name":str(name),"color":color,"url":url}

def get_task_graph(task_id, images=None):
    '''get_task_graph will return a tree for a single cognitive atlas tasks defined in NeuroVault
    :param task_id: the Cognitive Atlas task id
    :param get_images_with_contrasts: boolean to return images that have contrasts (default False)
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
            children = [] # concept children of a contrast
            current_names = []

            # Do we have images tagged with the contrast?
            if not images:
                images = StatisticMap.objects.filter(cognitive_contrast_cogatlas=contrast)

            for concept in contrast_concepts.json:
                if concept["name"] not in current_names:                   
                    concept_node = make_node(concept["id"],concept["name"],"#3c7263")

                    # Image nodes
                    if len(stat_maps) > 0:
                        stat_map_nodes = [make_node(i.pk,i.name,"#337ab7","/images/%s" %(i.pk)) for i in images]
                        concept_node["children"] = stat_map_nodes

                    children.append(concept_node)
                    current_names.append(concept["name"])
                contrast_node["children"] = children
            # Only append contrast if it has children
            if len(children) > 0:
                task_concepts.append(contrast_node)
        except:
            pass
    task_node["children"] = task_concepts    

    return task_node
