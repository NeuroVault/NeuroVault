from .models import Collection, Image
from .forms import CollectionFormSet, CollectionForm, SingleStatisticMapForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from neurovault.apps.statmaps.forms import UploadFileForm, SimplifiedStatisticMapForm,\
    StatisticMapForm, AddStatisticMapForm
from django.template.context import RequestContext
from django.core.files.base import ContentFile
from neurovault.apps.statmaps.utils import split_filename, generate_pycortex_volume, \
    generate_pycortex_static, generate_url_token, HttpRedirectException, get_paper_properties, \
    get_file_ctime, parse_nidm_results
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db.models import Q
from neurovault import settings
from sendfile import sendfile

import zipfile
import tarfile
import gzip
import shutil
import nibabel as nib
import re
import errno
import tempfile
import os
from collections import OrderedDict
from neurovault.apps.statmaps.nidm import StatisticMap


def get_collection(cid,request,mode=None):
    keyargs = {'pk':cid}
    private_url = re.match(r'^[A-Z]{8}$',cid)
    if private_url is not None:
        keyargs = {'private_token':cid}
    try:
        collection = Collection.objects.get(**keyargs)
        if private_url is None and collection.private:
            if collection.owner == request.user:
                if mode in ['file','api']:
                    raise PermissionDenied()
                else:
                    raise HttpRedirectException(collection.get_absolute_url())
            else:
                raise PermissionDenied()
    except Collection.DoesNotExist:
        raise Http404
    else:
        return collection


def get_image(pk,collection_cid,request,mode=None):
    image = get_object_or_404(Image, pk=pk)
    if image.collection.private and image.collection.private_token != collection_cid:
        if image.collection.owner == request.user:
            if mode == 'api':
                raise PermissionDenied()
            else:
                raise HttpRedirectException(image.get_absolute_url())
        else:
            raise PermissionDenied()
    else:
        return image


@login_required
def edit_images(request, collection_cid):
    collection = get_collection(collection_cid,request)
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
    return render(request, "statmaps/edit_images_simpler.html.haml", context)


@login_required
def edit_collection(request, cid=None):
    page_header = "Add new collection"
    if cid:
        collection = get_collection(cid,request)
        page_header = 'Edit collection'
        if collection.owner != request.user:
            return HttpResponseForbidden()
    else:
        collection = Collection(owner=request.user)
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection)
        if form.is_valid():
            collection = form.save(commit=False)
            if collection.private and collection.private_token is None:
                collection.private_token = generate_url_token()
            collection.save()

            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        form = CollectionForm(instance=collection)

    context = {"form": form, "page_header": page_header}
    return render(request, "statmaps/edit_collection.html.haml", context)


def view_image(request, pk, collection_cid=None):
    image = get_image(pk,collection_cid,request)
    user_owns_image = True if image.collection.owner == request.user else False
    api_cid = pk
    if image.collection.private:
        api_cid = '%s-%s' % (image.collection.private_token,pk)
    context = {'image': image, 'user': image.collection.owner, 'user_owns_image': user_owns_image,
            'api_cid':api_cid}
    return render(request, 'statmaps/image_details.html.haml', context)


def view_collection(request, cid):
    collection = get_collection(cid,request)
    user_owns_collection = True if collection.owner == request.user else False
    context = {'collection': collection,
            'user': request.user,
            'user_owns_collection': user_owns_collection,
            'cid':cid}
    if collection.owner == request.user:
        form = UploadFileForm()
        c = RequestContext(request)
        c.update(context)
        return render_to_response('statmaps/collection_details.html.haml', {'form': form}, c)
    else:
        return render(request, 'statmaps/collection_details.html.haml', context)


@login_required
def delete_collection(request, cid):
    collection = get_collection(cid,request)
    if collection.owner != request.user:
        return HttpResponseForbidden()
    collection.delete()
    return render(request, "statmaps/deleted_collection.html")


@login_required
def edit_image(request, pk):
    image = get_object_or_404(Image,pk=pk)
    if image.collection.owner != request.user:
        return HttpResponseForbidden()
    if request.method == "POST":
        form = SingleStatisticMapForm(request.user, request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = SingleStatisticMapForm(request.user, instance=image)

    context = {"form": form}
    return render(request, "statmaps/edit_image.html.haml", context)


@login_required
def add_image_for_neurosynth(request):
    temp_collection_name = "%s's temporary collection" % request.user.username
    #this is a hack we need to make sure this collection can be only
    #owned by the same user
    try:
        temp_collection = Collection.objects.get(name=temp_collection_name)
    except Collection.DoesNotExist:
        priv_token = generate_url_token()
        temp_collection = Collection(name=temp_collection_name,
                                     owner=request.user,
                                     private=True,
                                     private_token=priv_token)
        temp_collection.save()
    image = Image(collection=temp_collection)
    if request.method == "POST":
        form = SimplifiedStatisticMapForm(request.user, request.POST, request.FILES, instance=image)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect("http://neurosynth.org/decode/?neurovault=%s-%s" % (
                temp_collection.private_token,image.id))
    else:
        form = SimplifiedStatisticMapForm(request.user, instance=image)

    context = {"form": form}
    return render(request, "statmaps/add_image_for_neurosynth.html.haml", context)

@login_required
def add_image(request, collection_cid):
    collection = get_collection(collection_cid,request)
    image = Image(collection=collection)
    if request.method == "POST":
        form = AddStatisticMapForm(request.user, request.POST, request.FILES, instance=image)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = AddStatisticMapForm(request.user, instance=image)

    context = {"form": form}
    return render(request, "statmaps/add_image.html.haml", context)


def splitext_nii_gz(fname):
    head, ext = os.path.splitext(fname)
    if ext.lower() == ".gz":
        _, ext2 = os.path.splitext(fname[:-3])
        ext = ext2 + ext
    return head, ext


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


@login_required
def upload_folder(request, collection_cid):
    allowed_extensions = ['.nii', '.img', '.nii.gz']
    collection = get_collection(collection_cid,request)
    niftiFiles = []
    if request.method == 'POST':
        print request.POST
        print request.FILES
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if "file" in request.FILES and request.FILES['file'].name.endswith(".nidm.zip"):
                parse_nidm_results(request.FILES['file'], collection)
                return HttpResponseRedirect('.')
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
                    for f, path in zip(request.FILES.getlist(
                                       "file_input[]"), request.POST.getlist("paths[]")):
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
                    Tregexp = re.compile('spmT.*')
                    # Fregexp = re.compile('spmF.*')
                    if Tregexp.search(fname) is not None:
                        map_type = StatisticMap.T
                    else:
                        # Check if filename corresponds to a F-map
                        if Tregexp.search(fname) is not None:
                            map_type = StatisticMap.F
                        else:
                            map_type = StatisticMap.OTHER

                    path, name, ext = split_filename(fname)
                    name += ".nii.gz"
                    db_name = os.path.join(path.replace(tmp_directory,""), name)
                    db_name = os.path.sep.join(db_name.split(os.path.sep)[2:])
                    if ext.lower() != ".nii.gz":
                        new_file_tmp_directory = tempfile.mkdtemp()
                        nib.save(nii, os.path.join(new_file_tmp_directory, name))
                        f = ContentFile(open(os.path.join(
                                        new_file_tmp_directory, name)).read(), name=name)
                        shutil.rmtree(new_file_tmp_directory)
                        db_name += " (old ext: %s)" % ext
                    else:
                        f = ContentFile(open(fname).read(), name=name)

                    new_image = Image(name=db_name,
                                      description=raw_hdr['descrip'], collection=collection)
                    new_image.file = f
                    new_image.statisticType = map_type
                    new_image.save()
            finally:
                shutil.rmtree(tmp_directory)

            return HttpResponseRedirect('.')
    else:
        form = UploadFileForm()
    return render_to_response("statmaps/upload_folder.html",
                              {'form': form},  RequestContext(request))


@login_required
def delete_image(request, pk):
    image = get_object_or_404(Image,pk=pk)
    if image.collection.owner != request.user:
        return HttpResponseForbidden()
    image.delete()
    return render(request, "statmaps/deleted_image.html")


@login_required
def view_images_by_tag(request, tag):
    images = Image.objects.filter(tags__name__in=[tag]).filter(
                                        Q(collection__private=False) |
                                        Q(collection__owner=request.user))
    context = {'images': images, 'tag': tag}
    return render(request, 'statmaps/images_by_tag.html.haml', context)


def view_image_with_pycortex(request, pk, collection_cid=None):
    image = get_image(pk,collection_cid,request)
    base, fname, _ = split_filename(image.file.path)
    pycortex_dir = os.path.join(base, fname + "_pycortex")

    if not os.path.exists(pycortex_dir):
        volume = generate_pycortex_volume(image)
        generate_pycortex_static({image.name: volume}, pycortex_dir)

    _, _, ext = split_filename(image.file.url)
    pycortex_url = image.file.url[:-len(ext)] + "_pycortex/index.html"
    return redirect(pycortex_url)


def view_collection_with_pycortex(request, cid):
    volumes = {}
    collection = get_collection(cid,request,mode='file')
    images = Image.objects.filter(collection=collection)

    basedir = os.path.split(images[0].file.path)[0]
    baseurl = os.path.split(images[0].file.url)[0]
    output_dir = os.path.join(basedir, "pycortex_all")
    html_path = os.path.join(basedir, "pycortex_all/index.html")
    pycortex_url = os.path.join(baseurl, "pycortex_all/index.html")

    if os.path.exists(output_dir):
        # check if collection contents have changed
        if collection.modify_date > get_file_ctime(html_path):
            shutil.rmtree(output_dir)
            return view_collection_with_pycortex(request, cid)
    else:
        for image in images:
            vol = generate_pycortex_volume(image)
            volumes[image.name] = vol
        generate_pycortex_static(volumes, output_dir)

    return redirect(pycortex_url)


def serve_image(request, collection_cid, img_name):
    collection = get_collection(collection_cid,request,mode='file')
    image = Image.objects.get(collection=collection,file__endswith='/'+img_name)
    return sendfile(request, image.file.path)


def serve_pycortex(request, collection_cid, path, pycortex_dir='pycortex_all'):
    collection = get_collection(collection_cid,request,mode='file')
    int_path = os.path.join(settings.PRIVATE_MEDIA_ROOT,
                            'images',str(collection.id),pycortex_dir,path)
    return sendfile(request, int_path)


def stats_view(request):
    collections_by_journals = {}
    for collection in Collection.objects.filter(
                                private=False).exclude(Q(DOI__isnull=True) | Q(DOI__exact='')):
        if not collection.journal_name:
            _,_,_,_, collection.journal_name = get_paper_properties(collection.DOI)
            collection.save()
        if collection.journal_name not in collections_by_journals.keys():
            collections_by_journals[collection.journal_name] = 1
        else:
            collections_by_journals[collection.journal_name] += 1
    collections_by_journals = OrderedDict(sorted(collections_by_journals.items(
                                                ), key=lambda t: t[1], reverse=True))
    context = {'collections_by_journals': collections_by_journals}
    return render(request, 'statmaps/stats.html.haml', context)
