from .models import Collection, Image
from .forms import CollectionFormSet, CollectionForm, ImageForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response, render,\
    redirect
from neurovault.apps.statmaps.forms import UploadFileForm, SimplifiedImageForm
from django.template.context import RequestContext
from django.core.files.base import ContentFile
from neurovault.apps.statmaps.utils import split_filename, generate_pycortex_dir
from django.utils.http import quote, urlquote

import neurovault.settings as settings
import zipfile
import tarfile, gzip
import shutil
import nibabel as nib
import re
import errno
import tempfile
import os

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
    image = get_object_or_404(Image, pk=pk)
    if image.collection.owner != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ImageForm(request.user, request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = ImageForm(request.user, instance=image)
        
    context = {"form": form}
    return render(request, "statmaps/edit_image.html.haml", context)

@login_required
def add_image_for_neurosynth(request):
    temp_collection_name = "%s's temporary collection"%request.user.username
    #this is a hack we need to make sure this collection can be only 
    #owned by the same user
    try:
        temp_collection = Collection.objects.get(name=temp_collection_name)
    except Collection.DoesNotExist:
        temp_collection = Collection(name=temp_collection_name, 
                                     owner=request.user)
        temp_collection.save()
    image = Image(collection=temp_collection)
    if request.method == "POST":
        form = SimplifiedImageForm(request.user, request.POST, request.FILES, instance=image)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect("http://neurosynth.org/decode/?neurovault=%s"%image.id)
    else:
        form = SimplifiedImageForm(request.user, instance=image)
        
    context = {"form": form}
    return render(request, "statmaps/add_image_for_neurosynth.html.haml", context)

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
        print request.POST
        print request.FILES
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
                    for f, path in zip(request.FILES.getlist("file_input[]"), request.POST.getlist("paths[]")):
                        new_path, _ = os.path.split(os.path.join(tmp_directory, path))
                        mkdir_p(new_path)
                        filename = os.path.join(new_path,f.name)
                        tmp_file = open(filename, 'w')
                        tmp_file.write(f.read())
                        tmp_file.close()
                else:
                    raise
                        
                for root, _, filenames in os.walk(tmp_directory, topdown=False):
                    filenames = [f for f in filenames if not f[0] == '.']
                    for fname in filenames:
                        _, ext = splitext_nii_gz(fname)             
                        if ext in allowed_extensions:
                            niftiFiles.append(os.path.join(root, fname))
                                              
                for fname in niftiFiles:
                    # Read nifti file information
                    nii = nib.load(fname)
                    if len(nii.get_shape()) > 3 and nii.get_shape()[3] > 1:
                        continue
                    hdr = nii.get_header()
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
                    
                    path, name, ext = split_filename(fname)
                    name += ".nii.gz"
                    db_name = os.path.join(path.replace(tmp_directory,""), name)
                    db_name = os.path.sep.join(db_name.split(os.path.sep)[2:])
                    if ext.lower() != ".nii.gz":
                        new_file_tmp_directory = tempfile.mkdtemp()
                        nib.save(nii, os.path.join(new_file_tmp_directory, name))
                        f = ContentFile(open(os.path.join(new_file_tmp_directory, name)).read(), name=name)
                        shutil.rmtree(new_file_tmp_directory)
                        db_name += " (old ext: %s)"%ext
                    else:
                        f = ContentFile(open(fname).read(), name=name)
                    
                    collection = Collection.objects.get(pk=collection_pk)
                    new_image = Image(name=db_name, description=raw_hdr['descrip'], collection=collection)
                    new_image.file = f
                    new_image.map_type = map_type
                    new_image.save()
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

def view_image_with_pycortex(request, pk):
    image = get_object_or_404(Image, pk=pk)
    base, fname, _ = split_filename(image.file.path)
    pycortex_dir = os.path.join(base, fname + "_pycortex")
    print image.file.path, pycortex_dir, pk
    
    if not os.path.exists(pycortex_dir):
        generate_pycortex_dir(str(image.file.path), str(pycortex_dir), "trans_%s"%pk)
        
    base, fname, _ = split_filename(image.file.url)
    pycortex_url = os.path.join(base, fname + "_pycortex/index.html")
    print pycortex_url
    return redirect('http://' + request.get_host() + pycortex_url)
