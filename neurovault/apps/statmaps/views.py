from .models import Collection, Image
from .forms import CollectionFormSet, CollectionForm, ImageForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, render_to_response
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from neurovault.apps.statmaps.forms import UploadFileForm
from django.template.context import RequestContext
from django.core.files.uploadedfile import InMemoryUploadedFile
import tempfile
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from neurovault import settings
import zipfile
import tarfile, gzip
import fnmatch
import shutil
from nibabel.testing import data_path
import nibabel as nib
import re
from neurovault.apps.statmaps.storage import NiftiGzStorage
import errno

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
    if collection.owner == request.user:
        form = UploadFileForm()
        c = RequestContext(request)
        c.update(context)
        return render_to_response('statmaps/collection_details.html.haml', {'form': form}, c)
    else:
        return render(request, 'statmaps/collection_details.html.haml', context)

@login_required
def delete_collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    if collection.owner != request.user:
        return HttpResponseForbidden()
    collection.delete()
    return render(request, "statmaps/deleted_collection.html")

@login_required
def edit_image(request, pk):
    image = Image.objects.get(pk=pk)
    if image.collection.owner != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = ImageForm(instance=image)
        
    context = {"form": form}
    return render(request, "statmaps/edit_image.html", context)


def splitext_nii_gz(fname):
    head, ext = os.path.splitext(fname)
    if ext.lower() == ".gz":
        _, ext2 = os.path.splitext(fname[:-3])
        ext = ext2 + ext
    return head, ext

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


@login_required
def upload_folder(request, collection_pk):
    allowed_extensions = ['.nii', '.img', '.nii.gz']
    niftiFiles = []
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            
            tmp_directory = tempfile.mkdtemp()
            print tmp_directory
            try:
                # Save archive (.zip or .tar.gz) to disk
                if "file" in request.FILES:
                    archive_name = request.FILES['file'].name
                    _, archive_ext = os.path.splitext(archive_name)
                    if archive_ext == '.zip':
                        compressed = zipfile.ZipFile(request.FILES['file'])
                    else:
                        compressed = tarfile.TarFile(fileobj=gzip.open(request.FILES['file']))  
                    compressed.extractall(path=tmp_directory)

                elif "file_input[]" in request.FILES:
                    print request.POST["paths"]                        
                    for f, path in zip(request.FILES.getlist("file_input[]"), request.POST["paths"].split("###")):
                        new_path = os.path.join(tmp_directory, path)
                        mkdir_p(new_path)
                        filename = os.path.join(new_path,f.name)
                        tmp_file = open(filename, 'w')
                        tmp_file.write(f.read())
                        tmp_file.close()
                        
                for root, _, filenames in os.walk(tmp_directory, topdown=False):
                    filenames = [f for f in filenames if not f[0] == '.']
                    for fname in filenames:
                        _, ext = splitext_nii_gz(fname)             
                        if ext in allowed_extensions:
                            niftiFiles.append(os.path.join(root, fname))
                                              
                for fname in niftiFiles:
                    # Read nifti file information
                    img = nib.load(fname)
                    hdr = img.get_header()
                    raw_hdr = hdr.structarr
    
                    # SPM only !!!
                    # Check if filename corresponds to a T-map
                    Tregexp = re.compile('spmT.*');
                    Fregexp = re.compile('spmF.*');
                    if Tregexp.search(fname) is not None:
                        map_type = Image.T;
                    else:
                        # Check if filename corresponds to a F-map
                        if Tregexp.search(fname) is not None:
                            map_type = Image.F;
                        else:
                            map_type = Image.OTHER;
                    img = Image.create(fname, fname.split(os.path.sep)[-1], fname.split(os.path.sep)[-1], raw_hdr['descrip'], collection_pk, map_type);
                    img.save();
                    
            finally:
                shutil.rmtree(tmp_directory)

            return HttpResponseRedirect('editimages');
    else:
        form = UploadFileForm()
    return render_to_response("statmaps/upload_folder.html", {'form': form},  RequestContext(request))

@login_required
def delete_image(request, pk):
    image = get_object_or_404(Image, pk=pk)
    if image.collection.owner != request.user:
        return HttpResponseForbidden()
    image.delete()
    return render(request, "statmaps/deleted_image.html")

def view_images_by_tag(request, tag):
    images = Image.objects.filter(tags__name__in=[tag])
    context = {'images': images, 'tag': tag}
    return render(request, 'statmaps/images_by_tag.html.haml', context)
