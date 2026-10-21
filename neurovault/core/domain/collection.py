"""The Collection aggregate.

A collection's study metadata is grouped into value objects that follow the
sections of the collection form. Field names equal the persistence column
names, so the mapper in the persistence adapter is generic.
"""
from __future__ import annotations

import random
import string
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Callable, Optional

from .errors import DomainValidationError


@dataclass(frozen=True)
class Publication:
    publication_status: Optional[str] = None
    DOI: Optional[str] = None
    preprint_DOI: Optional[str] = None
    authors: Optional[str] = None
    paper_url: Optional[str] = None
    journal_name: Optional[str] = None
    doi_add_date: Optional[datetime] = None


@dataclass(frozen=True)
class Participants:
    subject_age_mean: Optional[float] = None
    subject_age_min: Optional[float] = None
    subject_age_max: Optional[float] = None
    handedness: Optional[str] = None
    proportion_male_subjects: Optional[float] = None
    inclusion_exclusion_criteria: Optional[str] = None
    number_of_rejected_subjects: Optional[int] = None
    group_comparison: Optional[bool] = None
    group_description: Optional[str] = None


@dataclass(frozen=True)
class Design:
    type_of_design: Optional[str] = None
    number_of_imaging_runs: Optional[int] = None
    number_of_experimental_units: Optional[int] = None
    length_of_runs: Optional[float] = None
    length_of_blocks: Optional[float] = None
    length_of_trials: Optional[str] = None
    optimization: Optional[bool] = None
    optimization_method: Optional[str] = None


@dataclass(frozen=True)
class Acquisition:
    scanner_make: Optional[str] = None
    scanner_model: Optional[str] = None
    field_strength: Optional[float] = None
    pulse_sequence: Optional[str] = None
    parallel_imaging: Optional[str] = None
    field_of_view: Optional[float] = None
    matrix_size: Optional[int] = None
    slice_thickness: Optional[float] = None
    skip_distance: Optional[float] = None
    acquisition_orientation: Optional[str] = None
    order_of_acquisition: Optional[str] = None
    repetition_time: Optional[float] = None
    echo_time: Optional[float] = None
    flip_angle: Optional[float] = None


@dataclass(frozen=True)
class Registration:
    used_intersubject_registration: Optional[bool] = None
    intersubject_registration_software: Optional[str] = None
    intersubject_transformation_type: Optional[str] = None
    nonlinear_transform_type: Optional[str] = None
    transform_similarity_metric: Optional[str] = None
    interpolation_method: Optional[str] = None
    object_image_type: Optional[str] = None
    functional_coregistered_to_structural: Optional[bool] = None
    functional_coregistration_method: Optional[str] = None
    coordinate_space: Optional[str] = None
    target_template_image: Optional[str] = None
    target_resolution: Optional[float] = None
    used_smoothing: Optional[bool] = None
    smoothing_type: Optional[str] = None
    smoothing_fwhm: Optional[float] = None
    resampled_voxel_size: Optional[float] = None


@dataclass(frozen=True)
class Preprocessing:
    software_package: Optional[str] = None
    software_version: Optional[str] = None
    order_of_preprocessing_operations: Optional[str] = None
    quality_control: Optional[str] = None
    used_b0_unwarping: Optional[bool] = None
    b0_unwarping_software: Optional[str] = None
    used_slice_timing_correction: Optional[bool] = None
    slice_timing_correction_software: Optional[str] = None
    used_motion_correction: Optional[bool] = None
    motion_correction_software: Optional[str] = None
    motion_correction_reference: Optional[str] = None
    motion_correction_metric: Optional[str] = None
    motion_correction_interpolation: Optional[str] = None
    used_motion_susceptibiity_correction: Optional[bool] = None


@dataclass(frozen=True)
class FirstLevel:
    intrasubject_model_type: Optional[str] = None
    intrasubject_estimation_type: Optional[str] = None
    intrasubject_modeling_software: Optional[str] = None
    hemodynamic_response_function: Optional[str] = None
    used_temporal_derivatives: Optional[bool] = None
    used_dispersion_derivatives: Optional[bool] = None
    used_motion_regressors: Optional[bool] = None
    used_reaction_time_regressor: Optional[bool] = None
    used_orthogonalization: Optional[bool] = None
    orthogonalization_description: Optional[str] = None
    used_high_pass_filter: Optional[bool] = None
    high_pass_filter_method: Optional[str] = None
    autocorrelation_model: Optional[str] = None


@dataclass(frozen=True)
class GroupLevel:
    group_model_type: Optional[str] = None
    group_estimation_type: Optional[str] = None
    group_modeling_software: Optional[str] = None
    group_inference_type: Optional[str] = None
    group_model_multilevel: Optional[str] = None
    group_repeated_measures: Optional[bool] = None
    group_repeated_measures_method: Optional[str] = None


@dataclass(frozen=True)
class Nutritional:
    nutbrain_hunger_state: Optional[str] = None
    nutbrain_food_viewing_conditions: Optional[str] = None
    nutbrain_food_choice_type: Optional[str] = None
    nutbrain_taste_conditions: Optional[str] = None
    nutbrain_odor_conditions: Optional[str] = None


METADATA_GROUPS = {
    "publication": Publication,
    "participants": Participants,
    "design": Design,
    "acquisition": Acquisition,
    "registration": Registration,
    "preprocessing": Preprocessing,
    "first_level": FirstLevel,
    "group_level": GroupLevel,
    "nutritional": Nutritional,
}
SCALARS = ("name", "description", "full_dataset_url", "private", "private_token")


def group_of(field_name):
    for attr, cls in METADATA_GROUPS.items():
        if field_name in {f.name for f in fields(cls)}:
            return attr
    return None


def generate_token(exists: Callable[[str], bool], length=8):
    """A random upper-case token that `exists` reports as unused."""
    while True:
        token = "".join(random.choice(string.ascii_uppercase) for _ in range(length))
        if not exists(token):
            return token


@dataclass
class Collection:
    id: Optional[int]
    owner_id: Optional[int]
    name: Optional[str]
    description: Optional[str] = None
    full_dataset_url: Optional[str] = None
    private: bool = False
    private_token: Optional[str] = None
    contributor_ids: frozenset = field(default_factory=frozenset)
    community_ids: frozenset = field(default_factory=frozenset)
    add_date: Optional[datetime] = None
    modify_date: Optional[datetime] = None
    publication: Publication = field(default_factory=Publication)
    participants: Participants = field(default_factory=Participants)
    design: Design = field(default_factory=Design)
    acquisition: Acquisition = field(default_factory=Acquisition)
    registration: Registration = field(default_factory=Registration)
    preprocessing: Preprocessing = field(default_factory=Preprocessing)
    first_level: FirstLevel = field(default_factory=FirstLevel)
    group_level: GroupLevel = field(default_factory=GroupLevel)
    nutritional: Nutritional = field(default_factory=Nutritional)

    @property
    def DOI(self):
        return self.publication.DOI

    def get(self, field_name):
        if field_name in SCALARS:
            return getattr(self, field_name)
        group = group_of(field_name)
        if group is None:
            raise KeyError(field_name)
        return getattr(getattr(self, group), field_name)

    def apply(self, changes: dict):
        """Set scalar and metadata fields by column name."""
        by_group = {}
        for key, value in changes.items():
            if key in SCALARS:
                setattr(self, key, value)
                continue
            group = group_of(key)
            if group is None:
                raise KeyError(key)
            by_group.setdefault(group, {})[key] = value
        for group, values in by_group.items():
            current = getattr(self, group)
            setattr(self, group, type(current)(**{**current.__dict__, **values}))

    def normalize(self, now: datetime):
        """Rules applied on every save (blank DOI/token become None, DOI date)."""
        doi = self.publication.DOI
        if doi is not None and doi.strip() == "":
            self.apply({"DOI": None})
        if self.private_token is not None and self.private_token.strip() == "":
            self.private_token = None
        if self.publication.DOI and not self.private and not self.publication.doi_add_date:
            self.apply({"doi_add_date": now})

    def ensure_token(self, exists: Callable[[str], bool]):
        if self.private and self.private_token is None:
            self.private_token = generate_token(exists)

    def require_name_or_doi(self):
        if not self.publication.DOI and not self.name:
            msg = ["You need to set the name or the DOI"]
            raise DomainValidationError({"name": msg, "DOI": msg})

    def is_member(self, user_id):
        return user_id is not None and (user_id == self.owner_id or user_id in self.contributor_ids)
