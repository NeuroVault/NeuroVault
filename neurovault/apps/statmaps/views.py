from .models import Study, StatMap
from .forms import StudyFormSet, StudyForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden,\
    HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import log

@login_required
def edit_statmaps(request, study_id):
    study = Study.objects.get(pk=study_id)
    if request.method == "POST":
        formset = StudyFormSet(request.POST, request.FILES, instance=study)
        if formset.is_valid():
            formset.save()
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

def new_study_beta(request):
    if request.method == "POST":
        log.info('received POST to main multiuploader view')
        if request.FILES == None:
            return HttpResponseBadRequest('Must have files attached!')

        #getting file data for farther manipulations
        file = request.FILES[u'files[]']
        wrapped_file = UploadedFile(file)
        filename = wrapped_file.name
        file_size = wrapped_file.file.size
        log.info ('Got file: "'+str(filename)+'"')

        #writing file manually into model
        #because we don't need form of any type.
        image = Image()
        image.title=str(filename)
        image.image=file
        image.save()
        log.info('File saving done')

        #getting url for photo deletion
        file_delete_url = '/delete/'
        
        #getting file url here
        file_url = '/'

        #getting thumbnail url using sorl-thumbnail
        im = get_thumbnail(image, "80x80", quality=50)
        thumb_url = im.url

        #generating json response array
        result = []
        result.append({"name":filename, 
                       "size":file_size, 
                       "url":file_url, 
                       "thumbnail_url":thumb_url,
                       "delete_url":file_delete_url+str(image.pk)+'/', 
                       "delete_type":"POST",})
        response_data = simplejson.dumps(result)
        return HttpResponse(response_data, mimetype='application/json')
    return render(request, 'statmaps/new_study_beta.html')

def view_statmaps_by_tag(request, tag):
    statmaps = StatMap.objects.filter(tags__name__in=[tag])
    context = {'statmaps': statmaps, 'tag': tag}
    return render(request, 'statmaps/statmaps_by_tag.html', context)
