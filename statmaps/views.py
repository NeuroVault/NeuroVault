from .models import Study
from .forms import StudyFormSet
from django.http.response import HttpResponseRedirect
from django.shortcuts import render


def edit_statmaps(request, study_id):
    study = Study.objects.get(pk=study_id)
    if request.method == "POST":
        formset = StudyFormSet(request.POST, request.FILES, instance=study)
        if formset.is_valid():
            formset.save()
            # Do something. Should generally end with a redirect. For example:
            return HttpResponseRedirect(study.get_absolute_url())
    else:
        formset = StudyFormSet(instance=study)
        
    context = {"formset": formset}
    return render(request, "statmaps/edit_statmaps.html", context)