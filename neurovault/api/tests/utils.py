from neurovault.apps.statmaps.models import CognitiveAtlasTask, CognitiveAtlasContrast

def _setup_test_cognitive_atlas():
    cat = CognitiveAtlasTask.objects.update_or_create(
        cog_atlas_id="trm_4f24126c22011",defaults={"name": "action observation task"})
    cat[0].save()
    contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id="cnt_4e08fefbf0382", 
                                                                defaults={"name":"standard deviation from the mean accuracy score",
                                                                "task": cat[0]})
    contrast.save()

    return cat[0], contrast