"""The polymorphic-to-Item migration (0007_move_items) on one row of every kind.

The local development data only contains statistic maps, so this covers the
other kinds, tags, comparisons, meta-analysis selections, permissions, the
pre-flight checks and the reverse (a round trip back to 0005).
"""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("statmaps", "0005_alter_basecollectionitem_modify_date")]
AFTER = [("statmaps", "0007_move_items")]
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
        self.owner = owner.pk
        collection = Collection.objects.create(name="c", owner=owner)
        self.contributor = User.objects.create(username="contrib").pk
        collection.contributors.add(self.contributor)
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

        self.before_apps = apps

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets + CONTEXT).apps

    def forward(self):
        self.apps = self.migrate(AFTER)

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.latest)

    def test_rows_kinds_and_columns(self):
        self.forward()
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
        self.forward()
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

    def test_new_ids_follow_the_old_ones_in_one_id_space(self):
        self.forward()
        Item = self.apps.get_model("statmaps", "Item")
        Bundle = self.apps.get_model("statmaps", "NIDMBundle")
        Collection = self.apps.get_model("statmaps", "Collection")
        collection = Collection.objects.get()
        item = Item.objects.create(kind="other", name="new", collection=collection, file="images/1/n.nii.gz")
        bundle = Bundle.objects.create(name="new.nidm", collection=collection, zip_file="images/1/x.zip")
        old = max(self.statmap, self.nidm_map, self.atlas, self.other, self.bundle)
        self.assertGreater(min(item.pk, bundle.pk), old)
        self.assertNotEqual(item.pk, bundle.pk)

    def test_round_trip_back_to_0005_restores_everything(self):
        self.forward()
        apps = self.migrate(BEFORE)
        ct = lambda pk: apps.get_model("statmaps", "BaseCollectionItem").objects.get(pk=pk).polymorphic_ctype.model
        self.assertEqual(
            {pk: ct(pk) for pk in (self.statmap, self.nidm_map, self.atlas, self.other, self.bundle)},
            {self.statmap: "statisticmap", self.nidm_map: "nidmresultstatisticmap", self.atlas: "atlas",
             self.other: "image", self.bundle: "nidmresults"},
        )
        s = apps.get_model("statmaps", "StatisticMap").objects.get(pk=self.statmap)
        self.assertEqual((s.name, s.map_type, s.modality, s.cognitive_paradigm_cogatlas_id, s.data, s.age),
                         ("statmap", "T", "fMRI-BOLD", "trm_x", {"extra": "x"}, 33.0))
        self.assertNotEqual(s.perc_bad_voxels, s.perc_bad_voxels)
        n = apps.get_model("statmaps", "NIDMResultStatisticMap").objects.get(pk=self.nidm_map)
        self.assertEqual((n.map_type, n.nidm_results_id), ("Z", self.bundle))
        a = apps.get_model("statmaps", "Atlas").objects.get(pk=self.atlas)
        self.assertEqual(a.label_description_file, "images/1/a.xml")
        r = apps.get_model("statmaps", "NIDMResults").objects.get(pk=self.bundle)
        self.assertEqual(r.zip_file, "images/1/b.nidm/b.nidm.zip")

        c = apps.get_model("statmaps", "Comparison").objects.get()
        self.assertEqual((c.image1_id, c.image2_id), (self.statmap, self.nidm_map))
        meta = apps.get_model("statmaps", "Metaanalysis").objects.get(pk=self.meta)
        self.assertEqual(list(meta.maps.values_list("pk", flat=True)), [self.statmap])
        Tagged = apps.get_model("statmaps", "ValueTaggedItem")
        self.assertEqual(
            {(t.content_type.model, t.object_id) for t in Tagged.objects.all()},
            {("statisticmap", self.statmap), ("atlas", self.atlas), ("nidmresults", self.bundle)},
        )
        UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
        item_perms = {
            (p.user_id, p.permission.codename, int(p.object_pk))
            for p in UserObjectPermission.objects.filter(content_type__model="basecollectionitem")
        }
        expected = {
            (user, codename, pk)
            for user in (self.owner, self.contributor)
            for codename in ("change_basecollectionitem", "delete_basecollectionitem")
            for pk in (self.statmap, self.nidm_map, self.atlas, self.other, self.bundle)
        }
        self.assertEqual(item_perms, expected)
        # and forward again from the restored data
        self.apps = self.migrate(AFTER)
        self.assertEqual(self.apps.get_model("statmaps", "Item").objects.count(), 4)

    def test_preflight_aborts_on_an_orphaned_item_row(self):
        Base = self.before_apps.get_model("statmaps", "BaseCollectionItem")
        orphan = Base.objects.create(name="orphan", collection_id=self.before_apps.get_model(
            "statmaps", "Collection").objects.get().pk, polymorphic_ctype_id=None)
        with self.assertRaisesRegex(RuntimeError, "no image or NIDM child"):
            self.migrate(AFTER)
        # nothing was moved: the old tables are still there and intact
        apps = self.migrate(BEFORE)
        self.assertEqual(apps.get_model("statmaps", "Image").objects.count(), 4)
        Base.objects.filter(pk=orphan.pk).delete()  # so tearDown can migrate forward
