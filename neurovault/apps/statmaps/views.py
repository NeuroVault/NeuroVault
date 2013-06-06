from .models import Collection, StatMap
from .forms import CollectionFormSet, CollectionForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

@login_required
def edit_statmaps(request, collection_pk):
    collection = Collection.objects.get(pk=collection_pk)
    if request.method == "POST":
        formset = CollectionFormSet(request.POST, request.FILES, instance=collection)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        formset = CollectionFormSet(instance=collection)
        
    context = {"formset": formset}
    return render(request, "statmaps/edit_statmaps.html", context)

@login_required
def edit_collection(request, pk=None):
    if pk:
        collection = Collection.objects.get(pk=pk)
        if collection.owner != request.user:
            return HttpResponseForbidden()
    else:
        collection = Collection(owner=request.user)
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection)
        print "post"
        print form.is_valid()
        if form.is_valid():
            print "saving"
            form.save()
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        form = CollectionForm(instance=collection)
        
    context = {"form": form}
    return render(request, "statmaps/edit_collection.html", context)

def view_statmap(request, pk):
    #Tal put logic for reading and transforming Nifti to JSON here
    statmap = get_object_or_404(StatMap, pk=pk)
    #pass the JSON data here
    return render(request, 'statmaps/statmap_details.html', {'statmap': statmap})

def view_statmaps_by_tag(request, tag):
    statmaps = StatMap.objects.filter(tags__name__in=[tag])
    context = {'statmaps': statmaps, 'tag': tag}
    return render(request, 'statmaps/statmaps_by_tag.html', context)
