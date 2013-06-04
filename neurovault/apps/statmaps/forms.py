from django.forms import ModelForm

from .models import Study, StatMap
from django.forms.models import inlineformset_factory
import os
from django.core.exceptions import ValidationError
import nibabel as nb
from tempfile import mkstemp, NamedTemporaryFile
import shutil
from neurovault.apps.statmaps.models import getPaperProperties

# Create the form class.
priorities = {
    'echo_time' : 1,
    'number_of_rejected_subjects' : 2,
    'inclusion_exclusion_criteria' : 3,
    'group_comparison' : 1,
    'contrast_definition_cogatlas' : 3,
    'subject_age_max' : 2,
    'used_dispersion_derivatives' : 3,
    'used_intersubject_registration' : 1,
    'intrasubject_estimation_type' : 1,
    'field_of_view' : 2,
    'order_of_preprocessing_operations' : 2,
    'smoothing_type' : 1,
    'subject_age_min' : 2,
    'length_of_blocks' : 2,
    'used_orthogonalization' : 1,
    'used_b0_unwarping' : 2,
    'used_temporal_derivatives' : 2,
    'software_package' : 1,
    'scanner_model' : 1,
    'high_pass_filter_method' : 2,
    'proportion_male_subjects' : 2,
    'number_of_imaging_runs' : 2,
    'interpolation_method' : 2,
    'group_repeated_measures_method' : 3,
    'motion_correction_software' : 3,
    'used_motion_regressors' : 2,
    'functional_coregistered_to_structural' : 2,
    'motion_correction_interpolation' : 3,
    'optimization_method' : 3,
    'hemodynamic_response_function' : 2,
    'group_model_type' : 1,
    'used_slice_timing_correction' : 1,
    'intrasubject_modeling_software' : 2,
    'target_template_image' : 2,
    'resampled_voxel_size' : 3,
    'object_image_type' : 1,
    'group_description' : 2,
    'functional_coregistration_method' : 3,
    'length_of_trials' : 2,
    'handedness' : 2,
    'number_of_subjects' : 1,
    'used_motion_correction' : 1,
    'pulse_sequence' : 1,
    'used_high_pass_filter' : 1,
    'orthogonalization_description' : 2,
    'acquisition_orientation' : 2,
    'order_of_acquisition' : 3,
    'group_repeated_measures' : 1,
    'motion_correction_reference' : 3,
    'group_model_multilevel' : 3,
    'number_of_experimental_units' : 2,
    'type_of_design' : 1,
    'coordinate_space' : 1,
    'transform_similarity_metric' : 3,
    'repetition_time' : 1,
    'slice_thickness' : 1,
    'length_of_runs' : 2,
    'contrast_definition' : 1,
    'software_version' : 1,
    'autocorrelation_model' : 2,
    'b0_unwarping_software' : 3,
    'intersubject_transformation_type' : 1,
    'quality_control' : 3,
    'used_smoothing' : 1,
    'smoothing_fwhm' : 1,
    'intrasubject_model_type' : 1,
    'matrix_size' : 2,
    'optimization' : 2,
    'group_inference_type' : 1,
    'subject_age_mean' : 1,
    'used_motion_susceptibiity_correction' : 3,
    'group_statistic_type' : 2,
    'skip_factor' : 2,
    'used_reaction_time_regressor' : 2,
    'group_modeling_software' : 2,
    'parallel_imaging' : 3,
    'intersubject_registration_software' : 2,
    'nonlinear_transform_type' : 2,
    'field_strength' : 1,
    'group_estimation_type' : 1,
    'target_resolution' : 1,
    'slice_timing_correction_software' : 3,
    'scanner_make' : 1,
    'group_smoothness_fwhm' : 1,
    'flip_angle' : 2,
    'group_statistic_parameters' : 3,
    'motion_correction_metric' : 3,
}


class StudyForm(ModelForm):
    class Meta:
        exclude = ('owner',)
        model = Study

    def __init__(self, *args, **kwargs):
        super(StudyForm, self).__init__(*args, **kwargs)

    # This allowsinserting null DOIs
    def clean_DOI(self):
        doi = self.cleaned_data['DOI']
        if doi == '':
            doi = None
        else:
            try:
                getPaperProperties(doi)
            except:
                raise ValidationError("Invalid DOI")
        return doi
        

class StatMapForm(ModelForm):
    # Add some custom validation to our file field
    def clean(self):
        cleaned_data = super(StatMapForm, self).clean()
        file = cleaned_data.get("file")
        if file:
            if not os.path.splitext(file.name)[1] in [".gz", ".nii", ".img"]:
                self._errors["file"] = self.error_class(["Doesn't have proper extension"])
                del cleaned_data["file"]
                return cleaned_data
            # Here we need to now to read the file and see if it's actually
            # a valid audio file. I don't know what the best library is to
            # to do this
            fname = file.name.split("/")[-1]
            with NamedTemporaryFile(suffix=fname, delete=False) as f:
                fname = f.name
                if os.path.splitext(file.name)[1] == ".img":
                    hdr_file = cleaned_data.get('hdr_file')
                    if not os.path.splitext(hdr_file.name)[1] in [".hdr"]:
                        self._errors["hdr_file"] = self.error_class(["Doesn't have proper extension"])
                        del cleaned_data["hdr_file"]
                        return cleaned_data
                    else:
                        hf = open(fname[:-3] + "hdr","wb")
                        hf.write(hdr_file.file.read())
                        hf.close()
                
                f.write(file.file.read())
                f.close()
                try:
                    nb.load(fname)
                except Exception, e:
                    self._errors["file"] = self.error_class([str(e)])
                    del cleaned_data["file"]
                finally:
                    os.remove(fname)
                    if os.path.splitext(file.name)[1] == ".img":
                        if os.path.splitext(hdr_file.name)[1] in [".hdr"]:
                            os.remove(fname[:-3] + "hdr")
        else:
            raise ValidationError("Couldn't read uploaded file")
        return cleaned_data
        


StudyFormSet = inlineformset_factory(
    Study, StatMap, form=StatMapForm, exclude=['json_path'], extra=1)
