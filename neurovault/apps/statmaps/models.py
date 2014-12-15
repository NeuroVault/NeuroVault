 # -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from neurovault.apps.statmaps.storage import NiftiGzStorage
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, TagBase
from xml import etree
from datetime import datetime
import os
import urllib2
from dirtyfields import DirtyFieldsMixin
from django.core.files import File
import nibabel as nb
from django.core.exceptions import ValidationError
from neurovault import settings
from polymorphic.polymorphic_model import PolymorphicModel
# from django.db.models.signals import post_save
# from django.dispatch import receiver

class Collection(models.Model):
    name = models.CharField(max_length=200, unique = True, null=False, verbose_name="Name of collection")
    DOI = models.CharField(max_length=200, unique=True, blank=True, null=True, default=None, verbose_name="DOI of the corresponding paper")
    authors = models.CharField(max_length=5000, blank=True, null=True)
    url = models.CharField(max_length=200, blank=True, null=True)
    journal_name = models.CharField(max_length=200, blank=True, null=True, default=None)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User)
    contributors = models.ManyToManyField(User,related_name="collection_contributors",related_query_name="contributor", blank=True,help_text="Select other NeuroVault users to add as contributes to the collection.  Contributors can add, edit and delete images in the collection.",verbose_name="Contributors")
    private = models.BooleanField(choices=((False, 'Public (The collection will be accessible by anyone and all the data in it will be distributed under CC0 license)'),
                                           (True, 'Private (The collection will be not listed in the NeuroVault index. It will be possible to shared it with others at a private URL.)')), default=False,verbose_name="Accesibility")
    private_token = models.CharField(max_length=8,blank=True,null=True,unique=True,db_index=True, default=None)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    type_of_design = models.CharField(choices=[('blocked', 'blocked'), ('eventrelated', 'event_related'), ('hybridblockevent', 'hybrid block/event'), ('other', 'other')], max_length=200, blank=True, help_text="Blocked, event-related, hybrid, or other", null=True, verbose_name="Type of design")
    number_of_imaging_runs = models.IntegerField(help_text="Number of imaging runs acquired", null=True, verbose_name="No. of imaging runs", blank=True)
    number_of_experimental_units = models.IntegerField(help_text="Number of blocks, trials or experimental units per imaging run", null=True, verbose_name="No. of experimental units", blank=True)
    length_of_runs = models.FloatField(help_text="Length of each imaging run in seconds", null=True, verbose_name="Length of runs", blank=True)
    length_of_blocks = models.FloatField(help_text="For blocked designs, length of blocks in seconds", null=True, verbose_name="Length of blocks", blank=True)
    length_of_trials = models.FloatField(help_text="Length of individual trials in seconds", null=True, verbose_name="Length of trials", blank=True)
    optimization = models.NullBooleanField(help_text="Was the design optimized for efficiency", null=True, verbose_name="Optimization?", blank=True)
    optimization_method = models.CharField(help_text="What method was used for optimization?", verbose_name="Optimization method", max_length=200, null=True, blank=True)
    number_of_subjects = models.IntegerField(help_text="Number of subjects entering into the analysis", null=True, verbose_name="No. of subjects", blank=True)
    subject_age_mean = models.FloatField(help_text="Mean age of subjects", null=True, verbose_name="Subject age mean", blank=True)
    subject_age_min = models.FloatField(help_text="Minimum age of subjects", null=True, verbose_name="Subject age min", blank=True)
    subject_age_max = models.FloatField(help_text="Maximum age of subjects", null=True, verbose_name="Subject age max", blank=True)
    handedness = models.CharField(choices=[('right', 'right'), ('left', 'left'), ('both', 'both')], max_length=200, blank=True, help_text="Handedness of subjects", null=True, verbose_name="Handedness")
    proportion_male_subjects = models.FloatField(help_text="The proportion of subjects who were male", null=True, verbose_name="Prop. male subjects", blank=True)
    inclusion_exclusion_criteria = models.CharField(help_text="Additional inclusion/exclusion criteria, if any (including specific sampling strategies that limit inclusion to a specific group, such as laboratory members)", verbose_name="Inclusion / exclusion criteria", max_length=200, null=True, blank=True)
    number_of_rejected_subjects = models.IntegerField(help_text="Number of subjects scanned but rejected from analysis", null=True, verbose_name="No. of rejected subjects", blank=True)
    group_comparison = models.NullBooleanField(help_text="Was this study a comparison between subject groups?", null=True, verbose_name="Group comparison?", blank=True)
    group_description = models.CharField(help_text="A description of the groups being compared", verbose_name="Group description", max_length=200, null=True, blank=True)
    scanner_make = models.CharField(help_text="Manufacturer of MRI scanner", verbose_name="Scanner make", max_length=200, null=True, blank=True)
    scanner_model = models.CharField(help_text="Model of MRI scanner", verbose_name="Scanner model", max_length=200, null=True, blank=True)
    field_strength = models.FloatField(help_text="Field strength of MRI scanner (in Tesla)", null=True, verbose_name="Field strength", blank=True)
    pulse_sequence = models.CharField(help_text="Description of pulse sequence used for fMRI", verbose_name="Pulse sequence", max_length=200, null=True, blank=True)
    parallel_imaging = models.CharField(help_text="Description of parallel imaging method and parameters", verbose_name="Parallel imaging", max_length=200, null=True, blank=True)
    field_of_view = models.FloatField(help_text="Imaging field of view in millimeters", null=True, verbose_name="Field of view", blank=True)
    matrix_size = models.IntegerField(help_text="Matrix size for MRI acquisition", null=True, verbose_name="Matrix size", blank=True)
    slice_thickness = models.FloatField(help_text="Distance between slices (includes skip or distance factor) in millimeters", null=True, verbose_name="Slice thickness", blank=True)
    skip_factor = models.FloatField(help_text="The size of the skipped area between slices in millimeters", null=True, verbose_name="Skip factor", blank=True)
    acquisition_orientation = models.CharField(help_text="The orientation of slices", verbose_name="Acquisition orientation", max_length=200, null=True, blank=True)
    order_of_acquisition = models.CharField(choices=[('ascending', 'ascending'), ('descending', 'descending'), ('interleaved', 'interleaved')], max_length=200, blank=True, help_text="Order of acquisition of slices (ascending, descending, or interleaved)", null=True, verbose_name="Order of acquisition")
    repetition_time = models.FloatField(help_text="Repetition time (TR) in milliseconds", null=True, verbose_name="Repetition time", blank=True)
    echo_time = models.FloatField(help_text="Echo time (TE) in milliseconds", null=True, verbose_name="Echo time", blank=True)
    flip_angle = models.FloatField(help_text="Flip angle in degrees", null=True, verbose_name="Flip angle", blank=True)
    software_package = models.CharField(help_text="If a single software package was used for all analyses, specify that here", verbose_name="Software package", max_length=200, null=True, blank=True)
    software_version = models.CharField(help_text="Version of software package used", verbose_name="Software version", max_length=200, null=True, blank=True)
    order_of_preprocessing_operations = models.CharField(help_text="Specify order of preprocessing operations", verbose_name="Order of preprocessing", max_length=200, null=True, blank=True)
    quality_control = models.CharField(help_text="Describe quality control measures", verbose_name="Quality control", max_length=200, null=True, blank=True)
    used_b0_unwarping = models.NullBooleanField(help_text="Was B0 distortion correction used?", null=True, verbose_name="Used B0 unwarping?", blank=True)
    b0_unwarping_software = models.CharField(help_text="Specify software used for distortion correction if different from the main package", verbose_name="B0 unwarping software", max_length=200, null=True, blank=True)
    used_slice_timing_correction = models.NullBooleanField(help_text="Was slice timing correction used?", null=True, verbose_name="Slice timing correction?", blank=True)
    slice_timing_correction_software = models.CharField(help_text="Specify software used for slice timing correction if different from the main package", verbose_name="Slice timing correction software", max_length=200, null=True, blank=True)
    used_motion_correction = models.NullBooleanField(help_text="Was motion correction used?", null=True, verbose_name="Motion correction?", blank=True)
    motion_correction_software = models.CharField(help_text="Specify software used for motion correction if different from the main package", verbose_name="Motion correction software", max_length=200, null=True, blank=True)
    motion_correction_reference = models.CharField(help_text="Reference scan used for motion correction", verbose_name="Motion correction reference", max_length=200, null=True, blank=True)
    motion_correction_metric = models.CharField(help_text="Similarity metric used for motion correction", verbose_name="Motion correction metric", max_length=200, null=True, blank=True)
    motion_correction_interpolation = models.CharField(help_text="Interpolation method used for motion correction", verbose_name="Motion correction interpolation", max_length=200, null=True, blank=True)
    used_motion_susceptibiity_correction = models.NullBooleanField(help_text="Was motion-susceptibility correction used?", null=True, verbose_name="Motion susceptibility correction?", blank=True)
    used_intersubject_registration = models.NullBooleanField(help_text="Were subjects registered to a common stereotactic space?", null=True, verbose_name="Intersubject registration?", blank=True)
    intersubject_registration_software = models.CharField(help_text="Specify software used for intersubject registration if different from main package", verbose_name="Registration software", max_length=200, null=True, blank=True)
    intersubject_transformation_type = models.CharField(choices=[('linear', 'linear'), ('nonlinear', 'nonlinear')], max_length=200, blank=True, help_text="Was linear or nonlinear registration used?", null=True, verbose_name="Intersubject transformation type")
    nonlinear_transform_type = models.CharField(help_text="If nonlinear registration was used, describe transform method", verbose_name="Nonlinear transform type", max_length=200, null=True, blank=True)
    transform_similarity_metric = models.CharField(help_text="Similarity metric used for intersubject registration", verbose_name="Transform similarity metric", max_length=200, null=True, blank=True)
    interpolation_method = models.CharField(help_text="Interpolation method used for intersubject registration", verbose_name="Interpolation method", max_length=200, null=True, blank=True)
    object_image_type = models.CharField(help_text="What type of image was used to determine the transformation to the atlas?", verbose_name="Object image type", max_length=200, null=True, blank=True)
    functional_coregistered_to_structural = models.NullBooleanField(help_text="Were the functional images coregistered to the subject's structural image?", null=True, verbose_name="Coregistered to structural?", blank=True)
    functional_coregistration_method = models.CharField(help_text="Method used to coregister functional to structural images", verbose_name="Coregistration method", max_length=200, null=True, blank=True)
    coordinate_space = models.CharField(choices=[('mni', 'MNI'), ('talairach', 'Talairach'), ('mni2tal', 'MNI2Tal'), ('other', 'other')], max_length=200, blank=True, help_text="Name of coordinate space for registration target", null=True, verbose_name="Coordinate space")
    target_template_image = models.CharField(help_text="Name of target template image", verbose_name="Target template image", max_length=200, null=True, blank=True)
    target_resolution = models.FloatField(help_text="Voxel size of target template in millimeters", null=True, verbose_name="Target resolution", blank=True)
    used_smoothing = models.NullBooleanField(help_text="Was spatial smoothing applied?", null=True, verbose_name="Used smoothing?", blank=True)
    smoothing_type = models.CharField(help_text="Describe the type of smoothing applied", verbose_name="Type of smoothing", max_length=200, null=True, blank=True)
    smoothing_fwhm = models.FloatField(help_text="The full-width at half-maximum of the smoothing kernel in millimeters", null=True, verbose_name="Smoothing FWHM", blank=True)
    resampled_voxel_size = models.FloatField(help_text="Voxel size in mm of the resampled, atlas-space images", null=True, verbose_name="Resampled voxel size", blank=True)
    intrasubject_model_type = models.CharField(help_text="Type of model used (e.g., regression)", verbose_name="Model type", max_length=200, null=True, blank=True)
    intrasubject_estimation_type = models.CharField(help_text="Estimation method used for model (e.g., OLS, generalized least squares)", verbose_name="Estimation type", max_length=200, null=True, blank=True)
    intrasubject_modeling_software = models.CharField(help_text="Software used for intrasubject modeling if different from overall package", verbose_name="Modeling software", max_length=200, null=True, blank=True)
    hemodynamic_response_function = models.CharField(help_text="Nature of HRF model", verbose_name="Hemodynamic response function", max_length=200, null=True, blank=True)
    used_temporal_derivatives = models.NullBooleanField(help_text="Were temporal derivatives included?", null=True, verbose_name="Temporal derivatives?", blank=True)
    used_dispersion_derivatives = models.NullBooleanField(help_text="Were dispersion derivatives included?", null=True, verbose_name="Dispersion derivatives?", blank=True)
    used_motion_regressors = models.NullBooleanField(help_text="Were motion regressors included?", null=True, verbose_name="Motion regressors?", blank=True)
    used_reaction_time_regressor = models.NullBooleanField(help_text="Was a reaction time regressor included?", null=True, verbose_name="Reaction time regressor?", blank=True)
    used_orthogonalization = models.NullBooleanField(help_text="Were any regressors specifically orthogonalized with respect to others?", null=True, verbose_name="Orthogonalization?", blank=True)
    orthogonalization_description = models.CharField(help_text="If orthogonalization was used, describe here", verbose_name="Orthogonalization description", max_length=200, null=True, blank=True)
    used_high_pass_filter = models.NullBooleanField(help_text="Was high pass filtering applied?", null=True, verbose_name="High-pass filter?", blank=True)
    high_pass_filter_method = models.CharField(help_text="Describe method used for high pass filtering", verbose_name="High-pass filtering method", max_length=200, null=True, blank=True)
    autocorrelation_model = models.CharField(help_text="What autocorrelation model was used (or 'none' of none was used)", verbose_name="Autocorrelation method", max_length=200, null=True, blank=True)
    group_model_type = models.CharField(help_text="Type of group model used (e.g., regression)", verbose_name="Group model type", max_length=200, null=True, blank=True)
    group_estimation_type = models.CharField(help_text="Estimation method used for group model (e.g., OLS, generalized least squares)", verbose_name="Group estimation type", max_length=200, null=True, blank=True)
    group_modeling_software = models.CharField(help_text="Software used for group modeling if different from overall package", verbose_name="Group modeling software", max_length=200, null=True, blank=True)
    group_inference_type = models.CharField(choices=[('randommixedeffects', 'random/mixed effects'), ('fixedeffects', 'fixed effects')], max_length=200, blank=True, help_text="Type of inference for group model", null=True, verbose_name="Group inference type")
    group_model_multilevel = models.CharField(help_text="If more than 2-levels, describe the levels and assumptions of the model (e.g. are variances assumed equal between groups)", verbose_name="Multilevel modeling", max_length=200, null=True, blank=True)
    group_repeated_measures = models.NullBooleanField(help_text="Was this a repeated measures design at the group level?", null=True, verbose_name="Repeated measures", blank=True)
    group_repeated_measures_method = models.CharField(help_text="If multiple measurements per subject, list method to account for within subject correlation, exact assumptions made about correlation/variance", verbose_name="Repeated measures method", max_length=200, null=True, blank=True)


    def get_absolute_url(self):
        return_cid = self.id
        if self.private:
            return_cid = self.private_token
        return reverse('collection_details', args=[str(return_cid)])

    def __unicode__(self):
        return self.name

    def save(self):
        if self.DOI != None and self.DOI.strip() == "":
            self.DOI = None
        if self.private_token != None and self.private_token.strip() == "":
            self.private_token = None
        super(Collection, self).save()

    class Meta:
        app_label = 'statmaps'


def upload_to(instance, filename):
    return os.path.join('images',str(instance.collection.id), filename)


class KeyValueTag(TagBase):
    value = models.CharField(max_length=200, blank=True)


class ValueTaggedItem(GenericTaggedItemBase):
    tag = models.ForeignKey(KeyValueTag, related_name="tagged_items")


class Image(PolymorphicModel):

    collection = models.ForeignKey(Collection)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(blank=False)
    file = models.FileField(upload_to=upload_to, null=False, blank=False, storage=NiftiGzStorage(), verbose_name='File with the unthresholded map (.img, .nii, .nii.gz)')
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    tags = TaggableManager(through=ValueTaggedItem, blank=True)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return_args = [str(self.id)]
        url_name = 'image_details'
        if self.collection.private:
            return_args.insert(0,str(self.collection.private_token))
            url_name = 'private_image_details'
        return reverse(url_name, args=return_args)

    def set_name(self, new_name):
        self.name = new_name

    class Meta:
        unique_together = ("collection", "name")

    def save(self):
        self.collection.modify_date = datetime.now()
        self.collection.save()
        super(Image, self).save()

    def delete(self):
        self.collection.modify_date = datetime.now()
        self.collection.save()
        super(Image, self).delete()

    @classmethod
    def create(cls, my_file, my_file_name, my_name, my_desc, my_collection_pk, my_map_type):
        my_collection = Collection.objects.get(pk=my_collection_pk)

        # Copy the nifti file into the proper location
        image = cls(description=my_desc, name=my_name, collection=my_collection)
        f = open(my_file)
        niftiFile = File(f);
        image.file.save(my_file_name, niftiFile);

        # If a .img file was loaded then load the correspoding .hdr file as well
        _, ext = os.path.splitext(my_file_name)
        print ext
        if ext in ['.img']:
            f = open(my_file[:-3] + "hdr")
            hdrFile = File(f);
            image.hdr_file.save(my_file_name[:-3] + "hdr", hdrFile);

        image.map_type = my_map_type;

        #create JSON file for neurosynth viewer
        if os.path.exists(image.file.path):
            nifti_gz_file = ".".join(image.file.path.split(".")[:-1]) + '.nii.gz'
            nii = nb.load(image.file.path)
            nb.save(nii, nifti_gz_file)
            f = open(nifti_gz_file)
            image.nifti_gz_file.save(nifti_gz_file.split(os.path.sep)[-1], File(f), save=False)

        image.save();

        return image

class StatisticMap(Image):
    Z = 'Z'
    T = 'T'
    F = 'F'
    X2 = 'X2'
    P = 'P'
    OTHER = 'Other'
    MAP_TYPE_CHOICES = (
        (T, 'T map'),
        (Z, 'Z map'),
        (F, 'F map'),
        (X2, 'Chi squared map'),
        (P, 'P map (given null hypothesis)'),
        (OTHER, 'Other'),
    )
    map_type = models.CharField(help_text=("Type of statistic that is the basis of the inference"), verbose_name="Map type",
                                                       max_length=200, null=False, blank=False, choices=MAP_TYPE_CHOICES)
    statistic_parameters = models.FloatField(help_text="Parameters of the null distribution of the test statisic, typically degrees of freedom (should be clear from the test statistic what these are).", null=True, verbose_name="Statistic parameters", blank=True)
    smoothness_fwhm = models.FloatField(help_text="Noise smoothness for statistical inference; this is the estimated smoothness used with Random Field Theory or a simulation-based inference method.", verbose_name="Smoothness FWHM", null=True, blank=True)
    contrast_definition = models.CharField(help_text="Exactly what terms are subtracted from what? Define these in terms of task or stimulus conditions (e.g., 'one-back task with objects versus zero-back task with objects') instead of underlying psychological concepts (e.g., 'working memory').", verbose_name="Contrast definition", max_length=200, null=True, blank=True)
    contrast_definition_cogatlas = models.CharField(help_text="Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast", verbose_name="Cognitive Atlas definition", max_length=200, null=True, blank=True)

class Atlas(Image):
    label_description_file = models.FileField(upload_to=upload_to,
                                              null=False, blank=False,
                                              storage=NiftiGzStorage(),
                                              verbose_name='FSL compatible label description file (.xml)')


class NIDMResults(Image):
    ttl_file = models.FileField(upload_to=upload_to,
                                null=False, blank=False,
                                storage=NiftiGzStorage(),
                                verbose_name='Turtle serialization of NIDM Results (.ttl)')

    def save(self):
        self._unpack_nidm_zip()
        self._update_ttl_paths()
        self._update_nidm_zip()
        super(NIDMResults, self).save()
