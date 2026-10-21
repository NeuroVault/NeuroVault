"""Repositories over the Django ORM."""
from contextlib import contextmanager

from django.db import models, transaction
from django.db.models import Q

from neurovault.apps.statmaps import models as orm
from neurovault.domain import collection as dc
from neurovault.domain.errors import NotFound
from neurovault.domain.items import (
    Annotation,
    Atlas,
    CognitiveParadigm,
    CollectionItem,
    ImageFiles,
    ItemHeader,
    MapStats,
    NIDMBundle,
    NIDMProvenance,
    OtherImage,
    StatMap,
    SubjectInfo,
    TemplateSpace,
)
from neurovault.domain.metaanalysis import Metaanalysis

from .mapping import assign, flatten, names, read, value

HEADER_COLUMNS = ("collection_id", "name", "description", "is_valid")
IMAGE_GROUPS = (ImageFiles, TemplateSpace, SubjectInfo)
ANNOTATION_SCALARS = ("ignore_file_warning", "modality", "statistic_parameters", "smoothness_fwhm")


class DjangoUnitOfWork:
    def atomic(self):
        return transaction.atomic()

    def on_commit(self, fn):
        transaction.on_commit(fn)


def _save_row(obj):
    """Write a row without the models' own save() side effects."""
    if hasattr(obj, "pre_save_polymorphic"):
        obj.pre_save_polymorphic()
    models.Model.save(obj)


def _header(obj):
    return ItemHeader(
        id=obj.pk,
        collection_id=obj.collection_id,
        name=obj.name,
        description=obj.description,
        add_date=obj.add_date,
        modify_date=obj.modify_date,
        is_valid=obj.is_valid,
        tags=frozenset(obj.tags.names()) if obj.pk else frozenset(),
    )


def _write_header(obj, header):
    assign(obj, {c: getattr(header, c) for c in HEADER_COLUMNS})


# ------------------------------------------------------------------- items


def item_from_row(obj) -> CollectionItem:
    if isinstance(obj, orm.StatisticMap):
        payload = StatMap(
            stats=read(obj, MapStats),
            annotation=Annotation(
                **{n: getattr(obj, n) for n in ANNOTATION_SCALARS},
                paradigm=read(obj, CognitiveParadigm),
            ),
        )
    elif isinstance(obj, orm.NIDMResultStatisticMap):
        payload = StatMap(stats=read(obj, MapStats), source=NIDMProvenance(obj.nidm_results_id))
    elif isinstance(obj, orm.Atlas):
        payload = Atlas(label_description_file=value(obj, "label_description_file"))
    elif type(obj) is orm.Image:
        payload = OtherImage()
    else:
        raise TypeError("not an image: %r" % obj)
    return CollectionItem(
        header=_header(obj),
        files=read(obj, ImageFiles),
        space=read(obj, TemplateSpace),
        subject=read(obj, SubjectInfo),
        figure=obj.figure,
        data=obj.data,
        payload=payload,
    )


def row_class_for(item: CollectionItem):
    p = item.payload
    if isinstance(p, StatMap):
        return orm.StatisticMap if p.source is None else orm.NIDMResultStatisticMap
    if isinstance(p, Atlas):
        return orm.Atlas
    return orm.Image


def write_item(obj, item: CollectionItem):
    _write_header(obj, item.header)
    for vo in (item.files, item.space, item.subject):
        assign(obj, flatten(vo))
    obj.figure, obj.data = item.figure, item.data
    p = item.payload
    if isinstance(p, StatMap):
        assign(obj, flatten(p.stats))
        if p.annotation is not None:
            assign(obj, {n: getattr(p.annotation, n) for n in ANNOTATION_SCALARS})
            assign(obj, flatten(p.annotation.paradigm))
        else:
            obj.nidm_results_id = p.source.bundle_id
    elif isinstance(p, Atlas):
        obj.label_description_file = p.label_description_file


class DjangoItemRepository:
    def get(self, item_id):
        try:
            obj = orm.BaseCollectionItem.objects.get(pk=item_id)
        except orm.BaseCollectionItem.DoesNotExist:
            raise NotFound("item %s" % item_id)
        if isinstance(obj, orm.NIDMResults):
            raise NotFound("item %s is a bundle" % item_id)
        return item_from_row(obj)

    def add(self, item):
        obj = row_class_for(item)()
        write_item(obj, item)
        _save_row(obj)
        if item.header.tags:
            obj.tags.set(list(item.header.tags))
        item.header.id = obj.pk
        item.header.add_date, item.header.modify_date = obj.add_date, obj.modify_date
        return obj.pk

    def save(self, item):
        obj = orm.BaseCollectionItem.objects.get(pk=item.id)
        if type(obj) is not row_class_for(item):
            raise TypeError("an item cannot change kind")
        write_item(obj, item)
        _save_row(obj)
        obj.tags.set(list(item.header.tags))
        item.header.modify_date = obj.modify_date

    def delete(self, item_id):
        orm.BaseCollectionItem.objects.filter(pk=item_id).delete()

    def ids_in_collection(self, collection_id):
        return list(
            orm.Image.objects.filter(collection_id=collection_id).order_by("pk").values_list("pk", flat=True)
        )

    def ids_from_bundle(self, bundle_id):
        return list(
            orm.NIDMResultStatisticMap.objects.filter(nidm_results_id=bundle_id)
            .order_by("pk")
            .values_list("pk", flat=True)
        )

    def delete_comparisons(self, item_id):
        orm.Comparison.objects.filter(Q(image1_id=item_id) | Q(image2_id=item_id)).delete()


# ----------------------------------------------------------------- bundles


def bundle_from_row(obj) -> NIDMBundle:
    return NIDMBundle(
        header=_header(obj), zip_file=value(obj, "zip_file"), ttl_file=value(obj, "ttl_file")
    )


class DjangoBundleRepository:
    def get(self, bundle_id):
        try:
            return bundle_from_row(orm.NIDMResults.objects.get(pk=bundle_id))
        except orm.NIDMResults.DoesNotExist:
            raise NotFound("bundle %s" % bundle_id)

    def add(self, bundle):
        obj = orm.NIDMResults()
        self._write(obj, bundle)
        bundle.header.id = obj.pk
        return obj.pk

    def save(self, bundle):
        self._write(orm.NIDMResults.objects.get(pk=bundle.id), bundle)

    def _write(self, obj, bundle):
        _write_header(obj, bundle.header)
        obj.zip_file, obj.ttl_file = bundle.zip_file, bundle.ttl_file
        _save_row(obj)
        obj.tags.set(list(bundle.header.tags))
        bundle.header.add_date, bundle.header.modify_date = obj.add_date, obj.modify_date

    def delete(self, bundle_id):
        orm.NIDMResults.objects.filter(pk=bundle_id).delete()

    def ids_in_collection(self, collection_id):
        return list(
            orm.NIDMResults.objects.filter(collection_id=collection_id).order_by("pk").values_list("pk", flat=True)
        )

    def count_named_like(self, collection_id, prefix):
        return orm.NIDMResults.objects.filter(collection_id=collection_id, name__startswith=prefix).count()


# ------------------------------------------------------------- collections

COLLECTION_SCALARS = ("name", "description", "full_dataset_url", "private", "private_token")


def collection_from_row(obj) -> dc.Collection:
    groups = {attr: read(obj, cls) for attr, cls in dc.METADATA_GROUPS.items()}
    return dc.Collection(
        id=obj.pk,
        owner_id=obj.owner_id,
        contributor_ids=frozenset(obj.contributors.values_list("pk", flat=True)) if obj.pk else frozenset(),
        community_ids=frozenset(obj.communities.values_list("pk", flat=True)) if obj.pk else frozenset(),
        add_date=obj.add_date,
        modify_date=obj.modify_date,
        **{c: getattr(obj, c) for c in COLLECTION_SCALARS},
        **groups,
    )


def write_collection(obj, c: dc.Collection):
    obj.owner_id = c.owner_id
    assign(obj, {k: getattr(c, k) for k in COLLECTION_SCALARS})
    for attr in dc.METADATA_GROUPS:
        assign(obj, flatten(getattr(c, attr)))


class DjangoCollectionRepository:
    def get(self, collection_id):
        try:
            return collection_from_row(orm.Collection.objects.get(pk=collection_id))
        except (orm.Collection.DoesNotExist, ValueError):
            raise NotFound("collection %s" % collection_id)

    def find_by_token(self, token):
        obj = orm.Collection.objects.filter(private_token=token).first()
        return collection_from_row(obj) if obj else None

    def find_by_name(self, name):
        obj = orm.Collection.objects.filter(name=name).first()
        return collection_from_row(obj) if obj else None

    def add(self, c):
        obj = orm.Collection()
        write_collection(obj, c)
        models.Model.save(obj)
        c.id = obj.pk
        self._write_relations(obj, c)
        c.add_date, c.modify_date = obj.add_date, obj.modify_date
        return obj.pk

    def save(self, c):
        obj = orm.Collection.objects.get(pk=c.id)
        write_collection(obj, c)
        models.Model.save(obj)
        self._write_relations(obj, c)
        c.modify_date = obj.modify_date

    def _write_relations(self, obj, c):
        if set(obj.contributors.values_list("pk", flat=True)) != set(c.contributor_ids):
            obj.contributors.set(list(c.contributor_ids))
        if set(obj.communities.values_list("pk", flat=True)) != set(c.community_ids):
            obj.communities.set(list(c.community_ids))

    def delete(self, collection_id):
        orm.Collection.objects.filter(pk=collection_id).delete()

    def token_exists(self, token):
        return orm.Collection.objects.filter(private_token=token).exists()

    def touch(self, collection_id, when):
        obj = orm.Collection.objects.get(pk=collection_id)
        c = collection_from_row(obj)
        c.normalize(when)
        write_collection(obj, c)
        models.Model.save(obj)


# ----------------------------------------------------------- meta-analyses


def metaanalysis_from_row(obj) -> Metaanalysis:
    return Metaanalysis(
        id=obj.pk,
        owner_id=obj.owner_id,
        name=obj.name,
        description=obj.description,
        status=obj.status,
        map_ids=frozenset(obj.maps.values_list("pk", flat=True)) if obj.pk else frozenset(),
        output_collection_id=obj.output_maps_id,
    )


class DjangoMetaanalysisRepository:
    def get(self, metaanalysis_id):
        try:
            return metaanalysis_from_row(orm.Metaanalysis.objects.get(pk=metaanalysis_id))
        except orm.Metaanalysis.DoesNotExist:
            raise NotFound("metaanalysis %s" % metaanalysis_id)

    def add(self, m):
        obj = orm.Metaanalysis()
        self._write(obj, m)
        m.id = obj.pk
        return obj.pk

    def save(self, m):
        self._write(orm.Metaanalysis.objects.get(pk=m.id), m)

    def _write(self, obj, m):
        obj.owner_id, obj.name, obj.description = m.owner_id, m.name, m.description
        obj.status, obj.output_maps_id = m.status, m.output_collection_id
        models.Model.save(obj)
        if set(obj.maps.values_list("pk", flat=True)) != set(m.map_ids):
            obj.maps.set(list(m.map_ids))

    def active_for(self, owner_id):
        return [
            metaanalysis_from_row(o)
            for o in orm.Metaanalysis.objects.filter(owner_id=owner_id, status="active").order_by("pk")
        ]
