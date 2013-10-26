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

@login_required
def upload_folder(request, collection_pk):
    collection = Collection.objects.get(pk=collection_pk)

    niftiFiles = []
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():

            # Save archive (.zip or .tar.gz) to disk
            if "file" in request.FILES:
                archive_name = request.FILES['file'].name
                _, archive_ext = os.path.splitext(archive_name);
    
                if isinstance(request.FILES['file'],InMemoryUploadedFile):
                    data = request.FILES['file']
                    path = default_storage.save('tmp/archive%s' % archive_ext, ContentFile(data.read()))
                    tmp_file = os.path.join(settings.MEDIA_ROOT, path)
                else:
                    tmp_file = request.FILES['file'].temporary_file_path
    
                # Uncompress archive in a temporary directory
                directory_name = tempfile.mkdtemp()
                if archive_ext == '.zip':
                    compressed = zipfile.ZipFile(tmp_file)
                else:
                    compressed = tarfile.TarFile(fileobj=gzip.open(tmp_file))
                compressed.extractall(path=directory_name);
    
                # Retreive nifti files: .nii, .hdr, .nii.gz
                
                for root, dirs, filenames in os.walk(directory_name, topdown=False):
                    # Ignore hidden directories 
                    filenames = [f for f in filenames if not f[0] == '.']
                    img = [];
                    for fname in filenames:
                        # if fname == 'SPM.mat':
                        #     spmmatfile = fname;
                        filename, ext = os.path.splitext(fname)
                        if ext == ".gz":
                            filename, ext2 = os.path.splitext(fname[:-3])
                            ext = ext2 + ext
                        if ext in ['.nii', '.img', '.nii.gz']:
                            niftiFiles.append(os.path.join(root, fname))
                            
            elif "file_input[]" in request.FILES:
                if not isinstance(request.FILES["file_input[]"], list):
                    request.FILES["file_input[]"] = [request.FILES["file_input[]"]]
                    
                for file in request.FILES["file_input[]"]:
                    archive_name = file.name
                    _, archive_ext = os.path.splitext(archive_name);
                    path = default_storage.save('tmp/archive%s' % archive_ext, ContentFile(file.read()))
                    niftiFiles.append(os.path.join(settings.MEDIA_ROOT, path))
                                      
                            
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
                        
                filename, ext = os.path.splitext(fname)
                if ext == ".gz":
                    filename, ext2 = os.path.splitext(fname[:-3])
                    ext = ext2 + ext


                img = Image.create(fname, fname.split(os.path.sep)[-1], filename, raw_hdr['descrip'], collection_pk, map_type);
                img.save();

            # for fname in filenames:
            #    _, ext = os.path.splitext(fname)
            #    if ext == ".gz":
            #        _, ext2 = os.path.splitext(fname[:-3])
            #        ext = ext2 + ext
            #    print ext

                
            # myImg = Image();
            # myImg.set_name('test');
            # return HttpResponseRedirect('/success/url/')
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
