# -*- coding: utf-8 -*-
import os
import shutil
import stat
from datetime import datetime
from gzip import GzipFile

import nibabel as nb
from django.contrib.auth.models import User
from django.core.files import File
from django.urls import reverse
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.fields.files import FieldFile
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils import timezone
from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm
from polymorphic.models import PolymorphicModel
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, TagBase

from neurovault.apps.statmaps.storage import (
    DoubleExtensionStorage,
    NIDMStorage,
    OverwriteStorage,
)

# from neurovault.apps.statmaps.tasks import run_voxelwise_pearson_similarity, process_map
from neurovault.apps.statmaps.tasks import process_map
from neurovault.settings import PRIVATE_MEDIA_ROOT

# possible templates
POSSIBLE_TEMPLATES = {
    "GenericMNI": {
        "name": "Human (Generic/Unknown MNI)",
        "species": "homo sapiens",
        "pycortex_enabled": True,
        "image_search_enabled": True,
        "mask": "MNI152_T1_2mm_brain_mask.nii.gz",
    },
    "Dorr2008": {
        "name": "Mouse (Dorr 2008 space)",
        "species": "mus musculus",
        "pycortex_enabled": False,
        "image_search_enabled": False,
        "mask": None,
    },
    "NMT": {
        "name": "Rhesus - macacca mulatta (NMT)",
        "species": "macaca mulatta",
        "pycortex_enabled": False,
        "image_search_enabled": False,
        "mask": None,
    },
    "MNI152NLin2009cAsym": {
        "name": "Human (MNI152 NLin 2009c Asym)",
        "species": "homo sapiens",
        "pycortex_enabled": True,
        "image_search_enabled": True,
        "mask": None,
    },
}
DEFAULT_TEMPLATE = "GenericMNI"


def get_possible_templates():
    return POSSIBLE_TEMPLATES


def get_target_template_list():
    return [
        (template, POSSIBLE_TEMPLATES[template]["name"])
        for template in POSSIBLE_TEMPLATES
    ]


COMMUNITIES = {
    "developmental": {"short_desc": "Developmental Neuroscience"},
    "nutrition": {"short_desc": "Nutrition Neuroscience"},
}
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
    DOI = models.CharField(
        max_length=200,
        unique=True,
        blank=True,
        null=True,
        default=None,
        verbose_name="DOI of the corresponding paper",
        help_text="Required if you want your maps to be archived in Stanford Digital Repository",
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
                "Public (The collection will be accessible by anyone and all the data in it will be distributed under CC0 license)",
            ),
            (
                True,
                "Private (The collection will be not listed in the NeuroVault index. It will be possible to shared it with others at a private URL.)",
            ),
        ),
        default=False,
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
        return all(
            (isinstance(i, StatisticMap) for i in self.basecollectionitem_set.all())
        )

    def get_absolute_url(self):
        return_cid = self.id
        if self.private:
            return_cid = self.private_token
        return reverse("statmaps:collection_details", args=[str(return_cid)])

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.DOI is not None and self.DOI.strip() == "":
            self.DOI = None
        if self.private_token is not None and self.private_token.strip() == "":
            self.private_token = None

        if self.DOI and not self.private and not self.doi_add_date:
            self.doi_add_date = timezone.now()

        # run calculations when collection turns public
        privacy_changed = False
        DOI_changed = False
        if self.pk is not None:
            old_object = Collection.objects.get(pk=self.pk)
            old_is_private = old_object.private
            old_has_DOI = old_object.DOI is not None
            privacy_changed = old_is_private != self.private
            DOI_changed = old_has_DOI != (self.DOI is not None)

        super(Collection, self).save(*args, **kwargs)

        """
        if (privacy_changed and not self.private) or (DOI_changed and self.DOI is not None):
            for image in self.basecollectionitem_set.instance_of(Image).all():
                if image.pk:
                    run_voxelwise_pearson_similarity.apply_async([image.pk])
        """

    class Meta:
        app_label = "statmaps"

    def delete(self, using=None):
        cid = self.pk
        for image in self.basecollectionitem_set.instance_of(Image):
            image.delete()
        for nidmresult in self.basecollectionitem_set.instance_of(NIDMResults):
            nidmresult.delete()
        ret = super(Collection, self).delete(using=using)
        collDir = os.path.join(PRIVATE_MEDIA_ROOT, "images", str(cid))
        try:
            shutil.rmtree(collDir)
        except OSError:
            print("Image directory for collection %s does not exist" % cid)

        return ret


@receiver(post_save, sender=Collection)
def collection_created(sender, instance, created, **kwargs):
    if created:
        assign_perm("delete_collection", instance.owner, instance)
        assign_perm("change_collection", instance.owner, instance)
        for image in instance.basecollectionitem_set.all():
            assign_perm("change_basecollectionitem", instance.owner, image)
            assign_perm("delete_basecollectionitem", instance.owner, image)


def contributors_changed(sender, instance, action, **kwargs):
    if action in ["post_remove", "post_add", "post_clear"]:
        current_contributors = set([user.pk for user in get_users_with_perms(instance)])
        new_contributors = set(
            [
                user.pk
                for user in [
                    instance.owner,
                ]
                + list(instance.contributors.all())
            ]
        )

        for contributor in list(new_contributors - current_contributors):
            contributor = User.objects.get(pk=contributor)
            assign_perm("change_collection", contributor, instance)
            for image in instance.basecollectionitem_set.all():
                assign_perm("change_basecollectionitem", contributor, image)
                assign_perm("delete_basecollectionitem", contributor, image)

        for contributor in current_contributors - new_contributors:
            contributor = User.objects.get(pk=contributor)
            remove_perm("change_collection", contributor, instance)
            for image in instance.basecollectionitem_set.all():
                remove_perm("change_basecollectionitem", contributor, image)
                remove_perm("delete_basecollectionitem", contributor, image)


m2m_changed.connect(contributors_changed, sender=Collection.contributors.through)


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
    nidm_types = ["nidmresultstatisticmap"]
    if (
        hasattr(instance, "polymorphic_ctype")
        and instance.polymorphic_ctype.model in nidm_types
    ):
        return upload_nidm_to(instance.nidm_results, filename)
    return os.path.join("images", str(instance.collection.id), filename)


upload_to = upload_img_to  # for migration backwards compat.


class KeyValueTag(TagBase):
    value = models.CharField(max_length=200, blank=True)


class ValueTaggedItem(GenericTaggedItemBase):
    tag = models.ForeignKey(
        KeyValueTag, related_name="tagged_items", on_delete=models.CASCADE
    )


class BaseCollectionItem(PolymorphicModel, models.Model):
    name = models.CharField(max_length=200, null=False, blank=False, db_index=True)
    description = models.TextField(blank=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    add_date = models.DateTimeField("date published", auto_now_add=True)
    modify_date = models.DateTimeField("date modified", auto_now=True)
    tags = TaggableManager(through=ValueTaggedItem, blank=True)
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def set_name(self, new_name):
        self.name = new_name

    def save(self):
        self.collection.modify_date = timezone.now()
        self.collection.save()
        super(BaseCollectionItem, self).save()

    def delete(self):
        self.collection.modify_date = timezone.now()
        self.collection.save()
        super(BaseCollectionItem, self).delete()

    @classmethod
    def get_fixed_fields(cls):
        return ("name", "description", "figure")


# sadly signals are not emitted for base classes so we need to connect this to every class separately
def basecollectionitem_created(sender, instance, created, **kwargs):
    if created:
        for user in [
            instance.collection.owner,
        ] + list(instance.collection.contributors.all()):
            assign_perm("change_basecollectionitem", user, instance)
            assign_perm("delete_basecollectionitem", user, instance)


class Image(BaseCollectionItem):
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
        help_text=("Was this map originaly derived from volume or surface?"),
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
        verbose_name="Corresponding figure",
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
    gender = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        choices=[("M", "Male"), ("F", "Female"), ("O", "Other")],
        verbose_name="Gender",
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
    # hstore_objects = hstore.HStoreManager()

    def get_absolute_url(self):
        return_args = [str(self.id)]
        url_name = "statmaps:image_details"
        if self.collection.private:
            return_args.insert(0, str(self.collection.private_token))
            url_name = "statmaps:private_image_details"
        return reverse(url_name, args=return_args)

    def get_thumbnail_url(self):
        try:
            url = self.thumbnail.url
        except ValueError:
            url = os.path.abspath(
                os.path.join("/static", "images", "glass_brain_empty.jpg")
            )
        return url

    @classmethod
    def create(
        cls, my_file, my_file_name, my_name, my_desc, my_collection_pk, my_map_type
    ):
        my_collection = Collection.objects.get(pk=my_collection_pk)

        # Copy the nifti file into the proper location
        image = cls(description=my_desc, name=my_name, collection=my_collection)
        f = open(my_file)
        niftiFile = File(f)
        image.file.save(my_file_name, niftiFile)

        # If a .img file was loaded then load the correspoding .hdr file as well
        _, ext = os.path.splitext(my_file_name)
        print(ext)
        if ext in [".img"]:
            f = open(my_file[:-3] + "hdr")
            hdrFile = File(f)
            image.hdr_file.save(my_file_name[:-3] + "hdr", hdrFile)

        image.map_type = my_map_type

        # create JSON file for neurosynth viewer
        if os.path.exists(image.file.path):
            nifti_gz_file = ".".join(image.file.path.split(".")[:-1]) + ".nii.gz"
            nii = nb.load(image.file.path)
            nb.save(nii, nifti_gz_file)
            f = open(nifti_gz_file)
            image.nifti_gz_file.save(
                nifti_gz_file.split(os.path.sep)[-1], File(f), save=False
            )

        image.save()

        return image

    # Celery task to generate glass brain image on new/update
    def save(self):
        file_changed = False
        collection_changed = False
        if self.pk is not None:
            old_pk = Image.objects.get(pk=self.pk)
            if old_pk.file != self.file:
                file_changed = True
            if old_pk.collection != self.collection:
                collection_changed = True

        do_update = True if file_changed else False
        new_image = True if self.pk is None else False
        super(Image, self).save()

        if do_update or new_image:
            process_map.apply_async([self.pk])

        if self.subject_species == None and self.target_template_image:
            import neurovault.apps.statmaps.utils as nvutils

            self.subject_species = nvutils.infer_subject_species(
                self.target_template_image
            )

        if collection_changed:
            for field_name in [f.name for f in self._meta.get_fields()]:
                field_instance = getattr(self, field_name)
                if field_instance and isinstance(field_instance, FieldFile):
                    old_path = field_instance.path
                    new_name = upload_img_to(self, field_instance.name.split("/")[-1])
                    new_name = field_instance.storage.get_available_name(new_name)
                    new_path = field_instance.storage.path(new_name)
                    if not os.path.exists(os.path.dirname(new_path)):
                        os.mkdir(os.path.dirname(new_path))
                    shutil.copy(old_path, new_path)
                    field_instance.name = new_name
                    assert old_path != new_path
                    os.remove(old_path)
            super(Image, self).save()

    @classmethod
    def get_fixed_fields(cls):
        return super(Image, cls).get_fixed_fields() + (
            "target_template_image",
            "age",
            "gender",
            "ethnicity",
            "race",
            "handedness",
            "bis11_score",
            "bis_bas_score",
            "spsrq_score",
            "BMI",
            "fat_percentage",
            "waist_hip_ratio",
            "hours_since_last_meal",
            "days_since_menstruation",
            "mean_PDS_score",
            "tanner_stage",
        )


class BaseStatisticMap(Image):
    T = "T"
    Z = "Z"
    F = "F"
    X2 = "X2"
    P = "P"
    IP = "IP"
    M = "M"
    U = "U"
    R = "R"
    Pa = "Pa"
    OTHER = "Other"
    S = "S"
    G = "G"
    M = "M"
    A = "A"
    V = "V"
    MAP_TYPE_CHOICES = (
        (T, "T map"),
        (Z, "Z map"),
        (F, "F map"),
        (X2, "Chi squared map"),
        (P, "P map (given null hypothesis)"),
        (IP, '1-P map ("inverted" probability)'),
        (M, "multivariate-beta map"),
        (U, "univariate-beta map"),
        (R, "ROI/mask"),
        (Pa, "parcellation"),
        (A, "anatomical"),
        (V, "variance"),
        (OTHER, "other"),
    )
    ANALYSIS_LEVEL_CHOICES = (
        (S, "single-subject"),
        (G, "group"),
        (M, "meta-analysis"),
        (OTHER, "other"),
    )

    map_type = models.CharField(
        help_text=("Type of statistic that is the basis of the inference"),
        verbose_name="Map type",
        max_length=200,
        null=False,
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

    def save(self):
        if self.perc_bad_voxels == None and self.file:
            import neurovault.apps.statmaps.utils as nvutils

            self.file.open()
            gzfileobj = GzipFile(
                filename=self.file.name, mode="rb", fileobj=self.file.file
            )
            nii = nb.Nifti1Image.from_file_map(
                {"image": nb.FileHolder(self.file.name, gzfileobj)}
            )
            self.is_thresholded, ratio_bad = nvutils.is_thresholded(nii)
            self.perc_bad_voxels = ratio_bad * 100.0

        if self.brain_coverage == None and self.file:
            import neurovault.apps.statmaps.utils as nvutils

            self.file.open()
            gzfileobj = GzipFile(
                filename=self.file.name, mode="rb", fileobj=self.file.file
            )
            nii = nb.Nifti1Image.from_file_map(
                {"image": nb.FileHolder(self.file.name, gzfileobj)}
            )
            (
                self.not_mni,
                self.brain_coverage,
                self.perc_voxels_outside,
            ) = nvutils.not_in_mni(nii, self.target_template_image)

        if self.map_type == self.OTHER:
            import neurovault.apps.statmaps.utils as nvutils

            self.file.open()
            gzfileobj = GzipFile(
                filename=self.file.name, mode="rb", fileobj=self.file.file
            )
            nii = nb.Nifti1Image.from_file_map(
                {"image": nb.FileHolder(self.file.name, gzfileobj)}
            )
            self.map_type = nvutils.infer_map_type(nii)

        # Calculation of image reduced_representation and comparisons
        file_changed = False
        if self.pk is not None:
            existing = Image.objects.get(pk=self.pk)
            if existing.file != self.file:
                file_changed = True
        do_update = True if file_changed else False
        new_image = True if self.pk is None else False

        # If we have an update, delete old pkl and comparisons first before saving
        if do_update and self.collection:
            if self.reduced_representation:  # not applicable for private collections
                self.reduced_representation.delete()

                # If more than one metric is added to NeuroVault, this must also filter based on metric
                comparisons = Comparison.objects.filter(Q(image1=self) | Q(image2=self))
                if comparisons:
                    comparisons.delete()
        super(BaseStatisticMap, self).save()

        # Calculate comparisons
        """
        if do_update or new_image:
            run_voxelwise_pearson_similarity.apply_async([self.pk])
        """

        self.file.close()

    @classmethod
    def get_fixed_fields(cls):
        return super(BaseStatisticMap, cls).get_fixed_fields() + (
            "map_type",
            "analysis_level",
            "number_of_subjects",
        )

    class Meta:
        abstract = True


class StatisticMap(BaseStatisticMap):
    fMRI_BOLD = "fMRI-BOLD"
    fMRI_CBF = "fMRI-CBF"
    fMRI_CBV = "fMRI-CBV"
    Diffusion_MRI = "Diffusion MRI"
    Structural_MRI = "Structural MRI"
    PET_FDG = "PET FDG"
    PET_15O = "PET [15O]-water"
    PET_OTHER = "PET other"
    MEG = "MEG"
    EEG = "EEG"
    Other = "Other"
    MODALITY_CHOICES = (
        (fMRI_BOLD, "fMRI-BOLD"),
        (fMRI_CBF, "fMRI-CBF"),
        (fMRI_CBV, "fMRI-CBV"),
        (Diffusion_MRI, "Diffusion MRI"),
        (Structural_MRI, "Structural MRI"),
        (PET_FDG, "PET FDG"),
        (PET_15O, "PET [15O]-water"),
        (PET_OTHER, "PET other"),
        (MEG, "MEG"),
        (EEG, "EEG"),
        (Other, "Other"),
    )
    ignore_file_warning = models.BooleanField(
        blank=False,
        default=False,
        verbose_name="Ignore the warning",
        help_text="Ignore the warning when the map is sparse by nature, an ROI mask, or was acquired with limited field of view.",
    )
    modality = models.CharField(
        verbose_name="Modality & Acquisition Type",
        help_text="Brain imaging procedure that was used to acquire the data.",
        max_length=200,
        null=False,
        blank=False,
        choices=MODALITY_CHOICES,
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
        help_text="Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/' target='_blank'>Cognitive Atlas</a> terms",
        verbose_name="Cognitive Atlas Paradigm",
        null=True,
        blank=False,
        on_delete=models.PROTECT,
    )
    cognitive_contrast_cogatlas = models.ForeignKey(
        CognitiveAtlasContrast,
        help_text="Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast",
        verbose_name="Cognitive Atlas Contrast",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    cognitive_paradigm_description_url = models.URLField(
        help_text="Link to a paper, poster, abstract or other form text describing in detail the task performed by the subject(s) in the scanner.",
        verbose_name="Cognitive Paradigm Description URL",
        null=True,
        blank=True,
    )

    @classmethod
    def get_fixed_fields(cls):
        return super(StatisticMap, cls).get_fixed_fields() + (
            "modality",
            "contrast_definition",
            "cognitive_paradigm_cogatlas",
            "cognitive_paradigm_description_url",
        )


post_save.connect(basecollectionitem_created, sender=StatisticMap, weak=True)


class NIDMResults(BaseCollectionItem):
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
        verbose_name_plural = "NIDMResults"

    def get_absolute_url(self):
        return_args = [str(self.collection_id), self.name]
        url_name = "statmaps:view_nidm_results"
        if self.collection.private:
            return_args[0] = str(self.collection.private_token)
        return reverse(url_name, args=return_args)

    @staticmethod
    def get_form_class():
        from neurovault.apps.statmaps.forms import NIDMResultsForm

        return NIDMResultsForm


@receiver(post_delete, sender=NIDMResults)
def mymodel_delete(sender, instance, **kwargs):
    nidm_path = os.path.dirname(instance.zip_file.path)
    if os.path.isdir(nidm_path):
        shutil.rmtree(nidm_path, onerror=remove_readonly)


# Solution to delete read-only files from:
# https://docs.python.org/3/library/shutil.html#rmtree-example
def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)


post_save.connect(basecollectionitem_created, sender=NIDMResults, weak=True)


class NIDMResultStatisticMap(BaseStatisticMap):
    nidm_results = models.ForeignKey(NIDMResults, on_delete=models.CASCADE)


post_save.connect(basecollectionitem_created, sender=NIDMResultStatisticMap, weak=True)


class Atlas(Image):
    label_description_file = models.FileField(
        upload_to=upload_img_to,
        null=False,
        blank=False,
        storage=DoubleExtensionStorage(),
        verbose_name="FSL compatible label description file (.xml)",
    )

    class Meta:
        verbose_name_plural = "Atlases"


post_save.connect(basecollectionitem_created, sender=Atlas, weak=True)


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
        Image, related_name="image1", db_index=True, on_delete=models.CASCADE
    )
    image2 = models.ForeignKey(
        Image, related_name="image2", db_index=True, on_delete=models.CASCADE
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
    maps = models.ManyToManyField(StatisticMap, blank=True)
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

    def save(self, *args, **kwargs):
        if self.status == "active":
            for m in Metaanalysis.objects.filter(owner=self.owner).filter(
                status="active"
            ):
                if m.pk != self.pk:
                    m.status = "inactive"
                    m.save()
        super(Metaanalysis, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("statmaps:view_metaanalysis", args=[str(self.id)])
