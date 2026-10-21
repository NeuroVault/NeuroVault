"""Collection items: images of any kind, and NIDM-Results bundles.

Composition replaces the old model inheritance: one `CollectionItem` carries a
payload (`StatMap`, `Atlas` or `OtherImage`). A statistic map that came out of
an NIDM-Results bundle differs from an uploaded one only by carrying
`NIDMProvenance` instead of an author `Annotation`.

Value-object field names equal the persistence column names, so the mapper in
the persistence adapter is generic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, fields, replace
from datetime import datetime
from typing import Optional, Union

from . import vocabulary as v

MapRef = str  # storage name of a file; "" or None means no file


@dataclass(frozen=True)
class ImageFiles:
    file: MapRef
    surface_left_file: Optional[MapRef] = None
    surface_right_file: Optional[MapRef] = None
    thumbnail: Optional[MapRef] = None
    reduced_representation: Optional[MapRef] = None

    def refs(self):
        return {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name)}


@dataclass(frozen=True)
class TemplateSpace:
    target_template_image: str = v.DEFAULT_TEMPLATE
    subject_species: Optional[str] = v.species_for(v.DEFAULT_TEMPLATE)
    data_origin: Optional[str] = "volume"


@dataclass(frozen=True)
class SubjectInfo:
    handedness: Optional[str] = None
    age: Optional[float] = None
    sex: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    BMI: Optional[float] = None
    fat_percentage: Optional[float] = None
    waist_hip_ratio: Optional[float] = None
    mean_PDS_score: Optional[float] = None
    tanner_stage: Optional[str] = None
    days_since_menstruation: Optional[float] = None
    hours_since_last_meal: Optional[float] = None
    bis_bas_score: Optional[float] = None
    bis11_score: Optional[float] = None
    spsrq_score: Optional[float] = None


@dataclass(frozen=True)
class MapStats:
    map_type: str = ""
    is_thresholded: Optional[bool] = None
    perc_bad_voxels: Optional[float] = None
    not_mni: Optional[bool] = None
    brain_coverage: Optional[float] = None
    perc_voxels_outside: Optional[float] = None
    analysis_level: Optional[str] = None
    number_of_subjects: Optional[int] = None


@dataclass(frozen=True)
class CognitiveParadigm:
    contrast_definition: Optional[str] = None
    contrast_definition_cogatlas: Optional[str] = None
    cognitive_paradigm_cogatlas_id: Optional[str] = None
    cognitive_contrast_cogatlas_id: Optional[str] = None
    cognitive_paradigm_description_url: Optional[str] = None
    cognitive_paradigm_short_description: Optional[str] = None
    cognitive_paradigm_name: Optional[str] = None


@dataclass(frozen=True)
class Annotation:
    """Author-supplied description of an uploaded map."""

    ignore_file_warning: bool = False
    modality: str = ""
    statistic_parameters: Optional[float] = None
    smoothness_fwhm: Optional[float] = None
    paradigm: CognitiveParadigm = field(default_factory=CognitiveParadigm)


@dataclass(frozen=True)
class NIDMProvenance:
    bundle_id: int


@dataclass(frozen=True)
class StatMap:
    stats: MapStats
    annotation: Optional[Annotation] = None
    source: Optional[NIDMProvenance] = None

    def __post_init__(self):
        if (self.annotation is None) == (self.source is None):
            raise ValueError("a StatMap has exactly one of annotation or source")

    @property
    def from_nidm(self):
        return self.source is not None


@dataclass(frozen=True)
class Atlas:
    label_description_file: MapRef


@dataclass(frozen=True)
class OtherImage:
    pass


Payload = Union[StatMap, Atlas, OtherImage]


@dataclass
class ItemHeader:
    """Fields every collection item has, image or bundle."""

    id: Optional[int]
    collection_id: int
    name: str
    description: str = ""
    add_date: Optional[datetime] = None
    modify_date: Optional[datetime] = None
    is_valid: bool = True
    tags: frozenset = field(default_factory=frozenset)


@dataclass
class CollectionItem:
    header: ItemHeader
    files: ImageFiles
    payload: Payload
    space: TemplateSpace = field(default_factory=TemplateSpace)
    subject: SubjectInfo = field(default_factory=SubjectInfo)
    figure: Optional[str] = None
    data: Optional[dict] = None

    @property
    def id(self):
        return self.header.id

    @property
    def collection_id(self):
        return self.header.collection_id

    @property
    def kind(self) -> str:
        return {StatMap: "statmap", Atlas: "atlas", OtherImage: "other"}[type(self.payload)]

    @property
    def is_statmap(self):
        return isinstance(self.payload, StatMap)

    @property
    def stats(self) -> Optional[MapStats]:
        return self.payload.stats if self.is_statmap else None

    def file_refs(self):
        refs = self.files.refs()
        if isinstance(self.payload, Atlas) and self.payload.label_description_file:
            refs["label_description_file"] = self.payload.label_description_file
        return refs

    def with_stats(self, **changes):
        self.payload = replace(self.payload, stats=replace(self.payload.stats, **changes))

    def with_files(self, **changes):
        self.files = replace(self.files, **changes)

    def with_space(self, **changes):
        self.space = replace(self.space, **changes)

    def ensure_species(self):
        """Infer the subject species from the template when it is unknown."""
        if self.space.subject_species is None and self.space.target_template_image:
            self.with_space(subject_species=v.species_for(self.space.target_template_image))


@dataclass
class NIDMBundle:
    header: ItemHeader
    zip_file: MapRef
    ttl_file: Optional[MapRef] = None

    @property
    def id(self):
        return self.header.id

    @property
    def collection_id(self):
        return self.header.collection_id

    def file_refs(self):
        return {k: getattr(self, k) for k in ("zip_file", "ttl_file") if getattr(self, k)}


HEADER_FIELDS = ("collection_id", "name", "description", "is_valid")
ITEM_SCALARS = ("figure", "data")
ANNOTATION_SCALARS = ("ignore_file_warning", "modality", "statistic_parameters", "smoothness_fwhm")
FILE_FIELDS = tuple(f.name for f in fields(ImageFiles)) + ("label_description_file",)


def _names(cls):
    return {f.name for f in fields(cls)}


IMAGE_COLUMNS = frozenset(
    set(HEADER_FIELDS) | set(ITEM_SCALARS) | _names(TemplateSpace) | _names(SubjectInfo)
    | _names(ImageFiles)
)


def column_names(kind, from_nidm=False):
    """Every column name `apply_changes` accepts for an item of `kind`."""
    names = set(IMAGE_COLUMNS)
    if kind == "statmap":
        names |= _names(MapStats)
        if not from_nidm:
            names |= set(ANNOTATION_SCALARS) | _names(CognitiveParadigm)
    if kind == "atlas":
        names.add("label_description_file")
    return names


def apply_changes(item: CollectionItem, changes: dict):
    """Set fields of `item` by column name; unknown names raise KeyError."""
    allowed = column_names(item.kind, item.is_statmap and item.payload.from_nidm)
    unknown = set(changes) - allowed
    if unknown:
        raise KeyError("not columns of a %s: %s" % (item.kind, sorted(unknown)))

    def pick(cls):
        return {k: v for k, v in changes.items() if k in _names(cls)}

    for k in HEADER_FIELDS:
        if k in changes:
            setattr(item.header, k, changes[k])
    for k in ITEM_SCALARS:
        if k in changes:
            setattr(item, k, changes[k])
    if pick(ImageFiles):
        item.files = replace(item.files, **pick(ImageFiles))
    if pick(TemplateSpace):
        item.space = replace(item.space, **pick(TemplateSpace))
    if pick(SubjectInfo):
        item.subject = replace(item.subject, **pick(SubjectInfo))
    p = item.payload
    if isinstance(p, StatMap):
        stats = replace(p.stats, **pick(MapStats))
        annotation = p.annotation
        if annotation is not None:
            scalars = {k: changes[k] for k in ANNOTATION_SCALARS if k in changes}
            paradigm = replace(annotation.paradigm, **pick(CognitiveParadigm))
            annotation = replace(annotation, paradigm=paradigm, **scalars)
        item.payload = replace(p, stats=stats, annotation=annotation)
    elif isinstance(p, Atlas) and "label_description_file" in changes:
        item.payload = Atlas(changes["label_description_file"])


def new_item(kind, collection_id, changes=None, bundle_id=None):
    """A new, unsaved item with the persistence defaults, then `changes`."""
    if kind == "statmap":
        if bundle_id is None:
            payload = StatMap(stats=MapStats(), annotation=Annotation())
        else:
            payload = StatMap(stats=MapStats(), source=NIDMProvenance(bundle_id))
    elif kind == "atlas":
        payload = Atlas(label_description_file="")
    elif kind == "other":
        payload = OtherImage()
    else:
        raise ValueError(kind)
    item = CollectionItem(
        header=ItemHeader(id=None, collection_id=collection_id, name=""),
        files=ImageFiles(file=""),
        payload=payload,
    )
    apply_changes(item, dict(changes or {}))
    return item


def legacy_image_type(item: Union[CollectionItem, NIDMBundle]) -> Optional[str]:
    """The `image_type` string the public API has always emitted."""
    if isinstance(item, NIDMBundle):
        return "NIDM Results"
    payload = item.payload
    if isinstance(payload, Atlas):
        return "atlas"
    if isinstance(payload, StatMap):
        return "statistic_map" if payload.source is None else "NIDM results statistic map"
    return None


def same_value(a, b):
    """Equality that treats NaN as equal to NaN (stored QA metrics can be NaN)."""
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b
