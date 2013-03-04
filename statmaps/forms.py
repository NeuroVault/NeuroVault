from django.forms import ModelForm
from .models import Study

# Create the form class.
class StudyForm(ModelForm):
    class Meta:
        model = Study
        
    def clean_DOI(self):
        doi = self.cleaned_data['DOI']
        if doi == '':
            doi = None
        return doi