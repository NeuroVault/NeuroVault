from .models import Study, StatMap
from .forms import StudyFormSet, StudyForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

@login_required
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

@login_required
def edit_study(request, study_id=None):
    if study_id:
        study = Study.objects.get(pk=study_id)
        if study.owner != request.user:
            return HttpResponseForbidden()
    else:
        study = Study(owner=request.user)
    if request.method == "POST":
        form = StudyForm(request.POST, request.FILES, instance=study)
        if form.is_valid():
            form.save()
            # Do something. Should generally end with a redirect. For example:
            return HttpResponseRedirect(study.get_absolute_url())
    else:
        form = StudyForm(instance=study)
        
    context = {"form": form}
    return render(request, "statmaps/edit_study.html", context)

def view_statmap(request, pk):
    #Tal put logic for reading and transforming Nifti to JSON here
    statmap = get_object_or_404(StatMap, pk=pk)
    #pass the JSON data here
    return render(request, 'statmaps/statmap_details.html', {'statmap': statmap})