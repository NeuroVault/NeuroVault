"""Celery entry points: thin driving adapters over the application services.

Task names keep their original module path so queued tasks still resolve.
"""
import os

from celery import Celery, shared_task
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.config.settings")
app = Celery("neurovault")
app.config_from_object("django.conf:settings")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task(name="neurovault.apps.statmaps.tasks.process_map")
def process_map(image_pk):
    """Thumbnail and fsaverage surfaces for a newly stored or replaced map."""
    from neurovault.config.bootstrap import services

    services().items.process(image_pk)


@shared_task(name="neurovault.apps.statmaps.tasks.save_resampled_transformation_single")
def save_resampled_transformation_single(pk1):
    """The 4mm brain-masked vector of a map (input of the gene-expression decoder)."""
    from neurovault.config.bootstrap import services

    return services().items.ensure_reduced_representation(pk1)


def repopulate_cognitive_atlas():
    from neurovault.adapters.external.cognitive_atlas import CognitiveAtlasGateway
    from neurovault.adapters.persistence.models import CognitiveAtlasContrast, CognitiveAtlasTask

    for task_id, task_name, contrasts in CognitiveAtlasGateway().tasks():
        task, _ = CognitiveAtlasTask.objects.update_or_create(
            cog_atlas_id=task_id, defaults={"name": task_name}
        )
        for contrast_id, contrast_name in contrasts:
            CognitiveAtlasContrast.objects.update_or_create(
                cog_atlas_id=contrast_id, defaults={"name": contrast_name, "task": task}
            )
    # Add an "Other" contrast
    task = CognitiveAtlasTask.objects.filter(name="None / Other")[0]
    CognitiveAtlasContrast.objects.update_or_create(
        cog_atlas_id="Other", defaults={"name": "Other", "task": task}
    )
