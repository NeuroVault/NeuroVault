"""Copy the polymorphic item rows into Item and NIDMBundle (docs/design/0001 §6).

Every row keeps its basecollectionitem id, so URLs, API ids, comparisons,
meta-analysis selections and file paths stay valid. Tags are re-pointed at
the new content types; per-item guardian rows are dropped (item access now
follows the collection, decision D7).
"""
from django.db import migrations

STAT_COLUMNS = (
    "map_type", "is_thresholded", "perc_bad_voxels", "not_mni", "brain_coverage",
    "perc_voxels_outside", "analysis_level", "number_of_subjects",
)
ANNOTATION_COLUMNS = (
    "ignore_file_warning", "modality", "statistic_parameters", "smoothness_fwhm",
    "contrast_definition", "contrast_definition_cogatlas", "cognitive_paradigm_cogatlas_id",
    "cognitive_contrast_cogatlas_id", "cognitive_paradigm_description_url",
    "cognitive_paradigm_short_description", "cognitive_paradigm_name",
)
BASE_COLUMNS = ("id", "name", "description", "collection_id", "add_date", "modify_date", "is_valid")
OLD_ITEM_MODELS = ("basecollectionitem", "image", "statisticmap", "nidmresultstatisticmap", "atlas")


def item_columns(apps):
    Item = apps.get_model("statmaps", "Item")
    return [f.column for f in Item._meta.concrete_fields]


def image_columns(apps):
    Image = apps.get_model("statmaps", "Image")
    return [
        f.column for f in Image._meta.local_concrete_fields if f.column != "basecollectionitem_ptr_id"
    ]


def copy(apps, schema_editor):
    q = schema_editor.connection.ops.quote_name
    image_cols = image_columns(apps)
    select = {c: "b.%s" % q(c) for c in BASE_COLUMNS}
    select.update({c: "i.%s" % q(c) for c in image_cols})
    select.update({c: "COALESCE(s.%s, n.%s)" % (q(c), q(c)) for c in STAT_COLUMNS})
    select.update({c: "s.%s" % q(c) for c in ANNOTATION_COLUMNS})
    select["label_description_file"] = "a.label_description_file"
    select["source_bundle_id"] = "n.nidm_results_id"
    select["kind"] = (
        "CASE WHEN s.image_ptr_id IS NOT NULL OR n.image_ptr_id IS NOT NULL THEN 'statmap' "
        "WHEN a.image_ptr_id IS NOT NULL THEN 'atlas' ELSE 'other' END"
    )
    columns = item_columns(apps)
    missing = set(columns) - set(select)
    assert not missing, "unmapped Item columns: %s" % sorted(missing)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO statmaps_nidmbundle (%s, zip_file, ttl_file) "
            "SELECT %s, r.zip_file, r.ttl_file FROM statmaps_basecollectionitem b "
            "JOIN statmaps_nidmresults r ON r.basecollectionitem_ptr_id = b.id"
            % (", ".join(BASE_COLUMNS), ", ".join("b.%s" % c for c in BASE_COLUMNS))
        )
        cursor.execute(
            "INSERT INTO statmaps_item (%s) SELECT %s FROM statmaps_basecollectionitem b "
            "JOIN statmaps_image i ON i.basecollectionitem_ptr_id = b.id "
            "LEFT JOIN statmaps_statisticmap s ON s.image_ptr_id = b.id "
            "LEFT JOIN statmaps_nidmresultstatisticmap n ON n.image_ptr_id = b.id "
            "LEFT JOIN statmaps_atlas a ON a.image_ptr_id = b.id"
            % (", ".join(q(c) for c in columns), ", ".join(select[c] for c in columns))
        )
        # new ids continue after every old one, in both tables
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM statmaps_basecollectionitem")
        (max_id,) = cursor.fetchone()
        for table in ("statmaps_item", "statmaps_nidmbundle"):
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), %s, %s)",
                [table, max(max_id, 1), max_id > 0],
            )

    ContentType = apps.get_model("contenttypes", "ContentType")
    item_ct, _ = ContentType.objects.get_or_create(app_label="statmaps", model="item")
    bundle_ct, _ = ContentType.objects.get_or_create(app_label="statmaps", model="nidmbundle")
    old_item_cts = list(
        ContentType.objects.filter(app_label="statmaps", model__in=OLD_ITEM_MODELS).values_list("pk", flat=True)
    )
    old_bundle_cts = list(
        ContentType.objects.filter(app_label="statmaps", model="nidmresults").values_list("pk", flat=True)
    )
    ValueTaggedItem = apps.get_model("statmaps", "ValueTaggedItem")
    ValueTaggedItem.objects.filter(content_type_id__in=old_item_cts).update(content_type=item_ct)
    ValueTaggedItem.objects.filter(content_type_id__in=old_bundle_cts).update(content_type=bundle_ct)

    UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")
    for model in (UserObjectPermission, GroupObjectPermission):
        model.objects.filter(content_type_id__in=old_item_cts + old_bundle_cts).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("statmaps", "0006_item_and_nidm_bundle"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("guardian", "0002_generic_permissions_index"),
    ]

    operations = [
        migrations.RunPython(copy, migrations.RunPython.noop, elidable=False),
    ]
