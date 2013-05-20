from django.forms import ModelForm
from .models import Study, StatMap
from django.forms.models import inlineformset_factory

# Create the form class.
class StudyForm(ModelForm):
    class Meta:
        exclude = ('owner',)
        model = Study
        
# This allowsinserting null DOIs
    def clean_DOI(self):
        doi = self.cleaned_data['DOI']
        if doi == '':
            doi = None
        return doi

    def __init__(self, *args, **kwargs):
        super(StudyForm, self).__init__(*args, **kwargs)

        self.fields.keyOrder = ['type_of_design', 'cluster_forming_threshold', 'corrected_significance_level',
                                'multiple_test_correction_scope', 'multiple_test_correction_type',
                                'multiple_test_correction_type', 'used_multiple_test_correction',
                                'group_estimation_type', 'group_inference_type', 'group_model_type',
                                'group_repeated_measures', 'contrast_definition', 'intrasubject_estimation_type',
                                'intrasubject_model_type', 'used_high_pass_filter', 'used_orthogonalization',
                                'coordinate_space', 'intersubject_transformation_type', 'object_image_type',
                                'smoothing_fwhm', 'smoothing_type', 'target_resolution', 'used_intersubject_registration',
                                'used_smoothing', 'echo_time', 'field_strength', 'pulse_sequence', 'repetition_time',
                                'scanner_make', 'scanner_model', 'slice_thickness', 'group_comparison', 'number_of_subjects',
                                'subject_age_mean', 'software_package', 'software_version', 'used_motion_correction',
                                'used_slice_timing_correction', 'length_of_blocks', 'length_of_runs', 'length_of_trials',
                                'number_of_experimental_units', 'number_of_imaging_runs', 'optimization', 'group_modeling_software',
                                'autocorrelation_model', 'hemodynamic_response_function', 'high_pass_filter_method',
                                'intrasubject_modeling_software', 'orthogonalization_description', 'used_motion_regressors',
                                'used_reaction_time_regressor', 'used_temporal_derivatives', 'functional_coregistered_to_structural',
                                'interpolation_method', 'intersubject_registration_software', 'nonlinear_transform_type',
                                'target_template_image', 'acquisition_orientation', 'field_of_view', 'flip_angle',
                                'matrix_size', 'skip_factor', 'group_description', 'handedness', 'number_of_rejected_subjects',
                                'proportion_male_subjects', 'subject_age_max', 'subject_age_min', 'order_of_preprocessing_operations',
                                'used_b0_unwarping', 'optimization_method', 'group_search_volume', 'group_model_multilevel',
                                'group_repeated_measures_method', 'contrast_definition_cogatlas', 'used_dispersion_derivatives',
                                'functional_coregistration_method', 'transform_similarity_metric', 'order_of_acquisition',
                                'parallel_imaging', 'inclusion_exclusion_criteria', 'b0_unwarping_software',
                                'motion_correction_interpolation', 'motion_correction_metric', 'motion_correction_reference',
                                'motion_correction_software', 'quality_control', 'slice_timing_correction_software',
                                'used_motion_susceptibiity_correction']

StudyFormSet = inlineformset_factory(Study, StatMap)
