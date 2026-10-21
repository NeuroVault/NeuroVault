"""Web input: validation and layout. Changes are carried out by the use cases."""
import os

from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.models import ModelMultipleChoiceField
from django.forms.widgets import RadioSelect
from django.urls import reverse

# from form_utils.forms import BetterModelForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout,
    Field,
    Submit,
    ButtonHolder,
    Div,
    Fieldset,
    Row,
    Column,
    HTML,
    Button
)
from crispy_forms.bootstrap import (
    Accordion, AccordionGroup, TabHolder, Tab, InlineRadios, FormActions, StrictButton
)
from urllib.parse import urlencode

from .models import (
    Collection,
    Image,
    User,
    StatisticMap,
    BaseStatisticMap,
    Atlas,
    NIDMResults,
    NIDMResultStatisticMap,
    Metaanalysis,
)

from django.forms.forms import Form
from django.forms.fields import FileField
from django import forms
from django.db.models.fields.files import FieldFile
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.forms.utils import flatatt
from django.forms.widgets import HiddenInput, CheckboxSelectMultiple
from file_resubmit.admin import AdminResubmitFileWidget
from guardian.shortcuts import get_objects_for_user

from neurovault.application.ports import SYSTEM
from neurovault.application.services.items import ImageFilesInput
from neurovault.bootstrap import services
from neurovault.domain.errors import DomainValidationError


# Create the form class.
collection_fieldsets = [
    (
        "Essentials",
        {
            "fields": [
                "name",
                Field(
                    "publication_status",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "DOI",
                "preprint_DOI",
                HTML("<div class='alert alert-warning' role='alert' id='not_intended_alert'>Collections not associated with a publication are not guaranteed to be retained for long-term archival.</div>"),
                HTML("<hr>"),
                "description",
                "full_dataset_url",
                "contributors",
                "communities",
                # "private",
                Field(
                    "private",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
            ],
            "legend": "Essentials",
        },
    ),
    (
        "Participants",
        {
            "fields": [
                "subject_age_mean",
                "subject_age_min",
                "subject_age_max",
                Field(
                    "handedness",
                    template="statmaps/fields/toggle_radio_field.html",
                ),           
                "proportion_male_subjects",
                "inclusion_exclusion_criteria",
                "number_of_rejected_subjects",
                Field(
                    "group_comparison",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "group_description",
            ],
            "legend": "Subjects",
        },
    ),
    (
        "ExperimentalDesign",
        {
            "fields": [
                Field(
                    "type_of_design",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "number_of_imaging_runs",
                "number_of_experimental_units",
                "length_of_runs",
                "length_of_blocks",
                "length_of_trials",
                Field(
                    "optimization",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "optimization_method",
            ],
            "legend": "Design",
        },
    ),
    (
        "MRI_acquisition",
        {
            "fields": [
                "scanner_make",
                "scanner_model",
                "field_strength",
                "pulse_sequence",
                "parallel_imaging",
                "field_of_view",
                "matrix_size",
                "slice_thickness",
                "skip_distance",
                "acquisition_orientation",
                Field(
                    "order_of_acquisition",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "repetition_time",
                "echo_time",
                "flip_angle",
            ],
            "legend": "Acquisition",
        },
    ),
    (
        "IntersubjectRegistration",
        {
            "fields": [
                Field(
                    "used_intersubject_registration",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "intersubject_registration_software",
                Field(
                    "intersubject_transformation_type",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "nonlinear_transform_type",
                "transform_similarity_metric",
                "interpolation_method",
                "object_image_type",
                Field(
                    "functional_coregistered_to_structural",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "functional_coregistration_method",
                Field(
                    "coordinate_space",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "target_resolution",
                Field(
                    "used_smoothing",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "smoothing_type",
                "smoothing_fwhm",
                "resampled_voxel_size",
            ],
            "legend": "Registration",
        },
    ),
    (
        "Preprocessing",
        {
            "fields": [
                "software_package",
                "software_version",
                "order_of_preprocessing_operations",
                "quality_control",
                Field(
                    "used_b0_unwarping",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "b0_unwarping_software",
                Field(
                    "used_slice_timing_correction",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "slice_timing_correction_software",
                Field(
                    "used_motion_correction",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "motion_correction_software",
                "motion_correction_reference",
                "motion_correction_metric",
                "motion_correction_interpolation",
                Field(
                    "used_motion_susceptibiity_correction",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
            ],
            "legend": "Preprocessing",
        },
    ),
    (
        "IndividualSubjectModeling",
        {
            "fields": [
                "intrasubject_model_type",
                "intrasubject_estimation_type",
                "intrasubject_modeling_software",
                "hemodynamic_response_function",
                Field(
                    "used_temporal_derivatives",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                Field(
                    "used_dispersion_derivatives",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                Field(
                    "used_motion_regressors",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                Field(
                    "used_reaction_time_regressor",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                Field(
                    "used_orthogonalization",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "orthogonalization_description",
                Field(
                    "used_high_pass_filter",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "high_pass_filter_method",
                "autocorrelation_model",
            ],
            "legend": "First Level",
        },
    ),
    (
        "GroupModeling",
        {
            "fields": [
                "group_model_type",
                "group_estimation_type",
                "group_modeling_software",
                Field(
                    "group_inference_type",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "group_model_multilevel",
                Field(
                    "group_repeated_measures",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "group_repeated_measures_method",
            ],
            "legend": "Second Level",
        },
    ),
    (
        "Nutritional",
        {
            "fields": [
                "nutbrain_hunger_state",
                "nutbrain_food_viewing_conditions",
                "nutbrain_food_choice_type",
                "nutbrain_taste_conditions",
                "nutbrain_odor_conditions",
            ],
            "legend": "Nutritional",
        },
    ),
]


class ContributorCommaSepInput(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(attrs, {"type": "text", name: name})
        if not type(value) == str and value is not None:
            out_vals = []
            for val in value:
                try:
                    out_vals.append(str(User.objects.get(pk=val).username))
                except:
                    continue
            value = ", ".join(out_vals)
            if value:
                final_attrs["value"] = smart_str(value)
        else:
            final_attrs["value"] = smart_str(value)
        return mark_safe("<input%s />" % flatatt(final_attrs))


class ContributorCommaField(ModelMultipleChoiceField):
    widget = ContributorCommaSepInput

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages["required"])
        elif not self.required and not value:
            return []

        split_vals = [v.strip() for v in value.split(",")]

        if not isinstance(split_vals, (list, tuple)):
            raise ValidationError("Invalid input.")

        for name in split_vals:
            if not len(self.queryset.filter(username=name)):
                raise ValidationError("User %s does not exist." % name)

        return self.queryset.filter(username__in=split_vals)


class MetaanalysisForm(ModelForm):
    class Meta:
        exclude = ("owner", "maps", "output_maps", "status")
        model = Metaanalysis
        # fieldsets = study_fieldsets
        # row_attrs = study_row_attrs

    def __init__(self, *args, **kwargs):
        super(MetaanalysisForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-2"
        self.helper.field_class = "col-lg-10"
        self.helper.add_input(Submit("submit", "Submit"))


class CollectionForm(ModelForm):
    class Meta:
        exclude = ("owner", "private_token", "contributors")
        model = Collection
        widgets = {"communities": CheckboxSelectMultiple, "group_comparison": forms.RadioSelect}

        # fieldsets = study_fieldsets
        # row_attrs = study_row_attrs

    def clean(self):
        cleaned_data = super(CollectionForm, self).clean()
        try:
            completed = services().collections.complete_publication(
                {"DOI": cleaned_data.get("DOI"), "name": cleaned_data.get("name")}
            )
        except DomainValidationError as e:
            for field_name, messages in e.errors.items():
                self._errors[field_name] = self.error_class(messages)
            if self.cleaned_data.get("DOI") is not None and self.cleaned_data["DOI"].strip() == "":
                self.cleaned_data["DOI"] = None
            return cleaned_data
        self.cleaned_data.update(completed)
        if completed.get("DOI") and "name" in self._errors:
            del self._errors["name"]
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-2"
        self.helper.field_class = "col-lg-10"
        self.helper.layout = Layout()
        tab_holder = TabHolder()

        self.fields["publication_status"].required = True
        self.fields['publication_status'].choices = self.fields['publication_status'].choices[1:]

        for fs in collection_fieldsets:
            # manually enforce field exclusion (without mutating the shared fieldsets)
            fields = [v for v in fs[1]["fields"] if v not in self.Meta.exclude]
            tab_holder.append(Tab(fs[1]["legend"], *fields))
        self.helper.layout.extend(
            [tab_holder, Submit("submit", "Save", css_class="btn-large offset2")]
        )


class OwnerCollectionForm(CollectionForm):
    contributors = ContributorCommaField(
        queryset=None,
        required=False,
        help_text="Select other NeuroVault users to add as contributes to the collection.  Contributors can add, edit and delete images in the collection.",
    )

    class Meta:
        exclude = ("owner", "private_token")
        model = Collection
        widgets = {"private": forms.RadioSelect, "communities": CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super(OwnerCollectionForm, self).__init__(*args, **kwargs)
        self.fields["contributors"].queryset = User.objects.exclude(
            pk=self.instance.owner.pk
        )


def image_changes(form):
    """(column changes, file uploads, tags) from a valid image form.

    Django's construct_instance has already applied the form to
    form.instance (fields omitted from the POST keep their values), so the
    columns are read back from it.
    """
    changes, files = {}, ImageFilesInput()
    model_fields = {f.name: f for f in form.instance._meta.concrete_fields}
    for name in form.fields:
        field = model_fields.get(name)
        if field is None or name in ("polymorphic_ctype", "nidm_results"):
            continue
        value = getattr(form.instance, field.attname)
        if isinstance(value, FieldFile):
            if value and not value._committed:
                setattr(files, name, value.file)
            continue
        changes["collection_id" if name == "collection" else field.attname] = value
    tags = form.cleaned_data.get("tags") if "tags" in form.fields else None
    return changes, files, tags


class ImageForm(ModelForm):
    hdr_file = FileField(
        required=False,
        label=".hdr part of the map (if applicable)",
        widget=AdminResubmitFileWidget,
    )

    class Meta:
        model = Image
        exclude = []
        widgets = {
            "file": AdminResubmitFileWidget,
            "hdr_file": AdminResubmitFileWidget,
            "data_origin": HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        self.bulk = kwargs.pop("bulk", False)
        self.min_image = kwargs.pop("min_image", None)
        self.max_image = kwargs.pop("max_image", None)
        self.curr_image = kwargs.pop("curr_image", None)

        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-2"
        self.helper.field_class = "col-lg-10"
        self.helper.form_tag = False
        self.helper.form_method = "post"
        # Define the layout explicitly to show the desired fields
        self.helper.layout = Layout(
            "file",
            "hdr_file",
            "data_origin"
        )

    def clean(self, **kwargs):
        cleaned_data = super().clean()
        cleaned_data["tags"] = clean_tags(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        raise NotImplementedError(
            "image forms validate only; store with services().items (see image_changes)"
        )

    def add_buttons(self):
        buttons = []
        if self.min_image and self.instance.id != self.min_image:
            buttons.append(Submit("submit_previous", "Previous Image", css_class="btn btn-primary"))
        if self.max_image and self.instance.id != self.max_image:
            buttons.append(Submit("submit_next", "Next Image", css_class="btn btn-primary"))

        buttons.append(Submit("submit_save", "Save and Exit", css_class="btn btn-primary float-right"))
        self.helper.layout.append(FormActions(*buttons))


class StatisticMapForm(ImageForm):
    COGNITIVE_TASK_CHOICES = [
        ("yes_other", "Yes"),
        ("rest_open", "Rest (Eyes Open)"),
        ("rest_closed", "Rest (Eyes Closed)"),
        ("none", "None / Other")
    ]
    cognitive_task_choice = forms.ChoiceField(
        choices=COGNITIVE_TASK_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        help_text="Was a task performed?",
        label="Cognitive Task"
    )
    class Meta(ImageForm.Meta):
        model = StatisticMap

        fields = [
            "file",
            "name",
            "collection",
            "description",
            "map_type",
            "modality",
            "target_template_image",
            "cognitive_paradigm_cogatlas",
            "cognitive_contrast_cogatlas",
            "cognitive_paradigm_description_url",
            "cognitive_paradigm_short_description",
            "cognitive_paradigm_name",
            "analysis_level",
            "number_of_subjects",
            "contrast_definition",
            "figure",
            "age",
            "sex",
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
            "ignore_file_warning",
            "hdr_file",
            "statistic_parameters",
            "smoothness_fwhm",
            "is_thresholded",
            "perc_bad_voxels",
            "is_valid",
            "data_origin",
            "tags"
        ]
        widgets = {
            "file": AdminResubmitFileWidget,
            "hdr_file": AdminResubmitFileWidget,
            "is_thresholded": HiddenInput,
            "ignore_file_warning": HiddenInput,
            "perc_bad_voxels": HiddenInput,
            "not_mni": HiddenInput,
            "brain_coverage": HiddenInput,
            "perc_voxels_outside": HiddenInput,
            "collection": HiddenInput,
            "is_valid": HiddenInput,
            "data_origin": HiddenInput,
            'description': forms.Textarea(attrs={'rows': 2, 'cols': 40}),  # Adjust the size here
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adjust the layout for all the fields in Meta.fields
        # Crispify the form
        self.helper = FormHelper(self)
        self.helper.form_method = "POST"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-2"
        self.helper.field_class = "col-lg-10"

        alert_html = ""
        if not self.instance.is_valid and not self.bulk:
            alert_html = HTML(
                """
                <div class="alert alert-warning" role="alert">
                <strong>Warning!</strong> critical image meta-data is incomplete and needs to be filled out.
                </div>
                """
            )

        # If the model instance has a FileField, this will display the path/filename.
        # The user will not be able to upload a new file from this form.
        ''' sex and company don't exist on the StatisticMap object.
        for field in ['sex', 'ethnicity', 'handedness']:
            self.fields[field].choices = [('', 'N/A')] + self.fields[field].choices[1:]

        self.fields['analysis_level'].choices = self.fields['analysis_level'].choices[1:]
        '''

        self.helper.layout = Layout(
            alert_html,
            "collection",
            Fieldset(
                "Essentials",
                "name",
                "description",
                "figure",
                Field(
                    "analysis_level",
                    template="statmaps/fields/toggle_radio_field.html",
                ),
                "modality",
                "map_type",
                "target_template_image",
                "number_of_subjects",
            ),
            Fieldset(
                "Cognitive Paradigm",
                Field(
                    "cognitive_task_choice",
                    template="statmaps/fields/toggle_radio_field.html",
                    help_text="Was a cognitive task performed?",
                ),
                "cognitive_paradigm_cogatlas",
                "cognitive_contrast_cogatlas",
                "cognitive_paradigm_name",
                "cognitive_paradigm_short_description",
                "cognitive_paradigm_description_url",
                "contrast_definition",
            ),
            Accordion(
                AccordionGroup(
                    "Analysis Details",
                    "statistic_parameters",
                    "smoothness_fwhm",
                    css_id="analysis-accordion",
                    css_class="show"  # Ensure the accordion is open by default
                ),
                AccordionGroup(
                    'Demographics',
                    'age',
                    Field(
                        'sex',
                        template="statmaps/fields/toggle_radio_field.html",
                    ),
                    Field(
                        'ethnicity',
                        template="statmaps/fields/toggle_radio_field.html",
                    ),
                    'race',
                    Field(
                        'handedness',
                        template="statmaps/fields/toggle_radio_field.html",
                    ),
                    css_id="demographics-accordion",
                    css_class="hide"  # Ensure the accordion is open by default
                ),
                AccordionGroup(
                    'Nutrition and Health Community',
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
                    css_id="nutritional-accordion",
                    css_class="hide"  # Ensure the accordion is closed by default
                ),
            )
        )

        self.add_buttons()

    def clean(self, **kwargs):
        cleaned_data = super().clean()
        django_file = cleaned_data.get("file")
        cleaned_data["is_valid"] = True
        cleaned_data["tags"] = clean_tags(cleaned_data)

        # Examples of your additional logic and data cleaning
        if "analysis_level" in cleaned_data:
            if cleaned_data.get("analysis_level") == "S":
                cleaned_data["number_of_subjects"] = 1
            if "number_of_subjects" in self._errors:
                del self._errors["number_of_subjects"]

        if (
            "data_origin" in cleaned_data
            and cleaned_data["data_origin"] == "surface"
        ):
            cleaned_data["is_thresholded"] = False
            cleaned_data["not_mni"] = False
            cleaned_data["perc_bad_voxels"] = 0
            cleaned_data["brain_coverage"] = 100
        elif (
            django_file
            and "file" not in self._errors
            and "hdr_file" not in self._errors
        ):
            report = services().items.check_map_file(
                django_file,
                cleaned_data.get("map_type"),
                cleaned_data["target_template_image"],
                cleaned_data.get("ignore_file_warning"),
            )
            cleaned_data.update(report.values)
            if report.error:
                self._errors["file"] = self.error_class([report.error])
                if cleaned_data.get("hdr_file"):
                    self._errors["hdr_file"] = self.error_class([report.error])
                self.fields["ignore_file_warning"].widget = forms.CheckboxInput()

            if cleaned_data.get("map_type") == "R":
                if "not_mni" in cleaned_data:
                    del cleaned_data["not_mni"]
                if "is_thresholded" in cleaned_data:
                    del cleaned_data["is_thresholded"]

        return cleaned_data


class EditStatisticMapForm(StatisticMapForm):
    """ Pass through """
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)


class AtlasForm(ImageForm):
    class Meta(ImageForm.Meta):
        model = Atlas
        fields = (
            "name",
            "description",
            "figure",
            "file",
            "hdr_file",
            "label_description_file",
            "tags",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            "name",
            "description",
            "figure",
            "file",
            "hdr_file",
            "label_description_file",
        )

        self.add_buttons()


class EditAtlasForm(AtlasForm):
    """
    Inherits from AtlasForm, but overrides the queryset of 'collection'
    based on the user. Also includes all fields by removing any excludes.
    """
    class Meta(AtlasForm.Meta):
        exclude = ()

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        # Restrict collection queryset if not a superuser
        if user.is_superuser:
            self.fields["collection"].queryset = Collection.objects.all()
        else:
            self.fields["collection"].queryset = get_objects_for_user(
                user, "statmaps.change_collection"
            )

        # Optionally override the layout defined in AtlasForm or keep it:
        self.helper.layout = Layout(
            "name",
            "collection",
            "description",
            "figure",
            "file",
            "hdr_file",
            "label_description_file",
            "tags"
        )

        self.add_buttons()


class SimplifiedStatisticMapForm(EditStatisticMapForm):
    """
    A reduced form that inherits from EditStatisticMapForm 
    but includes fewer fields (as specified in Meta.fields).
    """

    class Meta(EditStatisticMapForm.Meta):
        fields = (
            "name",
            "collection",
            "description",
            "map_type",
            "modality",
            "target_template_image",
            "cognitive_paradigm_cogatlas",
            "cognitive_contrast_cogatlas",
            "cognitive_paradigm_description_url",
            "file",
            "ignore_file_warning",
            "hdr_file",
            "tags",
            "is_thresholded",
            "perc_bad_voxels",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override the parent layout with just these fields
        self.helper.layout = Layout(
            "name",
            "collection",
            "description",
            "map_type",
            "modality",
            "target_template_image",
            Fieldset(
                "Cognitive Paradigm",
                Field(
                    "cognitive_task_choice",
                    template="statmaps/fields/toggle_radio_field.html",
                    help_text="Was a cognitive task performed?",
                ),
                "cognitive_paradigm_cogatlas",
                "cognitive_contrast_cogatlas",
                "cognitive_paradigm_name",
                "cognitive_paradigm_short_description",
                "cognitive_paradigm_description_url",
                "contrast_definition",
            ),
            "file",
            "ignore_file_warning",
            "hdr_file",
            "tags",
            "is_thresholded",
            "perc_bad_voxels",
            ButtonHolder(
                Submit("submit", "Submit")
            )
        )


class NeuropowerStatisticMapForm(EditStatisticMapForm):
    """
    Similar to EditStatisticMapForm, but requires analysis_level and number_of_subjects.
    Also uses its own custom fields in Meta.
    """

    class Meta(EditStatisticMapForm.Meta):
        fields = (
            "name",
            "collection",
            "description",
            "map_type",
            "modality",
            "target_template_image",
            "map_type",  # Notice map_type is repeated in the original code
            "analysis_level",
            "number_of_subjects",
            "cognitive_paradigm_cogatlas",
            "cognitive_contrast_cogatlas",
            "cognitive_paradigm_description_url",
            "file",
            "ignore_file_warning",
            "hdr_file",
            "tags",
            "is_thresholded",
            "perc_bad_voxels",
        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Mark these fields as required
        self.fields["analysis_level"].required = True
        self.fields["number_of_subjects"].required = True

        # Override the layout for this form
        self.helper.layout = Layout(
            "name",
            "collection",
            "description",
            "map_type",
            "modality",
            "target_template_image",
            "map_type",  # Potentially remove if truly redundant
            "analysis_level",
            "number_of_subjects",
            "cognitive_paradigm_cogatlas",
            "cognitive_contrast_cogatlas",
            "cognitive_paradigm_description_url",
            "file",
            "ignore_file_warning",
            "hdr_file",
            "tags",
            "is_thresholded",
            "perc_bad_voxels",
            ButtonHolder(
                Submit("submit", "Submit")
            )
        )


class UploadFileForm(Form):
    # TODO Need to upload in a temp directory
    # (upload_to="images/%s/%s"%(instance.collection.id, filename))
    file = FileField(required=False)

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.file = ""

    def clean(self):
        cleaned_data = super(UploadFileForm, self).clean()
        file = cleaned_data.get("file")
        if file:
            ext = os.path.splitext(file.name)[1]
            ext = ext.lower()
            if ext not in [".zip", ".gz"]:
                raise ValidationError("Filetype must be .zip or .gz.")


class PathOnlyWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(
            '<a target="_blank" href="%s">%s</a><br /><br />' % (value.url, value.url)
        )


class MapTypeListWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        map_type = [v for k, v in BaseStatisticMap.MAP_TYPE_CHOICES if k == value].pop()
        input = '<input type="hidden" name="%s" value="%s" />' % (name, value)
        return mark_safe("%s<strong>%s</strong><br /><br />" % (input, map_type))


class NIDMResultsForm(forms.ModelForm):
    class Meta:
        model = NIDMResults
        widgets = {"is_valid": forms.HiddenInput()}
        exclude = []

    def __init__(self, *args, **kwargs):
        super(NIDMResultsForm, self).__init__(*args, **kwargs)

        for fld in ["ttl_file"]:
            if self.instance.pk is None:
                self.fields[fld].widget = HiddenInput()
            else:
                self.fields[fld].widget = PathOnlyWidget()

        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-2"
        self.helper.field_class = "col-lg-10"
        self.helper.form_tag = True
        self.helper.add_input(Submit("submit", "Submit"))
        self.helper.add_input(
            Button(
                "delete",
                "Delete",
                onclick='window.location.href=window.location.href+"/delete"',
            )
        )
        self.prepared = None

        if self.instance.pk is not None:
            self.fields["name"].widget = HiddenInput()
            if self.fields.get("collection"):
                self.fields["collection"].widget = HiddenInput()

    def clean(self):
        cleaned_data = super(NIDMResultsForm, self).clean()
        cleaned_data["tags"] = clean_tags(cleaned_data)
        # only process new uploads or replaced zips
        if self.instance.pk is None or "zip_file" in self.changed_data:
            zip_file = cleaned_data.get("zip_file")
            if zip_file:
                try:
                    self.prepared = services().bundles.prepare(
                        cleaned_data["collection"].pk, zip_file, replacing_id=self.instance.pk
                    )
                except DomainValidationError as e:
                    raise ValidationError(list(e.errors.values())[0])
                cleaned_data["name"] = self.prepared.name

    def save(self, commit=True):
        """Store through the bundle use case (admin and test entry point)."""
        if self.errors:
            raise ValueError("The NIDM results could not be stored: %s" % self.errors.as_json())
        bundles = services().bundles
        data = self.cleaned_data
        if self.prepared is not None:
            bundle_id = bundles.ingest(
                SYSTEM, data["collection"].pk, self.prepared,
                description=data.get("description", ""), tags=data.get("tags") or (),
                replacing_id=self.instance.pk, check_access=False,
            )
        else:
            bundle_id = bundles.change(
                SYSTEM, self.instance.pk,
                {"description": data.get("description", ""), "name": data["name"]},
                tags=data.get("tags"), check_access=False,
            ).id
        self.instance = NIDMResults.objects.get(pk=bundle_id)
        return self.instance

    def save_m2m(self):
        pass


class NIDMViewForm(forms.ModelForm):
    class Meta:
        model = NIDMResults
        exclude = ["is_valid"]

    def __init__(self, *args, **kwargs):
        super(NIDMViewForm, self).__init__(*args, **kwargs)

        for fld in ["ttl_file", "zip_file"]:
            self.fields[fld].widget = PathOnlyWidget()
        for fld in self.fields:
            self.fields[fld].widget.attrs["readonly"] = "readonly"
        self.fields["name"].widget = HiddenInput()
        if self.fields.get("collection"):
            self.fields["collection"].widget = HiddenInput()

        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-2"
        self.helper.field_class = "col-lg-10"
        self.helper.form_tag = True


class NIDMResultStatisticMapForm(ImageForm):
    class Meta:
        model = NIDMResultStatisticMap
        fields = (
            "name",
            "collection",
            "description",
            "map_type",
            "figure",
            "file",
            "tags",
            "nidm_results",
        )

    def __init__(self, *args, **kwargs):
        super(NIDMResultStatisticMapForm, self).__init__(*args, **kwargs)
        # problem with exclude() and fields()
        self.fields["hdr_file"].widget = HiddenInput()
        if self.instance.pk is None:
            self.fields["file"].widget = HiddenInput()
        else:
            for fld in self.fields:
                self.fields[fld].widget.attrs["readonly"] = "readonly"
            # 'disabled' causes the values to not be sent in the POST (?)
            #   self.fields[fld].widget.attrs['disabled'] = 'disabled'

            if self.fields.get("nidm_results"):
                self.fields["nidm_results"].widget = HiddenInput()
            self.fields["map_type"].widget = MapTypeListWidget()
            self.fields["file"].widget = PathOnlyWidget()


class EditNIDMResultStatisticMapForm(NIDMResultStatisticMapForm):
    def __init__(self, user, *args, **kwargs):
        super(EditNIDMResultStatisticMapForm, self).__init__(*args, **kwargs)


def clean_tags(self):
    """
    Force all tags to lowercase.
    """
    tags = self.get("tags", None)
    if tags:
        tags = [t.lower() for t in tags]

    return tags
