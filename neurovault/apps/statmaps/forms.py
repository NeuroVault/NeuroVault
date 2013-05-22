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

StudyFormSet = inlineformset_factory(Study, StatMap, exclude = ['json_path'])