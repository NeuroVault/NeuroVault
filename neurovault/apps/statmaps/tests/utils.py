import os
import shutil

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile

from neurovault.application.ports import SYSTEM
from neurovault.apps.statmaps.forms import StatisticMapForm, AtlasForm, NIDMResultsForm, image_changes
from neurovault.apps.statmaps.models import Item, Collection, CognitiveAtlasTask
from neurovault.bootstrap import services
from neurovault.settings import PRIVATE_MEDIA_ROOT

COLLECTION_SKIP = ("id", "owner", "add_date", "modify_date", "doi_add_date")
ITEM_SKIP = ("id", "kind", "collection", "add_date", "modify_date")


def clearDB():
    """Remove stored files. The database is rolled back by TestCase.

    """
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


def persist(obj):
    """Store an unsaved Collection or Item built in a test through the use cases.

    The object's primary key is set and its fields are refreshed, so the test
    can keep using it.
    """
    if isinstance(obj, Collection):
        changes = {
            f.attname: getattr(obj, f.attname)
            for f in obj._meta.concrete_fields
            if f.name not in COLLECTION_SKIP
        }
        new_id = services().collections.save(SYSTEM, None, changes, owner_id=obj.owner_id)
    else:
        from neurovault.domain.items import column_names

        allowed = column_names(obj.kind, from_nidm=obj.source_bundle_id is not None)
        changes, files = {}, {}
        for f in obj._meta.concrete_fields:
            if f.name in ITEM_SKIP or (f.attname not in allowed and f.name not in allowed):
                continue
            value = getattr(obj, f.attname)
            if isinstance(value, FieldFile):
                if value and not value._committed:
                    files[f.name] = value.file
                continue
            changes[f.attname] = value
        from neurovault.application.services.items import ImageFilesInput

        new_id = services().items.add(
            SYSTEM, obj.collection_id, obj.kind, changes, ImageFilesInput(**files),
            check_access=False,
        )
    obj.pk = new_id
    obj.refresh_from_db()
    return obj


def add_contributor(collection, user):
    current = list(collection.contributors.values_list("pk", flat=True))
    services().collections.save(SYSTEM, collection.pk, {}, contributor_ids=current + [user.pk])
    collection.refresh_from_db()


def save_image_form(form, collection, kind):
    assert form.is_valid(), form.errors
    changes, files, tags = image_changes(form)
    changes.pop("collection_id", None)
    new_id = services().items.add(SYSTEM, collection.pk, kind, changes, files, tags=tags,
                                  check_access=False)
    return Item.objects.get(pk=new_id)


def save_statmap_form(
    image_path, collection, ignore_file_warning=False, image_name=None
):
    if collection.pk is None:
        persist(collection)
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
    return save_image_form(StatisticMapForm(post_dict, file_dict), collection, "statmap")


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
    return save_image_form(AtlasForm(post_dict, file_dict), collection, "atlas")


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
    assert form.is_valid(), form.errors
    return form.save()
