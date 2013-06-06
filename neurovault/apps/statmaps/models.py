 # -*- coding: utf-8 -*-

from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
# from django.db.models.signals import post_save
# from django.dispatch import receiver
from neurosynth.base import imageutils
import os
from neurovault.apps.statmaps.storage import NiftiGzStorage
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, TagBase
import urllib2
from xml.etree import ElementTree
import datetime

class Collection(models.Model):
    name = models.CharField(max_length=200, unique = True, null=False)
    DOI = models.CharField(max_length=200, unique=True, blank=True, null=True, default=None)
    authors = models.CharField(max_length=200, blank=True, null=True)
    url = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)

    type_of_design = models.CharField(choices=[('blocked', 'blocked'), ('eventrelated', 'event_related'), ('hybridblockevent', 'hybrid block/event'), ('other', 'other')], max_length=200, blank=True, help_text="Blocked, event-related, hybrid, or other", null=True, verbose_name="ExperimentalDesign.type_of_design")
    number_of_imaging_runs = models.IntegerField(help_text="Number of imaging runs acquired", null=True, verbose_name="ExperimentalDesign.number_of_imaging_runs", blank=True)
    number_of_experimental_units = models.IntegerField(help_text="Number of blocks, trials or experimental units per imaging run", null=True, verbose_name="ExperimentalDesign.number_of_experimental_units", blank=True)
    length_of_runs = models.FloatField(help_text="Length of each imaging run in seconds", null=True, verbose_name="ExperimentalDesign.length_of_runs", blank=True)
    length_of_blocks = models.FloatField(help_text="For blocked designs, length of blocks in seconds", null=True, verbose_name="ExperimentalDesign.length_of_blocks", blank=True)
    length_of_trials = models.FloatField(help_text="Length of individual trials in seconds", null=True, verbose_name="ExperimentalDesign.length_of_trials", blank=True)
    optimization = models.NullBooleanField(help_text="Was the design optimized for efficiency", null=True, verbose_name="ExperimentalDesign.optimization", blank=True)
    optimization_method = models.CharField(help_text="What method was used for optimization?", verbose_name="ExperimentalDesign.optimization_method", max_length=200, null=True, blank=True)
    number_of_subjects = models.IntegerField(help_text="Number of subjects entering into the analysis", null=True, verbose_name="Participants.number_of_subjects", blank=True)
    subject_age_mean = models.FloatField(help_text="Mean age of subjects", null=True, verbose_name="Participants.subject_age_mean", blank=True)
    subject_age_min = models.FloatField(help_text="Minimum age of subjects", null=True, verbose_name="Participants.subject_age_min", blank=True)
    subject_age_max = models.FloatField(help_text="Maximum age of subjects", null=True, verbose_name="Participants.subject_age_max", blank=True)
    handedness = models.CharField(choices=[('right', 'right'), ('left', 'left'), ('both', 'both')], max_length=200, blank=True, help_text="Handedness of subjects", null=True, verbose_name="Participants.handedness")
    proportion_male_subjects = models.FloatField(help_text="The proportion of subjects who were male", null=True, verbose_name="Participants.proportion_male_subjects", blank=True)
    inclusion_exclusion_criteria = models.CharField(help_text="Additional inclusion/exclusion criteria, if any (including specific sampling strategies that limit inclusion to a specific group, such as laboratory members)", verbose_name="Participants.inclusion_exclusion_criteria", max_length=200, null=True, blank=True)
    number_of_rejected_subjects = models.IntegerField(help_text="Number of subjects scanned but rejected from analysis", null=True, verbose_name="Participants.number_of_rejected_subjects", blank=True)
    group_comparison = models.NullBooleanField(help_text="Was this study a comparison between subject groups?", null=True, verbose_name="Participants.group_comparison", blank=True)
    group_description = models.CharField(help_text="A description of the groups being compared", verbose_name="Participants.group_description", max_length=200, null=True, blank=True)
    scanner_make = models.CharField(help_text="Manufacturer of MRI scanner", verbose_name="MRI_acquisition.scanner_make", max_length=200, null=True, blank=True)
    scanner_model = models.CharField(help_text="Model of MRI scanner", verbose_name="MRI_acquisition.scanner_model", max_length=200, null=True, blank=True)
    field_strength = models.FloatField(help_text="Field strength of MRI scanner (in Tesla)", null=True, verbose_name="MRI_acquisition.field_strength", blank=True)
    pulse_sequence = models.CharField(help_text="Description of pulse sequence used for fMRI", verbose_name="MRI_acquisition.pulse_sequence", max_length=200, null=True, blank=True)
    parallel_imaging = models.CharField(help_text="Description of parallel imaging method and parameters", verbose_name="MRI_acquisition.parallel_imaging", max_length=200, null=True, blank=True)
    field_of_view = models.FloatField(help_text="Imaging field of view in millimeters", null=True, verbose_name="MRI_acquisition.field_of_view", blank=True)
    matrix_size = models.IntegerField(help_text="Matrix size for MRI acquisition", null=True, verbose_name="MRI_acquisition.matrix_size", blank=True)
    slice_thickness = models.FloatField(help_text="Distance between slices (includes skip or distance factor) in millimeters", null=True, verbose_name="MRI_acquisition.slice_thickness", blank=True)
    skip_factor = models.FloatField(help_text="The size of the skipped area between slices in millimeters", null=True, verbose_name="MRI_acquisition.skip_factor", blank=True)
    acquisition_orientation = models.CharField(help_text="The orientation of slices", verbose_name="MRI_acquisition.acquisition_orientation", max_length=200, null=True, blank=True)
    order_of_acquisition = models.CharField(choices=[('ascending', 'ascending'), ('descending', 'descending'), ('interleaved', 'interleaved')], max_length=200, blank=True, help_text="Order of acquisition of slices (ascending, descending, or interleaved)", null=True, verbose_name="MRI_acquisition.order_of_acquisition")
    repetition_time = models.FloatField(help_text="Repetition time (TR) in milliseconds", null=True, verbose_name="MRI_acquisition.repetition_time", blank=True)
    echo_time = models.FloatField(help_text="Echo time (TE) in milliseconds", null=True, verbose_name="MRI_acquisition.echo_time", blank=True)
    flip_angle = models.FloatField(help_text="Flip angle in degrees", null=True, verbose_name="MRI_acquisition.flip_angle", blank=True)
    software_package = models.CharField(help_text="If a single software package was used for all analyses, specify that here", verbose_name="Preprocessing.software_package", max_length=200, null=True, blank=True)
    software_version = models.CharField(help_text="Version of software package used", verbose_name="Preprocessing.software_version", max_length=200, null=True, blank=True)
    order_of_preprocessing_operations = models.CharField(help_text="Specify order of preprocessing operations", verbose_name="Preprocessing.order_of_preprocessing_operations", max_length=200, null=True, blank=True)
    quality_control = models.CharField(help_text="Describe quality control measures", verbose_name="Preprocessing.quality_control", max_length=200, null=True, blank=True)
    used_b0_unwarping = models.NullBooleanField(help_text="Was B0 distortion correction used?", null=True, verbose_name="Preprocessing.used_b0_unwarping", blank=True)
    b0_unwarping_software = models.CharField(help_text="Specify software used for distortion correction if different from the main package", verbose_name="Preprocessing.b0_unwarping_software", max_length=200, null=True, blank=True)
    used_slice_timing_correction = models.NullBooleanField(help_text="Was slice timing correction used?", null=True, verbose_name="Preprocessing.used_slice_timing_correction", blank=True)
    slice_timing_correction_software = models.CharField(help_text="Specify software used for slice timing correction if different from the main package", verbose_name="Preprocessing.slice_timing_correction_software", max_length=200, null=True, blank=True)
    used_motion_correction = models.NullBooleanField(help_text="Was motion correction used?", null=True, verbose_name="Preprocessing.used_motion_correction", blank=True)
    motion_correction_software = models.CharField(help_text="Specify software used for motion correction if different from the main package", verbose_name="Preprocessing.motion_correction_software", max_length=200, null=True, blank=True)
    motion_correction_reference = models.CharField(help_text="Reference scan used for motion correction", verbose_name="Preprocessing.motion_correction_reference", max_length=200, null=True, blank=True)
    motion_correction_metric = models.CharField(help_text="Similarity metric used for motion correction", verbose_name="Preprocessing.motion_correction_metric", max_length=200, null=True, blank=True)
    motion_correction_interpolation = models.CharField(help_text="Interpolation method used for motion correction", verbose_name="Preprocessing.motion_correction_interpolation", max_length=200, null=True, blank=True)
    used_motion_susceptibiity_correction = models.NullBooleanField(help_text="Was motion-susceptibility correction used?", null=True, verbose_name="Preprocessing.used_motion_susceptibiity_correction", blank=True)
    used_intersubject_registration = models.NullBooleanField(help_text="Were subjects registered to a common stereotactic space?", null=True, verbose_name="IntersubjectRegistration.used_intersubject_registration", blank=True)
    intersubject_registration_software = models.CharField(help_text="Specify software used for intersubject registration if different from main package", verbose_name="IntersubjectRegistration.intersubject_registration_software", max_length=200, null=True, blank=True)
    intersubject_transformation_type = models.CharField(choices=[('linear', 'linear'), ('nonlinear', 'nonlinear')], max_length=200, blank=True, help_text="Was linear or nonlinear registration used?", null=True, verbose_name="IntersubjectRegistration.intersubject_transformation_type")
    nonlinear_transform_type = models.CharField(help_text="If nonlinear registration was used, describe transform method", verbose_name="IntersubjectRegistration.nonlinear_transform_type", max_length=200, null=True, blank=True)
    transform_similarity_metric = models.CharField(help_text="Similarity metric used for intersubject registration", verbose_name="IntersubjectRegistration.transform_similarity_metric", max_length=200, null=True, blank=True)
    interpolation_method = models.CharField(help_text="Interpolation method used for intersubject registration", verbose_name="IntersubjectRegistration.interpolation_method", max_length=200, null=True, blank=True)
    object_image_type = models.CharField(help_text="What type of image was used to determine the transformation to the atlas?", verbose_name="IntersubjectRegistration.object_image_type", max_length=200, null=True, blank=True)
    functional_coregistered_to_structural = models.NullBooleanField(help_text="Were the functional images coregistered to the subject's structural image?", null=True, verbose_name="IntersubjectRegistration.functional_coregistered_to_structural", blank=True)
    functional_coregistration_method = models.CharField(help_text="Method used to coregister functional to structural images", verbose_name="IntersubjectRegistration.functional_coregistration_method", max_length=200, null=True, blank=True)
    coordinate_space = models.CharField(choices=[('mni', 'MNI'), ('talairach', 'Talairach'), ('mni2tal', 'MNI2Tal'), ('other', 'other')], max_length=200, blank=True, help_text="Name of coordinate space for registration target", null=True, verbose_name="IntersubjectRegistration.coordinate_space")
    target_template_image = models.CharField(help_text="Name of target template image", verbose_name="IntersubjectRegistration.target_template_image", max_length=200, null=True, blank=True)
    target_resolution = models.FloatField(help_text="Voxel size of target template in millimeters", null=True, verbose_name="IntersubjectRegistration.target_resolution", blank=True)
    used_smoothing = models.NullBooleanField(help_text="Was spatial smoothing applied?", null=True, verbose_name="IntersubjectRegistration.used_smoothing", blank=True)
    smoothing_type = models.CharField(help_text="Describe the type of smoothing applied", verbose_name="IntersubjectRegistration.smoothing_type", max_length=200, null=True, blank=True)
    smoothing_fwhm = models.FloatField(help_text="The full-width at half-maximum of the smoothing kernel in millimeters", null=True, verbose_name="IntersubjectRegistration.smoothing_fwhm", blank=True)
    resampled_voxel_size = models.FloatField(help_text="Voxel size in mm of the resampled, atlas-space images", null=True, verbose_name="IntersubjectRegistration.resampled_voxel_size", blank=True)
    intrasubject_model_type = models.CharField(help_text="Type of model used (e.g., regression)", verbose_name="IndividualSubjectModeling.intrasubject_model_type", max_length=200, null=True, blank=True)
    intrasubject_estimation_type = models.CharField(help_text="Estimation method used for model (e.g., OLS, generalized least squares)", verbose_name="IndividualSubjectModeling.intrasubject_estimation_type", max_length=200, null=True, blank=True)
    intrasubject_modeling_software = models.CharField(help_text="Software used for intrasubject modeling if different from overall package", verbose_name="IndividualSubjectModeling.intrasubject_modeling_software", max_length=200, null=True, blank=True)
    hemodynamic_response_function = models.CharField(help_text="Nature of HRF model", verbose_name="IndividualSubjectModeling.hemodynamic_response_function", max_length=200, null=True, blank=True)
    used_temporal_derivatives = models.NullBooleanField(help_text="Were temporal derivatives included?", null=True, verbose_name="IndividualSubjectModeling.used_temporal_derivatives", blank=True)
    used_dispersion_derivatives = models.NullBooleanField(help_text="Were dispersion derivatives included?", null=True, verbose_name="IndividualSubjectModeling.used_dispersion_derivatives", blank=True)
    used_motion_regressors = models.NullBooleanField(help_text="Were motion regressors included?", null=True, verbose_name="IndividualSubjectModeling.used_motion_regressors", blank=True)
    used_reaction_time_regressor = models.NullBooleanField(help_text="Was a reaction time regressor included?", null=True, verbose_name="IndividualSubjectModeling.used_reaction_time_regressor", blank=True)
    used_orthogonalization = models.NullBooleanField(help_text="Were any regressors specifically orthogonalized with respect to others?", null=True, verbose_name="IndividualSubjectModeling.used_orthogonalization", blank=True)
    orthogonalization_description = models.CharField(help_text="If orthogonalization was used, describe here", verbose_name="IndividualSubjectModeling.orthogonalization_description", max_length=200, null=True, blank=True)
    used_high_pass_filter = models.NullBooleanField(help_text="Was high pass filtering applied?", null=True, verbose_name="IndividualSubjectModeling.used_high_pass_filter", blank=True)
    high_pass_filter_method = models.CharField(help_text="Describe method used for high pass filtering", verbose_name="IndividualSubjectModeling.high_pass_filter_method", max_length=200, null=True, blank=True)
    autocorrelation_model = models.CharField(help_text="What autocorrelation model was used (or 'none' of none was used)", verbose_name="IndividualSubjectModeling.autocorrelation_model", max_length=200, null=True, blank=True)
    contrast_definition = models.CharField(help_text="Exactly what terms are subtracted from what? Define these in terms of task or stimulus conditions (e.g., 'one-back task with objects versus zero-back task with objects') instead of underlying psychological concepts (e.g., 'working memory').", verbose_name="IndividualSubjectModeling.contrast_definition", max_length=200, null=True, blank=True)
    contrast_definition_cogatlas = models.CharField(help_text="Link to Cognitive Atlas definition of this contrast", verbose_name="IndividualSubjectModeling.contrast_definition_cogatlas", max_length=200, null=True, blank=True)
    group_model_type = models.CharField(help_text="Type of group model used (e.g., regression)", verbose_name="GroupModeling.group_model_type", max_length=200, null=True, blank=True)
    group_estimation_type = models.CharField(help_text="Estimation method used for group model (e.g., OLS, generalized least squares)", verbose_name="GroupModeling.group_estimation_type", max_length=200, null=True, blank=True)
    group_modeling_software = models.CharField(help_text="Software used for group modeling if different from overall package", verbose_name="GroupModeling.group_modeling_software", max_length=200, null=True, blank=True)
    group_inference_type = models.CharField(choices=[('randommixedeffects', 'random/mixed effects'), ('fixedeffects', 'fixed effects')], max_length=200, blank=True, help_text="Type of inference for group model", null=True, verbose_name="GroupModeling.group_inference_type")
    group_model_multilevel = models.CharField(help_text="If more than 2-levels, describe the levels and assumptions of the model (e.g. are variances assumed equal between groups)", verbose_name="GroupModeling.group_model_multilevel", max_length=200, null=True, blank=True)
    group_repeated_measures = models.NullBooleanField(help_text="Was this a repeated measures design at the group level?", null=True, verbose_name="GroupModeling.group_repeated_measures", blank=True)
    group_repeated_measures_method = models.CharField(help_text="If multiple measurements per subject, list method to account for within subject correlation, exact assumptions made about correlation/variance", verbose_name="GroupModeling.group_repeated_measures_method", max_length=200, null=True, blank=True)
    group_statistic_type = models.CharField(help_text=("Type of statistic that is the basis of the inference; e.g. 'Z','T','F','X2','PostProb',"
                                                       "'NonparametricP','MonteCarloP'"), verbose_name="GroupInference.group_statistic_type",
                                                       max_length=200, null=True, blank=True)
    group_statistic_parameters = models.FloatField(help_text="Parameters of the null distribution of the test statisic, typically degrees of freedom (should be clear from the test statistic what these are).", null=True, verbose_name="GroupInference.group_statistic_parameters", blank=True)
    group_smoothness_fwhm = models.CharField(help_text="Noise smoothness for statistical inference; this is the estimated smoothness used with Random Field Theory or a simulation-based inference method.", verbose_name="GroupInference.group_smoothness_fwhm", max_length=200, null=True, blank=True)

    def get_absolute_url(self):
        return reverse('collection_details', args=[str(self.id)])
    
    def __unicode__(self):
        return self.name
    
    def save(self):

        # Save the file before the rest of the data so we can convert it to json
        if self.DOI:
            try:
                self.name, self.authors, self.url, _ = getPaperProperties(self.DOI)
            except:
                pass
            
        super(Collection, self).save()
        
def getPaperProperties(doi):
    xmlurl = 'http://doi.crossref.org/servlet/query'
    xmlpath = xmlurl + '?pid=k.j.gorgolewski@sms.ed.ac.uk&format=unixref&id=' + urllib2.quote(doi)
    xml_str = urllib2.urlopen(xmlpath).read()
    doc = ElementTree.fromstring(xml_str)
    if len(doc.getchildren()) == 0 or len(doc.findall('.//crossref/error')) > 0:
        raise Exception("DOI %s was not found" % doi)
    title = doc.findall('.//title')[0].text
    authors = [author.findall('given_name')[0].text + " " + author.findall('surname')[0].text for author in doc.findall('.//contributors/person_name')]
    if len(authors) > 1:
        authors = ", ".join(authors[:-1]) + " and " + authors[-1]
    url = doc.findall('.//doi_data/resource')[0].text
    date_node = doc.findall('.//publication_date')[0]
    if len(date_node.findall('day')) > 0:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         int(date_node.findall('month')[0].text),
                                         int(date_node.findall('day')[0].text))
    elif len(date_node.findall('month')) > 0:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         int(date_node.findall('month')[0].text),
                                         1)
    else:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         1,
                                         1)
    return title, authors, url, publication_date

def upload_to(instance, filename):
    return "statmaps/%s/%s"%(instance.collection.name, filename)

class LowerCaseTag(TagBase):
    value = models.CharField(max_length=200, blank=True)

class ValueTaggedItem(GenericTaggedItemBase):
    tag = models.ForeignKey(LowerCaseTag, related_name="tagged_items")

class StatMap(models.Model):
    collection = models.ForeignKey(Collection)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to=upload_to, null=False, blank=False, storage=NiftiGzStorage())
    hdr_file = models.FileField(upload_to=upload_to, blank=True, storage=NiftiGzStorage())
    json_path = models.CharField(max_length=200, null=False, blank=True)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    tags = TaggableManager(through=ValueTaggedItem, blank=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        unique_together = ("collection", "name")

    def save(self):

        # Save the file before the rest of the data so we can convert it to json
        if self.file and not os.path.exists(self.file.path):
            self.file.save(self.file.name, self.file, save = False)
        if self.hdr_file and not os.path.exists(self.hdr_file.path):
            self.hdr_file.save(self.hdr_file.name, self.hdr_file, save = False)
        # Convert binary image to JSON using neurosynth
#         try:
        if os.path.exists(self.file.path):
            json_file = self.file.path + '.json'
#                 try:
            imageutils.img_to_json(self.file.path, swap=True, save=json_file)
            self.json_path = self.file.url + '.json'
#                 except Exception, e:
#                     pass
#         except Exception, e:
#             pass
        super(StatMap, self).save()

