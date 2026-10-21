# -*- coding: utf-8 -*-
"""Persistence records. Rules and side effects live in neurovault.core.application."""
import os
import uuid

from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, TagBase

from neurovault.adapters.persistence.storage import (
    DoubleExtensionStorage,
    NIDMStorage,
    OverwriteStorage,
)
from neurovault.core.domain import vocabulary

POSSIBLE_TEMPLATES = vocabulary.POSSIBLE_TEMPLATES
DEFAULT_TEMPLATE = vocabulary.DEFAULT_TEMPLATE
COMMUNITIES = vocabulary.COMMUNITIES


def get_possible_templates():
    return POSSIBLE_TEMPLATES


def get_target_template_list():
    return vocabulary.target_template_choices()


community_choices = []
for k in list(COMMUNITIES.keys()):
    community_choices.append((k, COMMUNITIES[k]["short_desc"]))


class Community(models.Model):
    label = models.CharField(
        max_length=200,
        unique=True,
        null=False,
        verbose_name="Lexical label of the community",
    )
    short_desc = models.CharField(
        max_length=200, null=False, verbose_name="Short description of the community"
    )

    def __str__(self):
        return self.short_desc

    def __unicode__(self):
        return self.short_desc


class Collection(models.Model):
    name = models.CharField(
        max_length=200, unique=True, null=False, verbose_name="Name of collection"
    )
    publication_status = models.CharField(
        choices=[
            ("published", "Yes"),
            ("submitted", "Submitted"),
            ("in_preparation", "In Preparation"),
            ("not_intended", "No"),
        ],
        help_text="Is this collection associated with an existing, or planned publication?",
        null=True,
        verbose_name="Publication?",
        blank=True,
    )
    DOI = models.CharField(
        max_length=200,
        unique=True,
        blank=True,
        null=True,
        default=None,
        verbose_name="Publication DOI",
        help_text="Required for published collections.",
    )
    preprint_DOI = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default=None,
        verbose_name="Preprint DOI",
        help_text="If there is not yet a publication, it is highly encouraged to provide a preprint DOI",
    )
    authors = models.CharField(max_length=5000, blank=True, null=True)
    paper_url = models.CharField(max_length=200, blank=True, null=True)
    journal_name = models.CharField(max_length=200, blank=True, null=True, default=None)
    description = models.TextField(blank=True, null=True)
    full_dataset_url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Full dataset URL",
        help_text='Link to an external dataset the maps in this collection have been generated from (for example: "https://openfmri.org/dataset/ds000001" or "http://dx.doi.org/10.15387/fcp_indi.corr.mpg1")',
    )
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    contributors = models.ManyToManyField(
        User,
        related_name="collection_contributors",
        related_query_name="contributor",
        blank=True,
        help_text="Select other NeuroVault users to add as contributes to the collection.  Contributors can add, edit and delete images in the collection.",
        verbose_name="Contributors",
    )
    private = models.BooleanField(
        choices=(
            (
                False,
                "Public",
            ),
            (
                True,
                "Private",
            ),
        ),
        default=False,
        help_text="Public collections distributed under CC0 license. Private collections are not publicly indexed, but can be shared using a private URL.",
        verbose_name="Accessibility",
    )
    private_token = models.CharField(
        max_length=8, blank=True, null=True, unique=True, db_index=True, default=None
    )
    add_date = models.DateTimeField("date published", auto_now_add=True)
    modify_date = models.DateTimeField("date modified", auto_now=True)
    doi_add_date = models.DateTimeField(
        "date the DOI was added", editable=False, blank=True, null=True, db_index=True
    )
    communities = models.ManyToManyField(
        Community,
        related_name="collections",
        related_query_name="collection",
        blank=True,
        help_text="Is this collection part of any special Community?",
        verbose_name="Communities",
        default=None,
    )

    type_of_design = models.CharField(
        choices=[
            ("blocked", "blocked"),
            ("eventrelated", "event_related"),
            ("hybridblockevent", "hybrid block/event"),
            ("other", "other"),
        ],
        max_length=200,
        blank=True,
        help_text="Blocked, event-related, hybrid, or other",
        null=True,
        verbose_name="Type of design",
    )
    number_of_imaging_runs = models.IntegerField(
        help_text="Number of imaging runs acquired",
        null=True,
        verbose_name="No. of imaging runs",
        blank=True,
    )
    number_of_experimental_units = models.IntegerField(
        help_text="Number of blocks, trials or experimental units per imaging run",
        null=True,
        verbose_name="No. of experimental units",
        blank=True,
    )
    length_of_runs = models.FloatField(
        help_text="Length of each imaging run in seconds",
        null=True,
        verbose_name="Length of runs",
        blank=True,
    )
    length_of_blocks = models.FloatField(
        help_text="For blocked designs, length of blocks in seconds",
        null=True,
        verbose_name="Length of blocks",
        blank=True,
    )
    length_of_trials = models.CharField(
        help_text="Length of individual trials in seconds. If length varies across trials, enter 'variable'. ",
        max_length=200,
        null=True,
        verbose_name="Length of trials",
        blank=True,
    )
    optimization = models.BooleanField(
        help_text="Was the design optimized for efficiency",
        null=True,
        verbose_name="Optimization?",
        blank=True,
    )
    optimization_method = models.CharField(
        help_text="What method was used for optimization?",
        verbose_name="Optimization method",
        max_length=200,
        null=True,
        blank=True,
    )
    subject_age_mean = models.FloatField(
        help_text="Mean age of subjects",
        null=True,
        verbose_name="Subject age mean",
        blank=True,
    )
    subject_age_min = models.FloatField(
        help_text="Minimum age of subjects",
        null=True,
        verbose_name="Subject age min",
        blank=True,
    )
    subject_age_max = models.FloatField(
        help_text="Maximum age of subjects",
        null=True,
        verbose_name="Subject age max",
        blank=True,
    )
    handedness = models.CharField(
        choices=[("right", "right"), ("left", "left"), ("both", "both")],
        max_length=200,
        blank=True,
        help_text="Handedness of subjects",
        null=True,
        verbose_name="Handedness",
    )
    proportion_male_subjects = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="The proportion (not percentage) of subjects who were male",
        null=True,
        verbose_name="Prop. male subjects",
        blank=True,
    )
    inclusion_exclusion_criteria = models.CharField(
        help_text="Additional inclusion/exclusion criteria, if any (including specific sampling strategies that limit inclusion to a specific group, such as laboratory members)",
        verbose_name="Inclusion / exclusion criteria",
        max_length=200,
        null=True,
        blank=True,
    )
    number_of_rejected_subjects = models.IntegerField(
        help_text="Number of subjects scanned but rejected from analysis",
        null=True,
        verbose_name="No. of rejected subjects",
        blank=True,
    )
    group_comparison = models.BooleanField(
        help_text="Was this study a comparison between subject groups?",
        null=True,
        verbose_name="Group comparison?",
        blank=True,
    )
    group_description = models.CharField(
        help_text="A description of the groups being compared",
        verbose_name="Group description",
        max_length=200,
        null=True,
        blank=True,
    )
    scanner_make = models.CharField(
        help_text="Manufacturer of MRI scanner",
        verbose_name="Scanner make",
        max_length=200,
        null=True,
        blank=True,
    )
    scanner_model = models.CharField(
        help_text="Model of MRI scanner",
        verbose_name="Scanner model",
        max_length=200,
        null=True,
        blank=True,
    )
    field_strength = models.FloatField(
        help_text="Field strength of MRI scanner (in Tesla)",
        null=True,
        verbose_name="Field strength",
        blank=True,
    )
    pulse_sequence = models.CharField(
        help_text="Description of pulse sequence used for fMRI",
        verbose_name="Pulse sequence",
        max_length=200,
        null=True,
        blank=True,
    )
    parallel_imaging = models.CharField(
        help_text="Description of parallel imaging method and parameters",
        verbose_name="Parallel imaging",
        max_length=200,
        null=True,
        blank=True,
    )
    field_of_view = models.FloatField(
        help_text="Imaging field of view in millimeters",
        null=True,
        verbose_name="Field of view",
        blank=True,
    )
    matrix_size = models.IntegerField(
        help_text="Matrix size for MRI acquisition",
        null=True,
        verbose_name="Matrix size",
        blank=True,
    )
    slice_thickness = models.FloatField(
        help_text="Distance between slices (includes skip or distance factor) in millimeters",
        null=True,
        verbose_name="Slice thickness",
        blank=True,
    )
    skip_distance = models.FloatField(
        help_text="The size of the skipped area between slices in millimeters",
        null=True,
        verbose_name="Skip distance",
        blank=True,
    )
    acquisition_orientation = models.CharField(
        help_text="The orientation of slices",
        verbose_name="Acquisition orientation",
        max_length=200,
        null=True,
        blank=True,
    )
    order_of_acquisition = models.CharField(
        choices=[
            ("ascending", "ascending"),
            ("descending", "descending"),
            ("interleaved", "interleaved"),
        ],
        max_length=200,
        blank=True,
        help_text="Order of acquisition of slices (ascending, descending, or interleaved)",
        null=True,
        verbose_name="Order of acquisition",
    )
    repetition_time = models.FloatField(
        help_text="Repetition time (TR) in milliseconds",
        null=True,
        verbose_name="Repetition time",
        blank=True,
    )
    echo_time = models.FloatField(
        help_text="Echo time (TE) in milliseconds",
        null=True,
        verbose_name="Echo time",
        blank=True,
    )
    flip_angle = models.FloatField(
        help_text="Flip angle in degrees",
        null=True,
        verbose_name="Flip angle",
        blank=True,
    )
    software_package = models.CharField(
        help_text="If a single software package was used for all analyses, specify that here",
        verbose_name="Software package",
        max_length=200,
        null=True,
        blank=True,
    )
    software_version = models.CharField(
        help_text="Version of software package used",
        verbose_name="Software version",
        max_length=200,
        null=True,
        blank=True,
    )
    order_of_preprocessing_operations = models.CharField(
        help_text="Specify order of preprocessing operations",
        verbose_name="Order of preprocessing",
        max_length=200,
        null=True,
        blank=True,
    )
    quality_control = models.CharField(
        help_text="Describe quality control measures",
        verbose_name="Quality control",
        max_length=200,
        null=True,
        blank=True,
    )
    used_b0_unwarping = models.BooleanField(
        help_text="Was B0 distortion correction used?",
        null=True,
        verbose_name="Used B0 unwarping?",
        blank=True,
    )
    b0_unwarping_software = models.CharField(
        help_text="Specify software used for distortion correction if different from the main package",
        verbose_name="B0 unwarping software",
        max_length=200,
        null=True,
        blank=True,
    )
    used_slice_timing_correction = models.BooleanField(
        help_text="Was slice timing correction used?",
        null=True,
        verbose_name="Slice timing correction?",
        blank=True,
    )
    slice_timing_correction_software = models.CharField(
        help_text="Specify software used for slice timing correction if different from the main package",
        verbose_name="Slice timing correction software",
        max_length=200,
        null=True,
        blank=True,
    )
    used_motion_correction = models.BooleanField(
        help_text="Was motion correction used?",
        null=True,
        verbose_name="Motion correction?",
        blank=True,
    )
    motion_correction_software = models.CharField(
        help_text="Specify software used for motion correction if different from the main package",
        verbose_name="Motion correction software",
        max_length=200,
        null=True,
        blank=True,
    )
    motion_correction_reference = models.CharField(
        help_text="Reference scan used for motion correction",
        verbose_name="Motion correction reference",
        max_length=200,
        null=True,
        blank=True,
    )
    motion_correction_metric = models.CharField(
        help_text="Similarity metric used for motion correction",
        verbose_name="Motion correction metric",
        max_length=200,
        null=True,
        blank=True,
    )
    motion_correction_interpolation = models.CharField(
        help_text="Interpolation method used for motion correction",
        verbose_name="Motion correction interpolation",
        max_length=200,
        null=True,
        blank=True,
    )
    used_motion_susceptibiity_correction = models.BooleanField(
        help_text="Was motion-susceptibility correction used?",
        null=True,
        verbose_name="Motion susceptibility correction?",
        blank=True,
    )
    used_intersubject_registration = models.BooleanField(
        help_text="Were subjects registered to a common stereotactic space?",
        null=True,
        verbose_name="Intersubject registration?",
        blank=True,
    )
    intersubject_registration_software = models.CharField(
        help_text="Specify software used for intersubject registration if different from main package",
        verbose_name="Registration software",
        max_length=200,
        null=True,
        blank=True,
    )
    intersubject_transformation_type = models.CharField(
        choices=[("linear", "linear"), ("nonlinear", "nonlinear")],
        max_length=200,
        blank=True,
        help_text="Was linear or nonlinear registration used?",
        null=True,
        verbose_name="Intersubject transformation type",
    )
    nonlinear_transform_type = models.CharField(
        help_text="If nonlinear registration was used, describe transform method",
        verbose_name="Nonlinear transform type",
        max_length=200,
        null=True,
        blank=True,
    )
    transform_similarity_metric = models.CharField(
        help_text="Similarity metric used for intersubject registration",
        verbose_name="Transform similarity metric",
        max_length=200,
        null=True,
        blank=True,
    )
    interpolation_method = models.CharField(
        help_text="Interpolation method used for intersubject registration",
        verbose_name="Interpolation method",
        max_length=200,
        null=True,
        blank=True,
    )
    object_image_type = models.CharField(
        help_text="What type of image was used to determine the transformation to the atlas? (e.g. T1, T2, EPI)",
        verbose_name="Object image type",
        max_length=200,
        null=True,
        blank=True,
    )
    functional_coregistered_to_structural = models.BooleanField(
        help_text="Were the functional images coregistered to the subject's structural image?",
        null=True,
        verbose_name="Coregistered to structural?",
        blank=True,
    )
    functional_coregistration_method = models.CharField(
        help_text="Method used to coregister functional to structural images",
        verbose_name="Coregistration method",
        max_length=200,
        null=True,
        blank=True,
    )
    coordinate_space = models.CharField(
        choices=[
            ("mni", "MNI"),
            ("talairach", "Talairach"),
            ("mni2tal", "MNI2Tal"),
            ("other", "other"),
        ],
        max_length=200,
        blank=True,
        help_text="Name of coordinate space for registration target",
        null=True,
        verbose_name="Coordinate space",
    )
    target_template_image = models.CharField(
        help_text="Name of target template image",
        verbose_name="Target template image",
        max_length=200,
        null=True,
        blank=True,
    )
    target_resolution = models.FloatField(
        help_text="Voxel size of target template in millimeters",
        null=True,
        verbose_name="Target resolution",
        blank=True,
    )
    used_smoothing = models.BooleanField(
        help_text="Was spatial smoothing applied?",
        null=True,
        verbose_name="Used smoothing?",
        blank=True,
    )
    smoothing_type = models.CharField(
        help_text="Describe the type of smoothing applied",
        verbose_name="Type of smoothing",
        max_length=200,
        null=True,
        blank=True,
    )
    smoothing_fwhm = models.FloatField(
        help_text="The full-width at half-maximum of the smoothing kernel in millimeters",
        null=True,
        verbose_name="Smoothing FWHM",
        blank=True,
    )
    resampled_voxel_size = models.FloatField(
        help_text="Voxel size in mm of the resampled, atlas-space images",
        null=True,
        verbose_name="Resampled voxel size",
        blank=True,
    )
    intrasubject_model_type = models.CharField(
        help_text="Type of model used (e.g., regression)",
        verbose_name="Model type",
        max_length=200,
        null=True,
        blank=True,
    )
    intrasubject_estimation_type = models.CharField(
        help_text="Estimation method used for model (e.g., OLS, generalized least squares)",
        verbose_name="Estimation type",
        max_length=200,
        null=True,
        blank=True,
    )
    intrasubject_modeling_software = models.CharField(
        help_text="Software used for intrasubject modeling if different from overall package",
        verbose_name="Modeling software",
        max_length=200,
        null=True,
        blank=True,
    )
    hemodynamic_response_function = models.CharField(
        help_text="Nature of HRF model",
        verbose_name="Hemodynamic response function",
        max_length=200,
        null=True,
        blank=True,
    )
    used_temporal_derivatives = models.BooleanField(
        help_text="Were temporal derivatives included?",
        null=True,
        verbose_name="Temporal derivatives?",
        blank=True,
    )
    used_dispersion_derivatives = models.BooleanField(
        help_text="Were dispersion derivatives included?",
        null=True,
        verbose_name="Dispersion derivatives?",
        blank=True,
    )
    used_motion_regressors = models.BooleanField(
        help_text="Were motion regressors included?",
        null=True,
        verbose_name="Motion regressors?",
        blank=True,
    )
    used_reaction_time_regressor = models.BooleanField(
        help_text="Was a reaction time regressor included?",
        null=True,
        verbose_name="Reaction time regressor?",
        blank=True,
    )
    used_orthogonalization = models.BooleanField(
        help_text="Were any regressors specifically orthogonalized with respect to others?",
        null=True,
        verbose_name="Orthogonalization?",
        blank=True,
    )
    orthogonalization_description = models.CharField(
        help_text="If orthogonalization was used, describe here",
        verbose_name="Orthogonalization description",
        max_length=200,
        null=True,
        blank=True,
    )
    used_high_pass_filter = models.BooleanField(
        help_text="Was high pass filtering applied?",
        null=True,
        verbose_name="High-pass filter?",
        blank=True,
    )
    high_pass_filter_method = models.CharField(
        help_text="Describe method used for high pass filtering",
        verbose_name="High-pass filtering method",
        max_length=200,
        null=True,
        blank=True,
    )
    autocorrelation_model = models.CharField(
        help_text="What autocorrelation model was used (or 'none' of none was used)",
        verbose_name="Autocorrelation method",
        max_length=200,
        null=True,
        blank=True,
    )
    group_model_type = models.CharField(
        help_text="Type of group model used (e.g., regression)",
        verbose_name="Group model type",
        max_length=200,
        null=True,
        blank=True,
    )
    group_estimation_type = models.CharField(
        help_text="Estimation method used for group model (e.g., OLS, generalized least squares)",
        verbose_name="Group estimation type",
        max_length=200,
        null=True,
        blank=True,
    )
    group_modeling_software = models.CharField(
        help_text="Software used for group modeling if different from overall package",
        verbose_name="Group modeling software",
        max_length=200,
        null=True,
        blank=True,
    )
    group_inference_type = models.CharField(
        choices=[
            ("randommixedeffects", "random/mixed effects"),
            ("fixedeffects", "fixed effects"),
        ],
        max_length=200,
        blank=True,
        help_text="Type of inference for group model",
        null=True,
        verbose_name="Group inference type",
    )
    group_model_multilevel = models.CharField(
        help_text="If more than 2-levels, describe the levels and assumptions of the model (e.g. are variances assumed equal between groups)",
        verbose_name="Multilevel modeling",
        max_length=200,
        null=True,
        blank=True,
    )
    group_repeated_measures = models.BooleanField(
        help_text="Was this a repeated measures design at the group level?",
        null=True,
        verbose_name="Repeated measures",
        blank=True,
    )
    group_repeated_measures_method = models.CharField(
        help_text="If multiple measurements per subject, list method to account for within subject correlation, exact assumptions made about correlation/variance",
        verbose_name="Repeated measures method",
        max_length=200,
        null=True,
        blank=True,
    )
    nutbrain_hunger_state = models.CharField(
        choices=[
            ("I", "Fed (<1h after meal)"),
            ("II", "2-3 h fasted"),
            ("III", "4-6 h fasted"),
            ("IV", "7-9h fasted"),
            ("V", "fasted overnight (> 10h)"),
            ("VI", "36h fast"),
        ],
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Hunger state",
    )
    nutbrain_food_viewing_conditions = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Food viewing conditions",
        help_text="Image categories",
    )
    nutbrain_food_choice_type = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Food choice type",
        help_text="Choice conditions/image types",
    )
    nutbrain_taste_conditions = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Taste conditions"
    )
    nutbrain_odor_conditions = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Odor conditions"
    )

    @property
    def is_statisticmap_set(self):
        """Holds only uploaded statistic maps (no atlases, other images or NIDM bundles)."""
        return not (
            self.nidm_bundles.exists()
            or self.items.exclude(kind="statmap", source_bundle__isnull=True).exists()
        )

    def item_count(self):
        """Images plus NIDM bundles."""
        return self.items.count() + self.nidm_bundles.count()

    def get_absolute_url(self):
        return_cid = self.id
        if self.private:
            if self.private_token is None:
                self.private_token = str(uuid.uuid4())[:8]
                self.save()
            return_cid = self.private_token
        return reverse("statmaps:collection_details", args=[str(return_cid)])

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        app_label = "statmaps"

class CognitiveAtlasTask(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False, db_index=True)
    cog_atlas_id = models.CharField(
        primary_key=True, max_length=200, null=False, blank=False
    )

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        cog_atlas_id = self.cog_atlas_id
        return reverse("statmaps:view_task", args=[str(cog_atlas_id)])

    class Meta:
        ordering = ["name"]


class CognitiveAtlasContrast(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    cog_atlas_id = models.CharField(
        primary_key=True, max_length=200, null=False, blank=False
    )
    task = models.ForeignKey(CognitiveAtlasTask, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ["name"]


def upload_nidm_to(instance, filename):
    base_subdir = os.path.split(instance.zip_file.name)[-1].replace(".zip", "")
    return os.path.join("images", str(instance.collection.id), base_subdir, filename)


def upload_img_to(instance, filename):
    """Storage path of an item's file (the use cases store files with the same layout)."""
    if getattr(instance, "source_bundle_id", None):
        return upload_nidm_to(instance.source_bundle, filename)
    return os.path.join("images", str(instance.collection.id), filename)


upload_to = upload_img_to  # for migration backwards compat.


class KeyValueTag(TagBase):
    value = models.CharField(max_length=200, blank=True)


class ValueTaggedItem(GenericTaggedItemBase):
    tag = models.ForeignKey(
        KeyValueTag, related_name="tagged_items", on_delete=models.CASCADE
    )


class ItemQuerySet(models.QuerySet):
    def statmaps(self):
        """Uploaded statistic maps (the former StatisticMap)."""
        return self.filter(kind=Item.STATMAP, source_bundle__isnull=True)

    def nidm_statmaps(self):
        return self.filter(kind=Item.STATMAP, source_bundle__isnull=False)

    def all_statmaps(self):
        return self.filter(kind=Item.STATMAP)

    def atlases(self):
        return self.filter(kind=Item.ATLAS)


STATMAP_FIXED_FIELDS = (
    "name", "description", "figure", "target_template_image", "age", "sex", "ethnicity",
    "race", "handedness", "bis11_score", "bis_bas_score", "spsrq_score", "BMI",
    "fat_percentage", "waist_hip_ratio", "hours_since_last_meal", "days_since_menstruation",
    "mean_PDS_score", "tanner_stage", "map_type", "analysis_level", "number_of_subjects",
    "modality", "contrast_definition", "cognitive_paradigm_cogatlas",
    "cognitive_paradigm_description_url",
)


class NIDMBundle(models.Model):
    """An uploaded NIDM-Results zip; its statistic maps are Items with source_bundle set."""

    name = models.CharField(max_length=200, null=False, blank=False, db_index=True)
    description = models.TextField(blank=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="nidm_bundles")
    add_date = models.DateTimeField("date published", auto_now_add=True)
    modify_date = models.DateTimeField("date modified", auto_now=True, db_index=True)
    tags = TaggableManager(through=ValueTaggedItem, blank=True)
    is_valid = models.BooleanField(default=True)
    ttl_file = models.FileField(
        upload_to=upload_nidm_to,
        storage=NIDMStorage(),
        null=True,
        blank=True,
        verbose_name="Turtle serialization of NIDM Results (.ttl)",
    )

    zip_file = models.FileField(
        upload_to=upload_nidm_to,
        storage=NIDMStorage(),
        null=False,
        blank=False,
        verbose_name="NIDM Results zip file",
    )

    class Meta:
        verbose_name = "NIDM results"
        verbose_name_plural = "NIDMResults"

    def __str__(self):
        return self.name

    type_label = "nidm results"

    def get_absolute_url(self):
        return_args = [str(self.collection_id), self.name]
        if self.collection.private:
            return_args[0] = str(self.collection.private_token)
        return reverse("statmaps:view_nidm_results", args=return_args)


class Item(models.Model):
    """An image of any kind. `kind` and `source_bundle` replace the old subclasses."""

    STATMAP, ATLAS, OTHER = "statmap", "atlas", "other"
    KIND_CHOICES = ((STATMAP, "statistic map"), (ATLAS, "atlas"), (OTHER, "image"))
    MAP_TYPE_CHOICES = vocabulary.MAP_TYPE_CHOICES
    ANALYSIS_LEVEL_CHOICES = vocabulary.ANALYSIS_LEVEL_CHOICES
    MODALITY_CHOICES = vocabulary.MODALITY_CHOICES
    Pa = vocabulary.Pa

    objects = ItemQuerySet.as_manager()

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    name = models.CharField(max_length=200, null=False, blank=False, db_index=True)
    description = models.TextField(blank=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="items")
    add_date = models.DateTimeField("date published", auto_now_add=True)
    modify_date = models.DateTimeField("date modified", auto_now=True, db_index=True)
    tags = TaggableManager(through=ValueTaggedItem, blank=True)
    is_valid = models.BooleanField(default=True)
    file = models.FileField(
        upload_to=upload_img_to,
        null=False,
        blank=False,
        storage=DoubleExtensionStorage(),
        max_length=500,
        verbose_name="File with the unthresholded volume map (.img, .nii, .nii.gz)",
    )
    surface_left_file = models.FileField(
        upload_to=upload_img_to,
        null=True,
        blank=True,
        storage=DoubleExtensionStorage(),
        verbose_name="File with the unthresholded LEFT hemisphere fsaverage surface map (.mgh, .curv, .gii)",
    )
    surface_right_file = models.FileField(
        upload_to=upload_img_to,
        null=True,
        blank=True,
        storage=DoubleExtensionStorage(),
        verbose_name="File with the unthresholded RIGHT hemisphere fsaverage surface map (.mgh, .curv, .gii)",
    )
    data_origin = models.CharField(
        help_text=("Was this map originally derived from volume or surface?"),
        verbose_name="Data origin",
        default="volume",
        max_length=200,
        null=True,
        blank=True,
        choices=[("volume", "volume"), ("surface", "surface")],
    )
    target_template_image = models.CharField(
        choices=get_target_template_list(),
        help_text="Name of target template image",
        verbose_name="Target template image",
        default=DEFAULT_TEMPLATE,
        max_length=200,
        null=False,
        blank=False,
    )
    subject_species = models.CharField(
        max_length=200,
        default=POSSIBLE_TEMPLATES[DEFAULT_TEMPLATE]["species"],
        blank=True,
        null=True,
    )
    figure = models.CharField(
        help_text="Which figure in the corresponding paper was this map displayed in?",
        verbose_name="Manuscript figure",
        max_length=200,
        null=True,
        blank=True,
    )

    ### Added for the NutBrain project BEGIN
    handedness = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        choices=[("L", "Left"), ("R", "Right")],
        verbose_name="Handedness",
    )
    age = models.FloatField(null=True, blank=True, verbose_name="Age (years)")
    sex = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        choices=[("M", "Male"), ("F", "Female"), ("O", "Other")],
        verbose_name="Sex",
    )
    race = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        choices=[
            ("W", "White"),
            ("B", "Black or African American"),
            ("I", "American Indian or Alaska Native"),
            ("A", "Asian"),
            ("H", "Native Hawaiian or Other Pacific Islander"),
        ],
        verbose_name="Race (US Census definition)",
    )
    ethnicity = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        choices=[("H", "Hispanic or Latino"), ("NH", "Not Hispanic or Latino")],
        verbose_name="Ethnicity (US Census definition)",
    )
    BMI = models.FloatField(
        null=True, blank=True, verbose_name="Body Mass Index (kg/m2)"
    )
    fat_percentage = models.FloatField(null=True, blank=True, verbose_name="% body fat")
    waist_hip_ratio = models.FloatField(
        null=True, blank=True, verbose_name="waist-hip-ratio"
    )
    mean_PDS_score = models.FloatField(
        null=True, blank=True, verbose_name="Mean Puberty Development Scale score"
    )
    tanner_stage = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        choices=[("I", "I"), ("II", "II"), ("III", "III"), ("IV", "IV"), ("V", "V")],
        verbose_name="Tanner stage",
    )
    days_since_menstruation = models.FloatField(
        null=True, blank=True, verbose_name="Number of days since menstruation"
    )
    hours_since_last_meal = models.FloatField(
        null=True, blank=True, verbose_name="Time since last meal (hours)"
    )
    bis_bas_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Behavioral inhibition, behavioral activation " "(BIS/BAS) score",
    )
    spsrq_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Sensitivity to Punishment and Sensitivity to "
        "Reward Questionnaire (SPSRQ) score",
    )
    bis11_score = models.FloatField(
        null=True, blank=True, verbose_name="Barratt Impulsiveness Scale (BIS-11) score"
    )
    # END

    thumbnail = models.FileField(
        help_text="The orthogonal view thumbnail path of the nifti image",
        null=True,
        blank=True,
        upload_to=upload_img_to,
        verbose_name="Image orthogonal view thumbnail 2D bitmap",
        storage=DoubleExtensionStorage(),
    )
    reduced_representation = models.FileField(
        help_text=(
            "Binary file with the vector of in brain values resampled to lower resolution"
        ),
        verbose_name="Reduced representation of the image",
        null=True,
        blank=True,
        upload_to=upload_img_to,
        storage=OverwriteStorage(),
    )
    data = models.JSONField(blank=True, null=True)

    # statistic maps
    map_type = models.CharField(
        help_text=("Type of statistic that is the basis of the inference"),
        verbose_name="Map type",
        max_length=200,
        null=True,
        blank=False,
        choices=MAP_TYPE_CHOICES,
    )
    is_thresholded = models.BooleanField(null=True, blank=True)
    perc_bad_voxels = models.FloatField(null=True, blank=True)
    not_mni = models.BooleanField(null=True, blank=True)
    brain_coverage = models.FloatField(null=True, blank=True)
    perc_voxels_outside = models.FloatField(null=True, blank=True)
    analysis_level = models.CharField(
        help_text=(
            "What level of summary data was used as the input to this analysis?"
        ),
        verbose_name="Analysis level",
        max_length=200,
        null=True,
        blank=False,
        choices=ANALYSIS_LEVEL_CHOICES,
    )
    number_of_subjects = models.IntegerField(
        help_text="Number of subjects used to generate this map",
        null=True,
        verbose_name="No. of subjects",
        blank=False,
    )
    ignore_file_warning = models.BooleanField(
        null=True,
        blank=False,
        default=False,
        verbose_name="Ignore the warning",
        help_text="Ignore the warning when the map is sparse by nature, an ROI mask, or was acquired with limited field of view.",
    )
    modality = models.CharField(
        verbose_name="Modality & Acquisition Type",
        help_text="Brain imaging procedure that was used to acquire the data.",
        max_length=200,
        null=True,
        blank=False,
        choices=MODALITY_CHOICES,
        db_index=True,
    )

    statistic_parameters = models.FloatField(
        help_text="Parameters of the null distribution of the test statistic, typically degrees of freedom (should be clear from the test statistic what these are).",
        null=True,
        verbose_name="Statistic parameters",
        blank=True,
    )
    smoothness_fwhm = models.FloatField(
        help_text="Noise smoothness for statistical inference; this is the estimated smoothness used with Random Field Theory or a simulation-based inference method.",
        verbose_name="Smoothness FWHM",
        null=True,
        blank=True,
    )
    contrast_definition = models.CharField(
        help_text="Exactly what terms are subtracted from what? Define these in terms of task or stimulus conditions (e.g., 'one-back task with objects versus zero-back task with objects') instead of underlying psychological concepts (e.g., 'working memory').",
        verbose_name="Contrast definition",
        max_length=200,
        null=True,
        blank=True,
    )
    contrast_definition_cogatlas = models.CharField(
        help_text="Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast",
        verbose_name="Cognitive Atlas definition",
        max_length=200,
        null=True,
        blank=True,
    )
    cognitive_paradigm_cogatlas = models.ForeignKey(
        CognitiveAtlasTask,
        help_text="Task performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/' target='_blank'>Cognitive Atlas</a>. If there's no match, select 'None / Other'. ",
        verbose_name="Cognitive Atlas Paradigm",
        null=True,
        blank=False,
        on_delete=models.PROTECT
    )
    cognitive_contrast_cogatlas = models.ForeignKey(
        CognitiveAtlasContrast,
        help_text="Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast",
        verbose_name="Cognitive Atlas Contrast",
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    cognitive_paradigm_description_url = models.URLField(
        help_text="Link to a paper, poster, abstract describing in detail the task performed by the subject(s) in the scanner.",
        verbose_name="Description URL",
        null=True,
        blank=True,
    )
    cognitive_paradigm_short_description = models.CharField(
        help_text="Describe your task",
        verbose_name="Task Description",
        null=True,
        blank=True,
    )
    cognitive_paradigm_name = models.CharField(
        help_text="Name of your task (if it)",
        verbose_name="Task Name",
        null=True,
        blank=True
     )
    source_bundle = models.ForeignKey(
        NIDMBundle, null=True, blank=True, on_delete=models.CASCADE, related_name="statmaps"
    )

    # atlases
    label_description_file = models.FileField(
        upload_to=upload_img_to,
        null=True,
        blank=True,
        storage=DoubleExtensionStorage(),
        verbose_name="FSL compatible label description file (.xml)",
    )

    class Meta:
        indexes = [models.Index(fields=["modality", "cognitive_paradigm_cogatlas"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(kind__in=["statmap", "atlas", "other"]), name="item_kind_valid"
            ),
            models.CheckConstraint(
                check=~models.Q(kind="atlas") | models.Q(label_description_file__isnull=False),
                name="item_atlas_has_labels",
            ),
            models.CheckConstraint(
                check=models.Q(kind="statmap") | models.Q(map_type__isnull=True),
                name="item_map_type_only_on_statmaps",
            ),
            models.CheckConstraint(
                check=models.Q(source_bundle__isnull=True) | models.Q(kind="statmap"),
                name="item_bundle_maps_are_statmaps",
            ),
            models.CheckConstraint(
                check=~models.Q(kind="statmap", source_bundle__isnull=True)
                | models.Q(modality__isnull=False),
                name="item_uploaded_statmaps_have_modality",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_statmap(self):
        return self.kind == self.STATMAP

    @property
    def type_label(self):
        """The label the collection tables have always shown for each kind."""
        if self.kind == self.STATMAP:
            return "nidm result statistic map" if self.source_bundle_id else "statistic map"
        return {self.ATLAS: "atlas", self.OTHER: "image"}[self.kind]

    def get_absolute_url(self, edit=False):
        return_args = [str(self.id)]
        if edit:
            return reverse("statmaps:edit_image", args=return_args)
        url_name = "statmaps:image_details"
        if self.collection.private:
            return_args.insert(0, str(self.collection.private_token))
            url_name = "statmaps:private_image_details"
        return reverse(url_name, args=return_args)

    def get_thumbnail_url(self):
        try:
            url = self.thumbnail.url
        except ValueError:
            url = os.path.abspath(os.path.join("/static", "images", "glass_brain_empty.jpg"))
        return url

    @staticmethod
    def get_fixed_fields():
        return STATMAP_FIXED_FIELDS



class Similarity(models.Model):
    similarity_metric = models.CharField(
        max_length=200,
        null=False,
        blank=False,
        db_index=True,
        help_text="the name of the similarity metric to describe a relationship between two or more images.",
        verbose_name="similarity metric name",
    )
    transformation = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text="the name of the transformation of the data relevant to the metric",
        verbose_name="transformation of images name",
    )
    metric_ontology_iri = models.URLField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text="If defined, a url of an ontology IRI to describe the similarity metric",
        verbose_name="similarity metric ontology IRI",
    )
    transformation_ontology_iri = models.URLField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text="If defined, a url of an ontology IRI to describe the transformation metric",
        verbose_name="image transformation ontology IRI",
    )

    class Meta:
        verbose_name = "similarity metric"
        verbose_name_plural = "similarity metrics"
        unique_together = ("similarity_metric", "transformation")

    def __str__(self):
        return "<metric:%s><transformation:%s>" % (
            self.similarity_metric,
            self.transformation,
        )

    def __unicode__(self):
        return "<metric:%s><transformation:%s>" % (
            self.similarity_metric,
            self.transformation,
        )


class Comparison(models.Model):
    image1 = models.ForeignKey(
        "Item", related_name="image1", db_index=True, on_delete=models.CASCADE
    )
    image2 = models.ForeignKey(
        "Item", related_name="image2", db_index=True, on_delete=models.CASCADE
    )
    similarity_metric = models.ForeignKey(Similarity, on_delete=models.CASCADE)
    similarity_score = models.FloatField(
        help_text="the comparison score between two or more statistical maps",
        verbose_name="the comparison score between two or more statistical maps",
    )

    def __str__(self):
        return "<%s><%s><score:%s>" % (self.image1, self.image2, self.similarity_score)

    def __unicode__(self):
        return "<%s><%s><score:%s>" % (self.image1, self.image2, self.similarity_score)

    class Meta:
        unique_together = ("image1", "image2")
        index_together = [
            ["image1", "image2", "similarity_metric"],
            ["image2", "similarity_metric"],
            ["image1", "similarity_metric"],
        ]

        verbose_name = "pairwise image comparison"
        verbose_name_plural = "pairwise image comparisons"


class Metaanalysis(models.Model):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, unique=True, null=False)
    description = models.TextField(blank=True, null=True)
    maps = models.ManyToManyField(Item, blank=True)
    status = models.CharField(
        choices=[
            ("active", "active"),
            ("inactive", "inactive"),
            ("completed", "completed"),
        ],
        max_length=200,
        blank=True,
        null=True,
        default="active",
    )
    output_maps = models.ForeignKey(
        Collection, blank=True, null=True, on_delete=models.SET_NULL
    )

    def get_absolute_url(self):
        return reverse("statmaps:view_metaanalysis", args=[str(self.id)])
