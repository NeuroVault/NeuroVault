from neurovault.apps.statmaps.forms import StatisticMapForm, AtlasForm, NIDMResultsForm
from neurovault.apps.statmaps.models import Collection, Image, CognitiveAtlasTask
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from neurovault.settings import PRIVATE_MEDIA_ROOT
import shutil
import os


def clearDB():
    try:
        Image.objects.all().delete()
        Collection.objects.all().delete()
    except Exception as e:
        print(e)
    if os.path.exists(PRIVATE_MEDIA_ROOT):
        for the_file in os.listdir(PRIVATE_MEDIA_ROOT):
            file_path = os.path.join(PRIVATE_MEDIA_ROOT, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(e)


def save_statmap_form(
    image_path, collection, ignore_file_warning=False, image_name=None
):  
    collection.save()
    if image_name is None:
        image_name = image_path

    post_dict = {
        "name": image_name,
        "map_type": "T",
        "collection": collection.pk,
        "cognitive_task_choice": "yes_other",
        "ignore_file_warning": ignore_file_warning,
        "file": SimpleUploadedFile(image_path, open(image_path, "rb").read()),
        "modality": "fMRI-BOLD",
        "target_template_image": "GenericMNI",
        "cognitive_paradigm_cogatlas": CognitiveAtlasTask.objects.first(),
        "analysis_level": "S",
        "number_of_subjects": 1,
    }

    file_dict = {
        "file": SimpleUploadedFile(image_path, open(image_path, "rb").read()),
    }
    form = StatisticMapForm(post_dict, file_dict)
    statmap = form.save(commit=False)
    statmap.collection = collection
    statmap.save()
    return statmap


def save_atlas_form(
    nii_path, xml_path, collection, ignore_file_warning=False, name=None
):
    if name is None:
        name = nii_path

    post_dict = {
        "name": name,
        "map_type": "Atlas",
        "collection": collection.pk,
        "ignore_file_warning": ignore_file_warning,
    }

    file_dict = {
        "file": SimpleUploadedFile(nii_path, open(nii_path, "rb").read()),
        "label_description_file": SimpleUploadedFile(
            xml_path, open(xml_path, "rb").read()
        ),
    }
    form = AtlasForm(post_dict, file_dict)
    atlas = form.save(commit=False)
    atlas.collection = collection
    atlas.save()
    return atlas


def save_nidm_form(zip_file, collection, name=None):
    if name == None:
        name = "fsl_nidm"
    with open(zip_file, "rb") as f:
        post_dict = {
            "name": name,
            "collection": collection.pk,
            "ignore_file_warning": True,
        }
        file_dict = {"zip_file": SimpleUploadedFile(zip_file, f.read())}
        form = NIDMResultsForm(post_dict, file_dict)
    return form.save()
