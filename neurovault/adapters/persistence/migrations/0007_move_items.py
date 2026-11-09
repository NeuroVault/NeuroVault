"""Move the polymorphic item rows into Item and NIDMBundle (docs/design/0001 §6, §8).

One atomic migration:

1. Lock the old item tables against writes, so nothing written by a still
   running old release is lost between the copy and the drop.
2. Pre-flight: abort on malformed rows (an item row with no image or NIDM
   child, or whose polymorphic type disagrees with its child tables) and on
   database views that depend on the old tables (the drop cascades).
3. Copy every row, keeping its basecollectionitem id, so URLs, API ids,
   comparisons, meta-analysis selections and file paths stay valid. Tags are
   re-pointed at the new content types. Per-item guardian rows are dropped:
   item access follows the collection (decision D7).
4. NIDMBundle ids come from Item's sequence, so images and bundles keep one
   id space, as before.
5. Re-point comparisons and meta-analysis selections at Item, then drop the
   old tables.

The reverse copies everything back (rows, tags, and per-item permissions
re-derived from each collection's owner and contributors), so rolling back
to 0005 loses nothing.
"""
import django.db.models.deletion
from django.db import migrations, models

OLD_TABLES = (
    "statmaps_basecollectionitem", "statmaps_image", "statmaps_statisticmap",
    "statmaps_nidmresultstatisticmap", "statmaps_atlas", "statmaps_nidmresults",
)
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
CHILD_KIND = (
    "CASE WHEN s.image_ptr_id IS NOT NULL THEN 'statisticmap' "
    "WHEN n.image_ptr_id IS NOT NULL THEN 'nidmresultstatisticmap' "
    "WHEN a.image_ptr_id IS NOT NULL THEN 'atlas' "
    "WHEN i.basecollectionitem_ptr_id IS NOT NULL THEN 'image' "
    "WHEN r.basecollectionitem_ptr_id IS NOT NULL THEN 'nidmresults' END"
)
CHILD_JOINS = (
    "FROM statmaps_basecollectionitem b "
    "LEFT JOIN statmaps_image i ON i.basecollectionitem_ptr_id = b.id "
    "LEFT JOIN statmaps_statisticmap s ON s.image_ptr_id = b.id "
    "LEFT JOIN statmaps_nidmresultstatisticmap n ON n.image_ptr_id = b.id "
    "LEFT JOIN statmaps_atlas a ON a.image_ptr_id = b.id "
    "LEFT JOIN statmaps_nidmresults r ON r.basecollectionitem_ptr_id = b.id "
)


def image_columns(apps):
    Image = apps.get_model("statmaps", "Image")
    return [f.column for f in Image._meta.local_concrete_fields if f.column != "basecollectionitem_ptr_id"]


def item_columns(apps):
    return [f.column for f in apps.get_model("statmaps", "Item")._meta.concrete_fields]


def content_types(apps, models_):
    ContentType = apps.get_model("contenttypes", "ContentType")
    return {m: ContentType.objects.get_or_create(app_label="statmaps", model=m)[0].pk for m in models_}


def share_id_sequence(cursor):
    """NIDMBundle takes its ids from Item's sequence (one id space)."""
    cursor.execute("ALTER TABLE statmaps_nidmbundle ALTER COLUMN id DROP IDENTITY IF EXISTS")
    cursor.execute(
        "ALTER TABLE statmaps_nidmbundle ALTER COLUMN id SET DEFAULT "
        "nextval(pg_get_serial_sequence('statmaps_item', 'id')::regclass)"
    )


def preflight(cursor):
    cursor.execute(
        "SELECT count(*) FROM statmaps_basecollectionitem b WHERE NOT EXISTS "
        "(SELECT 1 FROM statmaps_image i WHERE i.basecollectionitem_ptr_id = b.id) AND NOT EXISTS "
        "(SELECT 1 FROM statmaps_nidmresults r WHERE r.basecollectionitem_ptr_id = b.id)"
    )
    (orphans,) = cursor.fetchone()
    cursor.execute(
        "SELECT count(*) " + CHILD_JOINS + "JOIN django_content_type ct ON ct.id = b.polymorphic_ctype_id "
        "WHERE ct.model IS DISTINCT FROM " + CHILD_KIND
    )
    (mistyped,) = cursor.fetchone()
    cursor.execute(
        "SELECT DISTINCT view_schema || '.' || view_name FROM information_schema.view_table_usage "
        "WHERE table_name = ANY(%s)", [list(OLD_TABLES)]
    )
    views = [r[0] for r in cursor.fetchall()]
    problems = []
    if orphans:
        problems.append("%d statmaps_basecollectionitem rows have no image or NIDM child" % orphans)
    if mistyped:
        problems.append("%d item rows' polymorphic type disagrees with their child tables" % mistyped)
    if views:
        problems.append("views depend on the old item tables: %s" % ", ".join(views))
    if problems:
        raise RuntimeError("0007_move_items aborted: " + "; ".join(problems))


def forward(apps, schema_editor):
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "LOCK TABLE %s, statmaps_valuetaggeditem, statmaps_comparison, statmaps_metaanalysis_maps "
            "IN EXCLUSIVE MODE" % ", ".join(OLD_TABLES)
        )
        preflight(cursor)
        share_id_sequence(cursor)

        select = {c: "b.%s" % q(c) for c in BASE_COLUMNS}
        select.update({c: "i.%s" % q(c) for c in image_columns(apps)})
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
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM statmaps_basecollectionitem")
        (max_id,) = cursor.fetchone()
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('statmaps_item', 'id'), %s, %s)",
            [max(max_id, 1), max_id > 0],
        )

    ct = content_types(apps, OLD_ITEM_MODELS + ("nidmresults", "item", "nidmbundle"))
    ValueTaggedItem = apps.get_model("statmaps", "ValueTaggedItem")
    ValueTaggedItem.objects.filter(content_type_id__in=[ct[m] for m in OLD_ITEM_MODELS]).update(
        content_type_id=ct["item"]
    )
    ValueTaggedItem.objects.filter(content_type_id=ct["nidmresults"]).update(content_type_id=ct["nidmbundle"])
    old = [ct[m] for m in OLD_ITEM_MODELS + ("nidmresults",)]
    for name in ("UserObjectPermission", "GroupObjectPermission"):
        apps.get_model("guardian", name).objects.filter(content_type_id__in=old).delete()


def backward(apps, schema_editor):
    """Copy Item and NIDMBundle rows back into the polymorphic tables."""
    q = schema_editor.connection.ops.quote_name
    ct = content_types(apps, OLD_ITEM_MODELS + ("nidmresults", "item", "nidmbundle"))
    image_cols = image_columns(apps)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("LOCK TABLE statmaps_item, statmaps_nidmbundle IN EXCLUSIVE MODE")
        old_kind = (
            "CASE WHEN it.kind = 'statmap' AND it.source_bundle_id IS NULL THEN %(statisticmap)s "
            "WHEN it.kind = 'statmap' THEN %(nidmresultstatisticmap)s "
            "WHEN it.kind = 'atlas' THEN %(atlas)s ELSE %(image)s END" % ct
        )
        cursor.execute(
            "INSERT INTO statmaps_basecollectionitem (%s, polymorphic_ctype_id) "
            "SELECT %s, %s FROM statmaps_nidmbundle it"
            % (", ".join(BASE_COLUMNS), ", ".join("it.%s" % c for c in BASE_COLUMNS), ct["nidmresults"])
        )
        cursor.execute(
            "INSERT INTO statmaps_basecollectionitem (%s, polymorphic_ctype_id) "
            "SELECT %s, %s FROM statmaps_item it"
            % (", ".join(BASE_COLUMNS), ", ".join("it.%s" % c for c in BASE_COLUMNS), old_kind)
        )
        cursor.execute(
            "INSERT INTO statmaps_nidmresults (basecollectionitem_ptr_id, zip_file, ttl_file) "
            "SELECT id, zip_file, ttl_file FROM statmaps_nidmbundle"
        )
        cursor.execute(
            "INSERT INTO statmaps_image (basecollectionitem_ptr_id, %s) SELECT id, %s FROM statmaps_item"
            % (", ".join(q(c) for c in image_cols), ", ".join(q(c) for c in image_cols))
        )
        stat = ", ".join(q(c) for c in STAT_COLUMNS)
        annotation = ", ".join(q(c) for c in ANNOTATION_COLUMNS)
        cursor.execute(
            "INSERT INTO statmaps_statisticmap (image_ptr_id, %s, %s) SELECT id, %s, %s FROM statmaps_item "
            "WHERE kind = 'statmap' AND source_bundle_id IS NULL" % (stat, annotation, stat, annotation)
        )
        cursor.execute(
            "INSERT INTO statmaps_nidmresultstatisticmap (image_ptr_id, %s, nidm_results_id) "
            "SELECT id, %s, source_bundle_id FROM statmaps_item WHERE source_bundle_id IS NOT NULL"
            % (stat, stat)
        )
        cursor.execute(
            "INSERT INTO statmaps_atlas (image_ptr_id, label_description_file) "
            "SELECT id, label_description_file FROM statmaps_item WHERE kind = 'atlas'"
        )
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('statmaps_basecollectionitem', 'id'), "
            "GREATEST((SELECT COALESCE(MAX(id), 1) FROM statmaps_basecollectionitem), 1), "
            "(SELECT COUNT(*) > 0 FROM statmaps_basecollectionitem))"
        )
        # tags: back to the subclass content types the polymorphic models wrote
        cursor.execute(
            "UPDATE statmaps_valuetaggeditem t SET content_type_id = " + old_kind.replace("it.", "it2.")
            + " FROM statmaps_item it2 WHERE t.content_type_id = %s AND t.object_id = it2.id",
            [ct["item"]],
        )
        cursor.execute(
            "UPDATE statmaps_valuetaggeditem SET content_type_id = %s WHERE content_type_id = %s",
            [ct["nidmresults"], ct["nidmbundle"]],
        )

    # per-item permissions, as the old signals granted them: owner and contributors
    Permission = apps.get_model("auth", "Permission")
    UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    Collection = apps.get_model("statmaps", "Collection")
    base_ct = ct["basecollectionitem"]
    perms = [
        Permission.objects.get_or_create(
            content_type_id=base_ct, codename=codename, defaults={"name": "Can %s base collection item" % verb}
        )[0]
        for codename, verb in (("change_basecollectionitem", "change"), ("delete_basecollectionitem", "delete"))
    ]
    BaseCollectionItem = apps.get_model("statmaps", "BaseCollectionItem")
    rows = []
    for collection in Collection.objects.all():
        users = ([collection.owner_id] if collection.owner_id else []) + list(
            collection.contributors.values_list("pk", flat=True)
        )
        for item_id in BaseCollectionItem.objects.filter(collection=collection).values_list("pk", flat=True):
            for user_id in users:
                for perm in perms:
                    rows.append(UserObjectPermission(
                        user_id=user_id, permission=perm, content_type_id=base_ct, object_pk=str(item_id)
                    ))
    UserObjectPermission.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("statmaps", "0006_item_and_nidm_bundle"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("guardian", "0002_generic_permissions_index"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(forward, backward, elidable=False),
        migrations.AlterField(
            model_name="comparison",
            name="image1",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="image1", to="statmaps.item"
            ),
        ),
        migrations.AlterField(
            model_name="comparison",
            name="image2",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="image2", to="statmaps.item"
            ),
        ),
        migrations.AlterField(
            model_name="metaanalysis",
            name="maps",
            field=models.ManyToManyField(blank=True, to="statmaps.item"),
        ),
        migrations.RemoveIndex(model_name="statisticmap", name="statmaps_st_modalit_4bad2e_idx"),
        migrations.DeleteModel(name="NIDMResultStatisticMap"),
        migrations.DeleteModel(name="StatisticMap"),
        migrations.DeleteModel(name="Atlas"),
        migrations.DeleteModel(name="NIDMResults"),
        migrations.DeleteModel(name="Image"),
        migrations.DeleteModel(name="BaseCollectionItem"),
    ]
