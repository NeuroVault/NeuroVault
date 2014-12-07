import os
import shutil
from tempfile import mkstemp, NamedTemporaryFile

import nibabel as nb
import numpy as np

from django.forms import ModelForm
from django.forms.models import inlineformset_factory, ModelMultipleChoiceField, BaseInlineFormSet
from django.core.exceptions import ValidationError
# from form_utils.forms import BetterModelForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Hidden
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions, TabHolder, Tab

from .models import Collection, Image, ValueTaggedItem, User, StatisticMap, Atlas

from django.forms.forms import Form
from django.forms.fields import FileField
import tempfile
from neurovault.apps.statmaps.utils import split_filename, get_paper_properties, \
                                        detect_afni4D, split_afni4D_to_3D, memory_uploadfile
from django import forms
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.forms.util import flatatt


# Create the form class.
collection_fieldsets = [
    ('Essentials', {'fields': ['name',
                               'DOI',
                               'description'],
                    'legend': 'Essentials'}),
    ('Participants', {'fields': ['number_of_subjects',
                                 'subject_age_mean',
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
                                    'skip_factor',
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
    'number_of_subjects': {'priority': 1},
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
    'skip_factor': {'priority': 2},
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

    def clean(self,value):
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
        exclude = ('owner','private_token','contributors','private')
        model = Collection
        # fieldsets = study_fieldsets
        # row_attrs = study_row_attrs

    def clean(self):
        cleaned_data = super(CollectionForm, self).clean()
        doi = self.cleaned_data['DOI']
        if doi.strip() == '':
            self.cleaned_data['DOI'] = None

        if self.cleaned_data['DOI']:
            try:
                self.cleaned_data["name"], self.cleaned_data["authors"], self.cleaned_data["url"], _, self.cleaned_data["journal_name"] = get_paper_properties(self.cleaned_data['DOI'].strip())
            except:
                self._errors["DOI"] = self.error_class(["Could not resolve DOI"])
            else:
                if "name" in self._errors:
                    del self._errors["name"]
        elif "name" not in cleaned_data or not cleaned_data["name"]:
            self._errors["name"] = self.error_class(["You need to set the name or the DOI"])
            self._errors["DOI"] = self.error_class(["You need to set the name or the DOI"])

        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(CollectionForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        for fs in collection_fieldsets:
            tab_holder.append(Tab(
                fs[1]['legend'],
                *fs[1]['fields']
            )
            )
        self.helper.layout.extend([tab_holder, Submit(
                                  'submit','Save', css_class="btn-large offset2")])


class OwnerCollectionForm(CollectionForm):
    contributors = ContributorCommaField(queryset=None,required=False)

    class Meta():
        exclude = ('owner','private_token')
        model = Collection
        widgets = {
            'private': forms.RadioSelect
        }

    def __init__(self, *args, **kwargs):
        # explicitly populate owner-only fields to fieldsets
        for field in ['contributors','private']:
            if field not in collection_fieldsets[0][1]['fields']:
                collection_fieldsets[0][1]['fields'].append(field)
        super(OwnerCollectionForm, self).__init__(*args, **kwargs)
        self.fields['contributors'].queryset = User.objects.exclude(pk=self.instance.owner.pk)


class ImageForm(ModelForm):
    hdr_file = FileField(required=False, label='.hdr part of the map (if applicable)')

    def __init__(self, *args, **kwargs):
        super(ImageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.afni_subbricks = []
        self.afni_tmp = None

    class Meta:
        model = Image
        exclude = ('collection', )

    def clean(self, **kwargs):

        cleaned_data = super(ImageForm, self).clean()
        file = cleaned_data.get("file")

        if file:
            # check extension of the data filr
            _, fname, ext = split_filename(file.name)
            if not ext.lower() in [".nii.gz", ".nii", ".img"]:
                self._errors["file"] = self.error_class(["Doesn't have proper extension"])
                del cleaned_data["file"]
                return cleaned_data

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
                            # write the header file to a temporary directory
                            hf = open(os.path.join(tmp_dir, fname + ".hdr"), "wb")
                            hf.write(hdr_file.file.read())
                            hf.close()
                    else:
                        self._errors["hdr_file"] = self.error_class([".img files require .hdr"])
                        del cleaned_data["hdr_file"]
                        return cleaned_data

                # write the data file to a temporary directory
                nii_tmp = os.path.join(tmp_dir, fname + ext)
                f = open(nii_tmp, "wb")
                f.write(file.file.read())
                f.close()

                # check if it is really nifti
                try:
                    nii = nb.load(nii_tmp)
                except Exception as e:
                    self._errors["file"] = self.error_class([str(e)])
                    del cleaned_data["file"]
                    return cleaned_data

                # convert to nii.gz if needed
                if ext.lower() != ".nii.gz":

                    #Papaya does not handle float64, but by converting files we loose precision
                    #if nii.get_data_dtype() == np.float64:
                    #ii.set_data_dtype(np.float32)
                    nii_tmp = os.path.join(tmp_dir, fname + ".nii.gz")
                    nb.save(nii, nii_tmp)

                    cleaned_data['file'] = memory_uploadfile(nii_tmp, fname + "nii.gz",
                                                             cleaned_data['file'])

                # detect AFNI 4D files and prepare 3D slices
                if nii_tmp is not None and detect_afni4D(nii_tmp):
                    self.afni_subbricks = split_afni4D_to_3D(nii_tmp)

            finally:
                try:
                    if self.afni_subbricks:
                        self.afni_tmp = tmp_dir  # keep temp dir for AFNI slicing
                    else:
                        shutil.rmtree(tmp_dir)
                except OSError as exc:
                    if exc.errno != 2:  # code 2 - no such file or directory
                        raise  # re-raise exception
        else:
            raise ValidationError("Couldn't read uploaded file")
        return cleaned_data


class StatisticMapForm(ImageForm):
    class Meta(ImageForm.Meta):
        model = StatisticMap
        fields = ('name', 'collection', 'description', 'map_type',
                  'file', 'hdr_file', 'tags', 'statistic_parameters',
                  'smoothness_fwhm', 'contrast_definition', 'contrast_definition_cogatlas')


class AtlasForm(ImageForm):
    class Meta(ImageForm.Meta):
        model = Atlas
        fields = ('name', 'collection', 'description',
                  'file', 'hdr_file', 'label_description_file', 'tags')


class EditStatisticMapForm(StatisticMapForm):

    def __init__(self, user, *args, **kwargs):
        super(EditStatisticMapForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.add_input(Submit('submit', 'Submit'))


class EditAtlasForm(AtlasForm):

    def __init__(self, user, *args, **kwargs):
        super(EditAtlasForm, self).__init__(*args, **kwargs)
        self.fields['collection'].queryset = Collection.objects.filter(owner=user)

    class Meta(AtlasForm.Meta):
        exclude = ()


class SimplifiedStatisticMapForm(EditStatisticMapForm):

    class Meta(EditStatisticMapForm.Meta):
        fields = ('name', 'collection', 'description', 'map_type',
                  'file', 'hdr_file', 'tags')


class CollectionInlineFormset(BaseInlineFormSet):

    def save_afni_slices(self,form,commit):
        try:
            orig_img = form.instance
            first_img = None

            for n,(label,brick) in enumerate(form.afni_subbricks):
                brick_fname = os.path.split(brick)[-1]
                mfile = memory_uploadfile(brick, brick_fname, orig_img.file)
                brick_img = Image(name='%s - %s' % (orig_img.name, label), file=mfile)
                for field in ['collection','description','map_type']:
                    setattr(brick_img, field, form.cleaned_data[field])

                if n == 0:
                    form.instance = brick_img
                    first_img = form.save()
                else:
                    brick_img.save()
                    for tag in first_img.tags.all():
                        tagobj = ValueTaggedItem(content_object=brick_img,tag=tag)
                        tagobj.save()

        finally:
            shutil.rmtree(form.afni_tmp)
        return form

    def save_new(self,form,commit=True):
        if form.afni_subbricks:
            form = self.save_afni_slices(form,commit)
            return form.instance
        else:
            return super(CollectionInlineFormset, self).save_new(form,commit=commit)

    def save_existing(self,form,instance,commit=True):
        if form.afni_subbricks:
            form = self.save_afni_slices(form,commit)
            return form.instance
        else:
            return super(CollectionInlineFormset, self).save_existing(
                                                            form, instance, commit=commit)

CollectionFormSet = inlineformset_factory(
    Collection, StatisticMap, form=StatisticMapForm,
    exclude=['json_path', 'nifti_gz_file', 'collection'],
    extra=1, formset=CollectionInlineFormset)


class UploadFileForm(Form):

    # TODO Need to uplaod in a temp directory
    file = FileField(required=False);  #(upload_to="images/%s/%s"%(instance.collection.id, filename))

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
