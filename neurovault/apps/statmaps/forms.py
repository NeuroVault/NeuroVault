from django.forms import ModelForm
from .models import Study, StatMap
from django.forms.models import inlineformset_factory
import os
from django.core.exceptions import ValidationError
import nibabel as nb
from tempfile import mkstemp, NamedTemporaryFile
import shutil

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


class StatMapForm(ModelForm):
    # Add some custom validation to our file field
    def clean_file(self):
        file = self.cleaned_data['file']
        if file:
            if not os.path.splitext(file.name)[1] in [".gz", ".nii", ".img"]:
                raise ValidationError("Doesn't have proper extension")
            # Here we need to now to read the file and see if it's actually
            # a valid audio file. I don't know what the best library is to
            # to do this
            fname = file.name.split("/")[-1]
            with NamedTemporaryFile(suffix=fname, delete=False) as f:
                fname = f.name
                f.write(file.file.read())
                f.close()
                try:
                    nb.load(fname)
                except Exception, e:
                    raise ValidationError(e)
                finally:
                    os.remove(fname)
            return file
        else:
            raise ValidationError("Couldn't read uploaded file")

    def clean_hdr_file(self):
        file = self.cleaned_data['hdr_file']
        if file:
            if not os.path.splitext(file.name)[1] in [".hdr"]:
                raise ValidationError("Doesn't have proper extension")
            return file


StudyFormSet = inlineformset_factory(
    Study, StatMap, form=StatMapForm, exclude=['json_path'])
