import os
import re
import shutil
import subprocess
from subprocess import CalledProcessError
from cStringIO import StringIO

import nibabel as nb
import numpy as np
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.models import (
    ModelMultipleChoiceField
)

# from form_utils.forms import BetterModelForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Button
from crispy_forms.bootstrap import TabHolder, Tab

from .models import Collection, Image, User, StatisticMap, BaseStatisticMap, \
    Atlas, NIDMResults, NIDMResultStatisticMap

from django.forms.forms import Form
from django.forms.fields import FileField
import tempfile
from neurovault.apps.statmaps.utils import (
    split_filename, get_paper_properties,
    detect_4D, split_4D_to_3D, memory_uploadfile,
    is_thresholded, not_in_mni,
    splitext_nii_gz)
from neurovault.apps.statmaps.nidm_results import NIDMUpload
from django import forms
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.forms.utils import flatatt
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
from django.forms.widgets import HiddenInput
from neurovault import settings
from gzip import GzipFile
from file_resubmit.admin import AdminResubmitFileWidget
from guardian.shortcuts import get_objects_for_user

# Create the form class.
collection_fieldsets = [
    ('Essentials', {'fields': ['name',
                               'DOI',
                               'description',
                               'full_dataset_url',
                               'contributors',
                               'private'],
                    'legend': 'Essentials'}),
    ('Participants', {'fields': ['subject_age_mean',
                                 'subject_age_min',
                                 'subject_age_max',
                                 'handedness',
                                 'proportion_male_subjects',
                                 'inclusion_exclusion_criteria',
                                 'number_of_rejected_subjects',
                                 'group_comparison',
                                 'group_description'],
                      'legend': 'Subjects'}),
    ('ExperimentalDesign', {
     'fields': ['type_of_design',
                'number_of_imaging_runs',
                'number_of_experimental_units',
                'length_of_runs',
                'length_of_blocks',
                'length_of_trials',
                'optimization',
                'optimization_method'],
     'legend': 'Design'}),
    ('MRI_acquisition', {'fields': ['scanner_make',
                                    'scanner_model',
                                    'field_strength',
                                    'pulse_sequence',
                                    'parallel_imaging',
                                    'field_of_view',
                                    'matrix_size',
                                    'slice_thickness',
                                    'skip_distance',
                                    'acquisition_orientation',
                                    'order_of_acquisition',
                                    'repetition_time',
                                    'echo_time',
                                    'flip_angle'],
                         'legend': 'Acquisition'}),
    ('IntersubjectRegistration', {'fields': [
                                  'used_intersubject_registration',
                                  'intersubject_registration_software',
                                  'intersubject_transformation_type',
                                  'nonlinear_transform_type',
                                  'transform_similarity_metric',
                                  'interpolation_method',
                                  'object_image_type',
                                  'functional_coregistered_to_structural',
                                  'functional_coregistration_method',
                                  'coordinate_space',
                                  'target_template_image',
                                  'target_resolution',
                                  'used_smoothing',
                                  'smoothing_type',
                                  'smoothing_fwhm',
                                  'resampled_voxel_size'],
                                  'legend': 'Registration'}),
    ('Preprocessing', {
     'fields': ['software_package',
                'software_version',
                'order_of_preprocessing_operations',
                'quality_control',
                'used_b0_unwarping',
                'b0_unwarping_software',
                'used_slice_timing_correction',
                'slice_timing_correction_software',
                'used_motion_correction',
                'motion_correction_software',
                'motion_correction_reference',
                'motion_correction_metric',
                'motion_correction_interpolation',
                'used_motion_susceptibiity_correction'],
     'legend': 'Preprocessing'}),
    ('IndividualSubjectModeling', {
     'fields': ['intrasubject_model_type',
                'intrasubject_estimation_type',
                'intrasubject_modeling_software',
                'hemodynamic_response_function',
                'used_temporal_derivatives',
                'used_dispersion_derivatives',
                'used_motion_regressors',
                'used_reaction_time_regressor',
                'used_orthogonalization',
                'orthogonalization_description',
                'used_high_pass_filter',
                'high_pass_filter_method',
                'autocorrelation_model'],
     'legend': '1st Level'}),
    ('GroupModeling', {
     'fields': ['group_model_type',
                'group_estimation_type',
                'group_modeling_software',
                'group_inference_type',
                'group_model_multilevel',
                'group_repeated_measures',
                'group_repeated_measures_method'],
     'legend': '2nd Level'}),
]


collection_row_attrs = {
    'echo_time': {'priority': 1},
    'number_of_rejected_subjects': {'priority': 2},
    'inclusion_exclusion_criteria': {'priority': 3},
    'group_comparison': {'priority': 1},
    'subject_age_max': {'priority': 2},
    'used_dispersion_derivatives': {'priority': 3},
    'used_intersubject_registration': {'priority': 1},
    'intrasubject_estimation_type': {'priority': 1},
    'field_of_view': {'priority': 2},
    'order_of_preprocessing_operations': {'priority': 2},
    'smoothing_type': {'priority': 1},
    'subject_age_min': {'priority': 2},
    'length_of_blocks': {'priority': 2},
    'used_orthogonalization': {'priority': 1},
    'used_b0_unwarping': {'priority': 2},
    'used_temporal_derivatives': {'priority': 2},
    'software_package': {'priority': 1},
    'scanner_model': {'priority': 1},
    'high_pass_filter_method': {'priority': 2},
    'proportion_male_subjects': {'priority': 2},
    'number_of_imaging_runs': {'priority': 2},
    'interpolation_method': {'priority': 2},
    'group_repeated_measures_method': {'priority': 3},
    'motion_correction_software': {'priority': 3},
    'used_motion_regressors': {'priority': 2},
    'functional_coregistered_to_structural': {'priority': 2},
    'motion_correction_interpolation': {'priority': 3},
    'optimization_method': {'priority': 3},
    'hemodynamic_response_function': {'priority': 2},
    'group_model_type': {'priority': 1},
    'used_slice_timing_correction': {'priority': 1},
    'intrasubject_modeling_software': {'priority': 2},
    'target_template_image': {'priority': 2},
    'resampled_voxel_size': {'priority': 3},
    'object_image_type': {'priority': 1},
    'group_description': {'priority': 2},
    'functional_coregistration_method': {'priority': 3},
    'length_of_trials': {'priority': 2},
    'handedness': {'priority': 2},
    'used_motion_correction': {'priority': 1},
    'pulse_sequence': {'priority': 1},
    'used_high_pass_filter': {'priority': 1},
    'orthogonalization_description': {'priority': 2},
    'acquisition_orientation': {'priority': 2},
    'order_of_acquisition': {'priority': 3},
    'group_repeated_measures': {'priority': 1},
    'motion_correction_reference': {'priority': 3},
    'group_model_multilevel': {'priority': 3},
    'number_of_experimental_units': {'priority': 2},
    'type_of_design': {'priority': 1},
    'coordinate_space': {'priority': 1},
    'transform_similarity_metric': {'priority': 3},
    'repetition_time': {'priority': 1},
    'slice_thickness': {'priority': 1},
    'length_of_runs': {'priority': 2},
    'software_version': {'priority': 1},
    'autocorrelation_model': {'priority': 2},
    'b0_unwarping_software': {'priority': 3},
    'intersubject_transformation_type': {'priority': 1},
    'quality_control': {'priority': 3},
    'used_smoothing': {'priority': 1},
    'smoothing_fwhm': {'priority': 1},
    'intrasubject_model_type': {'priority': 1},
    'matrix_size': {'priority': 2},
    'optimization': {'priority': 2},
    'group_inference_type': {'priority': 1},
    'subject_age_mean': {'priority': 1},
    'used_motion_susceptibiity_correction': {'priority': 3},
    'group_statistic_type': {'priority': 2},
    'skip_distance': {'priority': 2},
    'used_reaction_time_regressor': {'priority': 2},
    'group_modeling_software': {'priority': 2},
    'parallel_imaging': {'priority': 3},
    'intersubject_registration_software': {'priority': 2},
    'nonlinear_transform_type': {'priority': 2},
    'field_strength': {'priority': 1},
    'group_estimation_type': {'priority': 1},
    'target_resolution': {'priority': 1},
    'slice_timing_correction_software': {'priority': 3},
    'scanner_make': {'priority': 1},
    'group_smoothness_fwhm': {'priority': 1},
    'flip_angle': {'priority': 2},
    'group_statistic_parameters': {'priority': 3},
    'motion_correction_metric': {'priority': 3},
}


class ContributorCommaSepInput(forms.Widget):

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type='text', name=name)
        if not type(value) == unicode and value is not None:
            out_vals = []
            for val in value:
                try:
                    out_vals.append(str(User.objects.get(pk=val).username))
                except:
                    continue
            value = ', '.join(out_vals)
            if value:
                final_attrs['value'] = smart_str(value)
        else:
            final_attrs['value'] = smart_str(value)
        return mark_safe(u'<input%s />' % flatatt(final_attrs))


class ContributorCommaField(ModelMultipleChoiceField):
    widget = ContributorCommaSepInput

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []

        split_vals = [v.strip() for v in value.split(',')]

        if not isinstance(split_vals, (list, tuple)):
            raise ValidationError("Invalid input.")

        for name in split_vals:
            if not len(self.queryset.filter(username=name)):
                raise ValidationError("User %s does not exist." % name)

        return self.queryset.filter(username__in=split_vals)


class CollectionForm(ModelForm):

    class Meta:
        exclude = ('owner', 'private_token', 'contributors', 'private')
        model = Collection
        # fieldsets = study_fieldsets
        # row_attrs = study_row_attrs

    def clean(self):
        cleaned_data = super(CollectionForm, self).clean()
        doi = self.cleaned_data['DOI']
        if doi.strip() == '':
            self.cleaned_data['DOI'] = None

        if self.cleaned_data['DOI']:
            self.cleaned_data['DOI'] = self.cleaned_data['DOI'].strip()
            try:
                self.cleaned_data["name"], self.cleaned_data["authors"], self.cleaned_data[
                    "paper_url"], _, self.cleaned_data["journal_name"] = get_paper_properties(self.cleaned_data['DOI'].strip())
            except:
                self._errors["DOI"] = self.error_class(
                    ["Could not resolve DOI"])
            else:
                if "name" in self._errors:
                    del self._errors["name"]
        elif "name" not in cleaned_data or not cleaned_data["name"]:
            self._errors["name"] = self.error_class(
                ["You need to set the name or the DOI"])
            self._errors["DOI"] = self.error_class(
                ["You need to set the name or the DOI"])

        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(CollectionForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        for fs in collection_fieldsets:
            # manually enforce field exclusion
            fs[1]['fields'] = [
                v for v in fs[1]['fields'] if v not in self.Meta.exclude]
            tab_holder.append(Tab(fs[1]['legend'], *fs[1]['fields']))
        self.helper.layout.extend([tab_holder, Submit(
                                  'submit', 'Save', css_class="btn-large offset2")])


class OwnerCollectionForm(CollectionForm):
    contributors = ContributorCommaField(
        queryset=None, required=False, help_text="Select other NeuroVault users to add as contributes to the collection.  Contributors can add, edit and delete images in the collection.")

    class Meta():
        exclude = ('owner', 'private_token')
        model = Collection
        widgets = {
            'private': forms.RadioSelect
        }

    def __init__(self, *args, **kwargs):
        super(OwnerCollectionForm, self).__init__(*args, **kwargs)
        self.fields['contributors'].queryset = User.objects.exclude(
            pk=self.instance.owner.pk)


class ImageValidationMixin(object):

    def __init__(self, *args, **kwargs):
        super(ImageValidationMixin, self).__init__()
        self.afni_subbricks = []
        self.afni_tmp = None

    def clean_and_validate(self, cleaned_data):
        print "enter clean_and_validate"
        file = cleaned_data.get('file')
        surface_left_file = cleaned_data.get('surface_left_file')
        surface_right_file = cleaned_data.get('surface_right_file')

        if surface_left_file and surface_right_file and not file:
            if "file" in self._errors.keys():
                del self._errors["file"]
            cleaned_data["data_origin"] = 'surface'
            tmp_dir = tempfile.mkdtemp()
            try:
                new_name = cleaned_data["name"] + ".nii.gz"
                ribbon_projection_file = os.path.join(tmp_dir, new_name)

                inputs_dict = {"lh": "surface_left_file",
                               "rh": "surface_right_file"}
                intent_dict = {"lh": "CortexLeft",
                               "rh": "CortexRight"}

                for hemi in ["lh", "rh"]:
                    print hemi
                    surface_file = cleaned_data.get(inputs_dict[hemi])
                    _, ext = splitext_nii_gz(surface_file.name)

                    if not ext.lower() in [".mgh", ".curv", ".gii", ".nii", ".nii.gz"]:
                        self._errors[inputs_dict[hemi]] = self.error_class(
                            ["Doesn't have proper extension"]
                        )
                        del cleaned_data[inputs_dict[hemi]]
                        return cleaned_data

                    infile = os.path.join(tmp_dir, hemi + ext)

                    print "write " + hemi
                    print surface_file.file
                    surface_file.open()
                    surface_file = StringIO(surface_file.read())
                    with open(infile, 'w') as fd:
                        surface_file.seek(0)
                        shutil.copyfileobj(surface_file, fd)

                    try:
                        if ext.lower() != ".gii":
                            out_gii = os.path.join(tmp_dir, hemi + '.gii')
                            subprocess.check_output(
                                [os.path.join(os.environ['FREESURFER_HOME'],
                                              "bin", "mris_convert"),
                                 "-c", infile,
                                 os.path.join(os.environ['FREESURFER_HOME'],
                                              "subjects", "fsaverage", "surf",
                                              hemi + ".white"),
                                 out_gii])
                        else:
                            out_gii = infile

                        gii = nb.load(out_gii)

                        if gii.darrays[0].dims != [163842]:
                            self._errors[inputs_dict[hemi]] = self.error_class(
                                ["Doesn't have proper dimensions - are you sure it's fsaverage?"]
                            )
                            del cleaned_data[inputs_dict[hemi]]
                            return cleaned_data

                        # fix intent
                        old_dict = gii.meta.metadata
                        old_dict['AnatomicalStructurePrimary'] = intent_dict[hemi]
                        gii.meta = gii.meta.from_dict(old_dict)
                        gii.to_filename(os.path.join(tmp_dir, hemi + '.gii'))

                        subprocess.check_output(
                            [os.path.join(os.environ['FREESURFER_HOME'],
                                          "bin", "mri_surf2surf"),
                             "--s", "fsaverage",
                             "--hemi", hemi,
                             "--srcsurfval",
                             os.path.join(tmp_dir, hemi+'.gii'),
                             "--trgsubject", "ICBM2009c_asym_nlin",
                             "--trgsurfval",
                             os.path.join(tmp_dir, hemi+'.MNI.gii')])
                    except CalledProcessError, e:
                        raise RuntimeError(str(e.cmd) + " returned code " +
                                           str(e.returncode) + " with output " + e.output)

                cleaned_data['surface_left_file'] = memory_uploadfile(
                    os.path.join(tmp_dir, 'lh.gii'),
                    new_name[:-7] + ".fsaverage.lh.func.gii", None)
                cleaned_data['surface_right_file'] = memory_uploadfile(
                    os.path.join(tmp_dir, 'rh.gii'),
                    new_name[:-7] + ".fsaverage.rh.func.gii", None)
                print "surf2vol"
                try:
                    subprocess.check_output(
                        [os.path.join(os.environ['FREESURFER_HOME'],
                                      "bin", "mri_surf2vol"),
                         "--subject", "ICBM2009c_asym_nlin",
                         "--o",
                         ribbon_projection_file[:-3],
                         "--so",
                         os.path.join(os.environ['FREESURFER_HOME'],
                                      "subjects", "ICBM2009c_asym_nlin", "surf", "lh.white"),
                         os.path.join(tmp_dir, 'lh.MNI.gii'),
                         "--so",
                         os.path.join(os.environ['FREESURFER_HOME'],
                                      "subjects", "ICBM2009c_asym_nlin", "surf", "rh.white"),
                         os.path.join(tmp_dir, 'rh.MNI.gii')])
                except CalledProcessError, e:
                    raise RuntimeError(str(e.cmd) + " returned code " +
                                       str(e.returncode) + " with output " + e.output)

                #fix one voxel offset
                nii = nb.load(ribbon_projection_file[:-3])
                affine = nii.affine
                affine[0, 3] -= 1
                nb.Nifti1Image(nii.get_data(), affine).to_filename(ribbon_projection_file)

                cleaned_data['file'] = memory_uploadfile(
                    ribbon_projection_file, new_name, None)
            finally:
                shutil.rmtree(tmp_dir)


        elif file:
            # check extension of the data file
            _, fname, ext = split_filename(file.name)
            if not ext.lower() in [".nii.gz", ".nii", ".img"]:
                self._errors["file"] = self.error_class(
                    ["Doesn't have proper extension"]
                )
                del cleaned_data["file"]
                return cleaned_data

            # prepare file to loading into memory
            file.open()
            fileobj = file.file
            if file.name.lower().endswith(".gz"):
                fileobj = GzipFile(filename=file.name, mode='rb',
                                   fileobj=fileobj)

            file_map = {'image': nb.FileHolder(file.name, fileobj)}
            try:
                tmp_dir = tempfile.mkdtemp()
                if ext.lower() == ".img":
                    hdr_file = cleaned_data.get('hdr_file')
                    if hdr_file:
                        # check extension of the hdr file
                        _, _, hdr_ext = split_filename(hdr_file.name)
                        if not hdr_ext.lower() in [".hdr"]:
                            self._errors["hdr_file"] = self.error_class(
                                ["Doesn't have proper extension"])
                            del cleaned_data["hdr_file"]
                            return cleaned_data
                        else:
                            hdr_file.open()
                            file_map["header"] = nb.FileHolder(hdr_file.name,
                                                               hdr_file.file)
                    else:
                        self._errors["hdr_file"] = self.error_class(
                            [".img file requires .hdr file"]
                        )
                        del cleaned_data["hdr_file"]
                        return cleaned_data

                # check if it is really nifti
                try:
                    # print file_map
                    if "header" in file_map:
                        nii = nb.Nifti1Pair.from_file_map(file_map)
                    else:
                        nii = nb.Nifti1Image.from_file_map(file_map)
                except Exception as e:
                    raise

                # detect AFNI 4D files and prepare 3D slices
                if nii is not None and detect_4D(nii):
                    self.afni_subbricks = split_4D_to_3D(nii, tmp_dir=tmp_dir)
                else:
                    squeezable_dimensions = len([a for a in nii.shape if a not in [0, 1]])

                    if squeezable_dimensions != 3:
                        self._errors["file"] = self.error_class(
                            ["4D files are not supported.\n "
                             "If it's multiple maps in one "
                             "file please split them and "
                             "upload separately"])
                        del cleaned_data["file"]
                        return cleaned_data

                    # convert to nii.gz if needed
                    if (ext.lower() != ".nii.gz"
                            or squeezable_dimensions < len(nii.shape)):
                        # convert pseudo 4D to 3D
                        if squeezable_dimensions < len(nii.shape):
                            new_data = np.squeeze(nii.get_data())
                            nii = nb.Nifti1Image(new_data, nii.get_affine(),
                                                 nii.get_header())

                        # Papaya does not handle float64, but by converting
                        # files we loose precision
                        # if nii.get_data_dtype() == np.float64:
                        # ii.set_data_dtype(np.float32)
                        new_name = fname + ".nii.gz"
                        nii_tmp = os.path.join(tmp_dir, new_name)
                        nb.save(nii, nii_tmp)

                        print "updating file in cleaned_data"

                        cleaned_data['file'] = memory_uploadfile(
                            nii_tmp, new_name, cleaned_data['file']
                        )
            finally:
                try:
                    if self.afni_subbricks:
                        # keep temp dir for AFNI slicing
                        self.afni_tmp = tmp_dir
                    else:
                        shutil.rmtree(tmp_dir)
                except OSError as exc:
                    if exc.errno != 2:  # code 2 - no such file or directory
                        raise  # re-raise exception
        elif not getattr(self, 'partial', False):
            # Skip validation error if this is a partial update from the API
            raise ValidationError("Couldn't read uploaded file")

        return cleaned_data


class ImageForm(ModelForm, ImageValidationMixin):
    hdr_file = FileField(
        required=False, label='.hdr part of the map (if applicable)', widget=AdminResubmitFileWidget)

    def __init__(self, *args, **kwargs):
        ImageValidationMixin.__init__(self, *args, **kwargs)
        ModelForm.__init__(self, *args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False

    class Meta:
        model = Image
        exclude = []
        widgets = {
            'file': AdminResubmitFileWidget,
            'hdr_file': AdminResubmitFileWidget,
            'data_origin': HiddenInput
        }

    def clean(self, **kwargs):
        cleaned_data = super(ImageForm, self).clean()
        cleaned_data["tags"] = clean_tags(cleaned_data)
        return self.clean_and_validate(cleaned_data)




class StatisticMapForm(ImageForm):

    def __init__(self, *args, **kwargs):
        super(StatisticMapForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.add_input(Submit('submit', 'Submit'))

    def clean(self, **kwargs):
        cleaned_data = super(StatisticMapForm, self).clean()
        django_file = cleaned_data.get("file")

        cleaned_data["is_valid"] = True #This will be only saved if the form will validate
        cleaned_data["tags"] = clean_tags(cleaned_data)
        print cleaned_data

        if "data_origin" in cleaned_data.keys() and cleaned_data["data_origin"] == "surface":
            cleaned_data["is_thresholded"] = False
            cleaned_data["not_mni"] = False
            cleaned_data["perc_bad_voxels"] = 0
            cleaned_data["brain_coverage"] = 100
        elif django_file and "file" not in self._errors and "hdr_file" not in self._errors:
            django_file.open()
            fileobj = StringIO(django_file.read())
            django_file.seek(0)
            gzfileobj = GzipFile(
                filename=django_file.name, mode='rb', fileobj=fileobj)
            nii = nb.Nifti1Image.from_file_map(
                {'image': nb.FileHolder(django_file.name, gzfileobj)})
            cleaned_data["is_thresholded"], ratio_bad = is_thresholded(nii)
            cleaned_data["perc_bad_voxels"] = ratio_bad*100.0

            if cleaned_data["is_thresholded"] and not cleaned_data.get("ignore_file_warning") and cleaned_data.get("map_type") != "R":
                self._errors["file"] = self.error_class(
                    ["This map seems to be thresholded (%.4g%% of voxels are zeros). Please use an unthresholded version of the map if possible." % (cleaned_data["perc_bad_voxels"])])
                if cleaned_data.get("hdr_file"):
                    self._errors["hdr_file"] = self.error_class(
                        ["This map seems to be thresholded (%.4g%% of voxels are zeros). Please use an unthresholded version of the map if possible." % (cleaned_data["perc_bad_voxels"])])
                self.fields[
                    "ignore_file_warning"].widget = forms.CheckboxInput()
            else:
                cleaned_data["not_mni"], cleaned_data["brain_coverage"], cleaned_data[
                    "perc_voxels_outside"] = not_in_mni(nii)
                if cleaned_data["not_mni"] and not cleaned_data.get("ignore_file_warning") and cleaned_data.get(
                    "map_type") != "R":
                    self._errors["file"] = self.error_class(
                        ["This map seems not to be in the MNI space (%.4g%% of meaningful voxels are outside of the brain). Please use transform your data to MNI space." % (cleaned_data["perc_voxels_outside"])])
                    if cleaned_data.get("hdr_file"):
                        self._errors["hdr_file"] = self.error_class(
                            ["This map seems not to be in the MNI space (%.4g%% of meaningful voxels are outside of the brain). Please use transform your data to MNI space." % (cleaned_data["perc_voxels_outside"])])
                    self.fields[
                        "ignore_file_warning"].widget = forms.CheckboxInput()

            if cleaned_data.get("map_type") == "R":
                if "not_mni" in cleaned_data:
                    del cleaned_data["not_mni"]
                if "is_thresholded" in cleaned_data:
                    del cleaned_data["is_thresholded"]

        return cleaned_data

    class Meta(ImageForm.Meta):
        model = StatisticMap
        fields = ('name', 'collection', 'description', 'map_type', 'modality', 'cognitive_paradigm_cogatlas',
                  'cognitive_contrast_cogatlas', 'cognitive_paradigm_description_url', 'analysis_level', 'number_of_subjects', 'contrast_definition', 'figure',
                  'file', 'ignore_file_warning', 'hdr_file', 'tags', 'statistic_parameters',
                  'smoothness_fwhm', 'is_thresholded', 'perc_bad_voxels', 'is_valid', 'data_origin')
        widgets = {
            'file': AdminResubmitFileWidget,
            'hdr_file': AdminResubmitFileWidget,
            'is_thresholded': HiddenInput,
            'ignore_file_warning': HiddenInput,
            'perc_bad_voxels': HiddenInput,
            'not_mni': HiddenInput,
            'brain_coverage': HiddenInput,
            'perc_voxels_outside': HiddenInput,
            'is_valid': HiddenInput,
            'data_origin': HiddenInput
        }

    def save_afni_slices(self, commit):
        try:
            orig_img = self.instance

            for n, (label, brick) in enumerate(self.afni_subbricks):
                brick_fname = os.path.split(brick)[-1]
                mfile = memory_uploadfile(brick, brick_fname, orig_img.file)
                brick_img = StatisticMap(name='%s - %s' % (orig_img.name, label), collection=orig_img.collection,
                                         file=mfile)
                for field in set(self.Meta.fields) - set(['file', 'hdr_file', 'name', 'collection']):
                    if field in self.cleaned_data:
                        setattr(brick_img, field, self.cleaned_data[field])

                brick_img.save()
            return orig_img.collection

        finally:
            try:
                shutil.rmtree(self.afni_tmp)
            except OSError as exc:
                if exc.errno != 2:
                    raise

    def save(self, commit=True):
        if self.afni_subbricks:
            return self.save_afni_slices(commit)
        else:
            return super(StatisticMapForm, self).save(commit=commit)


class AtlasForm(ImageForm):

    class Meta(ImageForm.Meta):
        model = Atlas
        fields = ('name', 'collection', 'description', 'figure',
                  'file', 'hdr_file', 'label_description_file', 'tags')


class PolymorphicImageForm(ImageForm):

    def __init__(self, *args, **kwargs):
        super(PolymorphicImageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        if self.instance.polymorphic_ctype is not None:
            if self.instance.polymorphic_ctype.model == 'atlas':
                self.fields = AtlasForm.base_fields
            elif self.instance.polymorphic_ctype.model == 'nidmresultstatisticmap':
                self.fields = NIDMResultStatisticMapForm(self.instance.collection.owner,
                                                         instance=self.instance).fields
            else:
                self.fields = StatisticMapForm.base_fields

    def clean(self, **kwargs):
        if "label_description_file" in self.fields.keys():
            use_form = AtlasForm
        elif "map_type" in self.fields.keys():
            use_form = StatisticMapForm
        else:
            raise Exception("unknown image type! %s" % str(self.fields.keys()))

        new_instance = use_form(self)
        new_instance.cleaned_data = self.cleaned_data
        new_instance._errors = self._errors
        self.fields = new_instance.fields
        return new_instance.clean()


class EditStatisticMapForm(StatisticMapForm):

    def __init__(self, *args, **kwargs):
        user = kwargs['user']
        del kwargs['user']
        super(EditStatisticMapForm, self).__init__(*args, **kwargs)
        if user.is_superuser:
            self.fields['collection'].queryset = Collection.objects.all()
        else:
            self.fields['collection'].queryset = get_objects_for_user(
                user, 'statmaps.change_collection')


class AddStatisticMapForm(StatisticMapForm):

    class Meta(StatisticMapForm.Meta):
        fields = ('name', 'description', 'map_type', 'modality', 'cognitive_paradigm_cogatlas',
                  'cognitive_contrast_cogatlas', 'cognitive_paradigm_description_url', 'analysis_level', 'number_of_subjects', 'contrast_definition', 'figure',
                  'file', 'ignore_file_warning', 'hdr_file', 'surface_left_file', 'surface_right_file', 'tags', 'statistic_parameters',
                  'smoothness_fwhm', 'is_thresholded', 'perc_bad_voxels', 'data_origin')


class EditAtlasForm(AtlasForm):

    def __init__(self, *args, **kwargs):
        user = kwargs['user']
        del kwargs['user']
        super(EditAtlasForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.add_input(Submit('submit', 'Submit'))
        if user.is_superuser:
            self.fields['collection'].queryset = Collection.objects.all()
        else:
            self.fields['collection'].queryset = get_objects_for_user(
                user, 'statmaps.change_collection')

    class Meta(AtlasForm.Meta):
        exclude = ()


class SimplifiedStatisticMapForm(EditStatisticMapForm):

    class Meta(EditStatisticMapForm.Meta):
        fields = ('name', 'collection', 'description', 'map_type', 'modality', 'cognitive_paradigm_cogatlas',
                  'cognitive_contrast_cogatlas', 'cognitive_paradigm_description_url', 'file', 'ignore_file_warning', 'hdr_file', 'tags', 'is_thresholded',
                  'perc_bad_voxels')

class NeuropowerStatisticMapForm(EditStatisticMapForm):
    def __init__(self, *args, **kwargs):
        super(NeuropowerStatisticMapForm, self).__init__(*args, **kwargs)
        self.fields['analysis_level'].required = True
        self.fields['number_of_subjects'].required = True

    class Meta(EditStatisticMapForm.Meta):
        fields = ('name', 'collection', 'description', 'map_type', 'modality', 'map_type','analysis_level','number_of_subjects','cognitive_paradigm_cogatlas',
                  'cognitive_contrast_cogatlas', 'cognitive_paradigm_description_url', 'file', 'ignore_file_warning', 'hdr_file', 'tags', 'is_thresholded',
                  'perc_bad_voxels')

class UploadFileForm(Form):

    # TODO Need to upload in a temp directory
    # (upload_to="images/%s/%s"%(instance.collection.id, filename))
    file = FileField(required=False)

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.file = ''

    def clean(self):
        cleaned_data = super(UploadFileForm, self).clean()
        file = cleaned_data.get("file")
        if file:
            ext = os.path.splitext(file.name)[1]
            ext = ext.lower()
            if ext not in ['.zip', '.gz']:
                raise ValidationError("Not allowed filetype!")


class PathOnlyWidget(forms.Widget):

    def render(self, name, value, attrs=None):
        return mark_safe('<a target="_blank" href="%s">%s</a><br /><br />' % (value.url, value.url))


class MapTypeListWidget(forms.Widget):

    def render(self, name, value, attrs=None):
        map_type = [
            v for k, v in BaseStatisticMap.MAP_TYPE_CHOICES if k == value].pop()
        input = '<input type="hidden" name="%s" value="%s" />' % (name, value)
        return mark_safe('%s<strong>%s</strong><br /><br />' % (input, map_type))


class NIDMResultsValidationMixin(object):

    def clean_and_validate(self, data):
        zip_file = data.get('zip_file')
        partial = getattr(self, 'partial', False)

        if (zip_file and partial) or (not partial):
            return self.clean_and_validate_zip_file(data, zip_file)

        return data

    def clean_and_validate_zip_file(self, data, zip_file):
        # make sure the zip file has a unique name
        base_subdir = os.path.split(data['zip_file'].name)[-1].replace(
            '.nidm.zip',
            '')
        nres = NIDMResults.objects.filter(collection=data['collection'],
                                          name__startswith=base_subdir + ".nidm").count()
        # don't count current instance
        if self.instance.pk is not None and nres != 0:
            nres -= 1
        safe_name = '{0}_{1}.nidm'.format(base_subdir, nres)
        data['name'] = base_subdir + ".nidm" if nres == 0 else safe_name
        data['zip_file'].name = zip_file.name = data['name'] + ".zip"

        try:
            self.nidm = NIDMUpload(zip_file)
        except Exception, e:
            raise ValidationError(
                "The NIDM file was not readable: {0}".format(e)
            )

        try:
            self.clean_nidm(data)
        except Exception, e:
            raise ValidationError(e)

        # delete existing images and files when changing file
        if self.instance.pk is not None:
            for statmap in self.instance.nidmresultstatisticmap_set.all():
                statmap.delete()
            cdir = os.path.dirname(self.instance.zip_file.path)
            if os.path.isdir(cdir):
                shutil.rmtree(cdir)

        ttl_name = os.path.split(self.nidm.ttl.filename)[-1]

        data['ttl_file'] = InMemoryUploadedFile(
            # fix ttl for spm12
            file=ContentFile(self.nidm.fix_spm12_ttl(
                self.nidm.zip.read(self.nidm.ttl))),
            field_name='file',
            name=ttl_name,
            content_type='text/turtle',
            size=self.nidm.ttl.file_size,
            charset='utf-8'
        )

        return data

    def clean_nidm(self, cleaned_data):
        for s in self.nidm.statmaps:
            s['fname'] = os.path.split(s['file'])[-1]
            s['statmap'] = NIDMResultStatisticMap(name=s['name'])
            s['statmap'].collection = cleaned_data['collection']
            s['statmap'].description = cleaned_data['description']
            s['statmap'].map_type = s['type']
            s['statmap'].nidm_results = self.instance
            s['statmap'].file = 'images/1/foo/bar/'

            try:
                s['statmap'].clean_fields(exclude=('nidm_results', 'file'))
                s['statmap'].validate_unique()
            except Exception, e:
                import traceback
                raise ValidationError(
                    "There was a problem validating the Statistic Maps " +
                    "for this NIDM Result: \n{0}\n{1}".format(e, traceback.format_exc()))


def save_nidm_statmaps(nidm, instance):
    for s in nidm.statmaps:
        s['statmap'].nidm_results = instance
        s['statmap'].file = ContentFile(open(s['file']).read(),
                                        name=os.path.split(s['file'])[-1])
        s['statmap'].save()

    dest = os.path.dirname(instance.zip_file.path)
    nidm.copy_to_dest(dest)
    nidm.cleanup()


def handle_update_ttl_urls(instance):
    ttl_content = instance.ttl_file.file.read()
    fname = os.path.basename(
        instance.nidmresultstatisticmap_set.first().file.name)

    ttl_regx = re.compile(r'(prov:atLocation\ \")(file:\/.*\/)?(' +
                          fname + ')(\"\^\^xsd\:anyURI\ \;)')

    hdr, urlprefix, nifti, ftr = re.search(ttl_regx, ttl_content).groups()
    if not urlprefix:
        urlprefix = ""
    base_url = settings.DOMAIN_NAME
    replace_path = base_url + os.path.join(
        instance.collection.get_absolute_url(), instance.name) + '/'

    updated_ttl = ttl_content.replace(hdr + urlprefix, hdr + replace_path)
    instance.ttl_file.file.close()

    with open(instance.ttl_file.path, 'w') as ttlf:
        ttlf.write(updated_ttl)
        ttlf.close()


class NIDMResultsForm(forms.ModelForm, NIDMResultsValidationMixin):

    class Meta:
        model = NIDMResults
        widgets = {
            'is_valid': forms.HiddenInput()
        }
        exclude = []

    def __init__(self, *args, **kwargs):
        super(NIDMResultsForm, self).__init__(*args, **kwargs)

        for fld in ['ttl_file']:
            if self.instance.pk is None:
                self.fields[fld].widget = HiddenInput()
            else:
                self.fields[fld].widget = PathOnlyWidget()

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = True
        self.helper.add_input(Submit('submit', 'Submit'))
        self.helper.add_input(
            Button('delete', 'Delete',
                   onclick='window.location.href=window.location.href+"/delete"'))
        self.nidm = None
        self.new_statmaps = []

        if self.instance.pk is not None:
            self.fields['name'].widget = HiddenInput()
            if self.fields.get('collection'):
                self.fields['collection'].widget = HiddenInput()

    def clean(self):
        cleaned_data = super(NIDMResultsForm, self).clean()
        cleaned_data["tags"] = clean_tags(cleaned_data)
        # only process new uploads or replaced zips
        if self.instance.pk is None or 'zip_file' in self.changed_data:
            self.cleaned_data = self.clean_and_validate(cleaned_data)

    def save(self, commit=True):
        if self.instance.pk is None or 'zip_file' in self.changed_data:
            do_update = True

        nidm_r = super(NIDMResultsForm, self).save(commit)
        if commit and do_update is not None:
            self.save_nidm()
            self.update_ttl_urls()
        return nidm_r

    def update_ttl_urls(self):
        handle_update_ttl_urls(self.instance)

    def save_nidm(self):
        if self.nidm and 'zip_file' in self.changed_data:
            save_nidm_statmaps(self.nidm, self.instance)
            # todo: rewrite ttl


class NIDMViewForm(forms.ModelForm):

    class Meta:
        model = NIDMResults
        exclude = ['is_valid']

    def __init__(self, *args, **kwargs):
        super(NIDMViewForm, self).__init__(*args, **kwargs)

        for fld in ['ttl_file', 'zip_file']:
            self.fields[fld].widget = PathOnlyWidget()
        for fld in self.fields:
            self.fields[fld].widget.attrs['readonly'] = 'readonly'
        self.fields['name'].widget = HiddenInput()
        if self.fields.get('collection'):
            self.fields['collection'].widget = HiddenInput()

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = True


class NIDMResultStatisticMapForm(ImageForm):

    class Meta():
        model = NIDMResultStatisticMap
        fields = ('name', 'collection', 'description', 'map_type', 'figure',
                  'file', 'tags', 'nidm_results')

    def __init__(self, *args, **kwargs):
        super(NIDMResultStatisticMapForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        # problem with exclude() and fields()
        self.fields['hdr_file'].widget = HiddenInput()
        if self.instance.pk is None:
            self.fields['file'].widget = HiddenInput()
        else:
            for fld in self.fields:
                self.fields[fld].widget.attrs['readonly'] = 'readonly'
            # 'disabled' causes the values to not be sent in the POST (?)
            #   self.fields[fld].widget.attrs['disabled'] = 'disabled'

            if self.fields.get('nidm_results'):
                self.fields['nidm_results'].widget = HiddenInput()
            self.fields['map_type'].widget = MapTypeListWidget()
            self.fields['file'].widget = PathOnlyWidget()


class EditNIDMResultStatisticMapForm(NIDMResultStatisticMapForm):

    def __init__(self, user, *args, **kwargs):
        super(EditNIDMResultStatisticMapForm, self).__init__(*args, **kwargs)


def clean_tags(self):
    """
    Force all tags to lowercase.
    """
    tags = self.get('tags', None)
    if tags:
        tags = [t.lower() for t in tags]

    return tags
