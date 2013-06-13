from .models import Collection, Image
from .forms import CollectionFormSet, CollectionForm, ImageForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

@login_required
def edit_images(request, collection_pk):
    collection = Collection.objects.get(pk=collection_pk)
    if collection.owner != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        formset = CollectionFormSet(request.POST, request.FILES, instance=collection)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        formset = CollectionFormSet(instance=collection)
        
    context = {"formset": formset}
    return render(request, "statmaps/edit_images.html.haml", context)

@login_required
def edit_collection(request, pk=None):
    page_header = "Add new collection"
    if pk:
        collection = Collection.objects.get(pk=pk)
        page_header = 'Edit collection'
        if collection.owner != request.user:
            return HttpResponseForbidden()
    else:
        collection = Collection(owner=request.user)
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection)
        print form.is_valid()
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        form = CollectionForm(instance=collection)
        
    context = {"form": form, "page_header": page_header}
    return render(request, "statmaps/edit_collection.html.haml", context)

def view_image(request, pk):
    image = get_object_or_404(Image, pk=pk)
    user_owns_image = True if image.collection.owner == request.user else False
    context = {'image': image, 'user': image.collection.owner, 'user_owns_image': user_owns_image }
    return render(request, 'statmaps/image_details.html.haml', context)

def view_collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    user_owns_collection = True if collection.owner == request.user else False
    context = {'collection': collection, 'user': request.user, 'user_owns_collection': user_owns_collection }
    return render(request, 'statmaps/collection_details.html.haml', context)

@login_required
def edit_image(request, pk):
    image = Image.objects.get(pk=pk)
    if image.collection.owner != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES, instance=image)
        print form.is_valid()
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = ImageForm(instance=image)
        
    context = {"form": form}
    return render(request, "statmaps/edit_image.html", context)

def view_images_by_tag(request, tag):
    images = Image.objects.filter(tags__name__in=[tag])
    print images
    context = {'images': images, 'tag': tag}
    return render(request, 'statmaps/images_by_tag.html.haml', context)
