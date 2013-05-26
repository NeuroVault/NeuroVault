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


class StudyForm(ModelForm):
    class Meta:
        exclude = ('owner',)
        model = Study

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
