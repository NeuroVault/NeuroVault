"""The polymorphic-to-Item data migration (0007) on one row of every kind.

The local development data only contains statistic maps, so this covers the
other kinds, tags, comparisons, meta-analysis selections and permissions.
"""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("statmaps", "0005_alter_basecollectionitem_modify_date")]
AFTER = [("statmaps", "0008_repoint_item_references")]
CONTEXT = [("guardian", "0002_generic_permissions_index"), ("auth", "0012_alter_user_first_name_max_length")]


class CopyItemsMigration(TransactionTestCase):
    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest = executor.loader.graph.leaf_nodes()
        executor.migrate(BEFORE)
        apps = executor.loader.project_state(BEFORE + CONTEXT).apps

        User = apps.get_model("auth", "User")
        ContentType = apps.get_model("contenttypes", "ContentType")
        Permission = apps.get_model("auth", "Permission")
        Collection = apps.get_model("statmaps", "Collection")
        Task = apps.get_model("statmaps", "CognitiveAtlasTask")
        ct = {
            m: ContentType.objects.get_or_create(app_label="statmaps", model=m)[0]
            for m in ("basecollectionitem", "image", "statisticmap", "nidmresults",
                      "nidmresultstatisticmap", "atlas")
        }
        owner = User.objects.create(username="owner")
        collection = Collection.objects.create(name="c", owner=owner)
        task = Task.objects.create(cog_atlas_id="trm_x", name="task")

        def common(model, **kw):
            return dict(collection=collection, polymorphic_ctype=ct[model], **kw)

        self.statmap = apps.get_model("statmaps", "StatisticMap").objects.create(
            **common("statisticmap", name="statmap", description="d", file="images/1/s.nii.gz",
                     map_type="T", modality="fMRI-BOLD", analysis_level="G", number_of_subjects=20,
                     perc_bad_voxels=float("nan"), cognitive_paradigm_cogatlas=task,
                     data={"extra": "x"}, thumbnail="images/1/glass_brain_1.jpg", age=33.0)
        ).pk
        bundle = apps.get_model("statmaps", "NIDMResults").objects.create(
            **common("nidmresults", name="b.nidm", zip_file="images/1/b.nidm/b.nidm.zip",
                     ttl_file="images/1/b.nidm/nidm.ttl")
        )
        self.bundle = bundle.pk
        self.nidm_map = apps.get_model("statmaps", "NIDMResultStatisticMap").objects.create(
            **common("nidmresultstatisticmap", name="nidm map", file="images/1/b.nidm/T.nii.gz",
                     map_type="Z", analysis_level="Other", number_of_subjects=0, nidm_results=bundle)
        ).pk
        self.atlas = apps.get_model("statmaps", "Atlas").objects.create(
            **common("atlas", name="atlas", file="images/1/a.nii.gz",
                     label_description_file="images/1/a.xml")
        ).pk
        self.other = apps.get_model("statmaps", "Image").objects.create(
            **common("image", name="plain", file="images/1/p.nii.gz")
        ).pk

        Tag = apps.get_model("statmaps", "KeyValueTag")
        Tagged = apps.get_model("statmaps", "ValueTaggedItem")
        for pk, model, name in ((self.statmap, "statisticmap", "visual"), (self.atlas, "atlas", "parc"),
                                (self.bundle, "nidmresults", "nidm")):
            Tagged.objects.create(tag=Tag.objects.create(name=name, slug=name),
                                  content_type=ct[model], object_id=pk)

        Similarity = apps.get_model("statmaps", "Similarity")
        apps.get_model("statmaps", "Comparison").objects.create(
            image1_id=self.statmap, image2_id=self.nidm_map, similarity_score=0.5,
            similarity_metric=Similarity.objects.create(similarity_metric="pearson", transformation="v"),
        )
        meta = apps.get_model("statmaps", "Metaanalysis").objects.create(owner=owner, name="m")
        meta.maps.add(self.statmap)
        self.meta = meta.pk

        perm, _ = Permission.objects.get_or_create(
            codename="change_basecollectionitem", content_type=ct["basecollectionitem"],
            defaults={"name": "x"},
        )
        UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
        UserObjectPermission.objects.create(
            user=owner, permission=perm, content_type=ct["basecollectionitem"], object_pk=str(self.statmap)
        )
        collection_perm, _ = Permission.objects.get_or_create(
            codename="change_collection", content_type=ContentType.objects.get_or_create(
                app_label="statmaps", model="collection")[0], defaults={"name": "y"},
        )
        UserObjectPermission.objects.create(
            user=owner, permission=collection_perm, content_type=collection_perm.content_type,
            object_pk=str(collection.pk),
        )

        executor = MigrationExecutor(connection)
        executor.migrate(AFTER)
        self.apps = executor.loader.project_state(AFTER + CONTEXT).apps

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.latest)

    def test_rows_kinds_and_columns(self):
        Item = self.apps.get_model("statmaps", "Item")
        kinds = dict(Item.objects.values_list("pk", "kind"))
        self.assertEqual(kinds, {self.statmap: "statmap", self.nidm_map: "statmap",
                                 self.atlas: "atlas", self.other: "other"})
        s = Item.objects.get(pk=self.statmap)
        self.assertEqual(
            (s.name, s.description, s.file, s.map_type, s.modality, s.analysis_level,
             s.number_of_subjects, s.cognitive_paradigm_cogatlas_id, s.data, s.thumbnail, s.age,
             s.source_bundle_id, s.ignore_file_warning),
            ("statmap", "d", "images/1/s.nii.gz", "T", "fMRI-BOLD", "G", 20, "trm_x",
             {"extra": "x"}, "images/1/glass_brain_1.jpg", 33.0, None, False),
        )
        self.assertNotEqual(s.perc_bad_voxels, s.perc_bad_voxels)  # NaN survives
        n = Item.objects.get(pk=self.nidm_map)
        self.assertEqual((n.map_type, n.source_bundle_id, n.modality, n.ignore_file_warning),
                         ("Z", self.bundle, None, None))
        a = Item.objects.get(pk=self.atlas)
        self.assertEqual((a.label_description_file, a.map_type), ("images/1/a.xml", None))
        bundle = self.apps.get_model("statmaps", "NIDMBundle").objects.get(pk=self.bundle)
        self.assertEqual((bundle.name, bundle.zip_file, bundle.ttl_file),
                         ("b.nidm", "images/1/b.nidm/b.nidm.zip", "images/1/b.nidm/nidm.ttl"))

    def test_references_tags_and_permissions(self):
        Comparison = self.apps.get_model("statmaps", "Comparison")
        c = Comparison.objects.get()
        self.assertEqual((c.image1_id, c.image2_id), (self.statmap, self.nidm_map))
        meta = self.apps.get_model("statmaps", "Metaanalysis").objects.get(pk=self.meta)
        self.assertEqual(list(meta.maps.values_list("pk", flat=True)), [self.statmap])

        ContentType = self.apps.get_model("contenttypes", "ContentType")
        Tagged = self.apps.get_model("statmaps", "ValueTaggedItem")
        tags = {(t.content_type.model, t.object_id, t.tag.name) for t in Tagged.objects.all()}
        self.assertEqual(tags, {("item", self.statmap, "visual"), ("item", self.atlas, "parc"),
                                ("nidmbundle", self.bundle, "nidm")})

        UserObjectPermission = self.apps.get_model("guardian", "UserObjectPermission")
        models = sorted(p.content_type.model for p in UserObjectPermission.objects.all())
        self.assertEqual(models, ["collection"])

    def test_new_ids_follow_the_old_ones(self):
        Item = self.apps.get_model("statmaps", "Item")
        Collection = self.apps.get_model("statmaps", "Collection")
        new = Item.objects.create(kind="other", name="new", collection=Collection.objects.get(),
                                  file="images/1/n.nii.gz")
        self.assertGreater(new.pk, max(self.statmap, self.nidm_map, self.atlas, self.other, self.bundle))
