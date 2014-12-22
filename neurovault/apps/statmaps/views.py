from .models import Collection, Image
from .forms import CollectionFormSet, CollectionForm, UploadFileForm, SimplifiedStatisticMapForm,\
    StatisticMapForm, EditStatisticMapForm, OwnerCollectionForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from django.template.context import RequestContext
from django.core.files.base import ContentFile
from neurovault.apps.statmaps.utils import split_filename, generate_pycortex_volume, \
    generate_pycortex_static, generate_url_token, HttpRedirectException, get_paper_properties, \
    get_file_ctime, detect_afni4D, split_afni4D_to_3D, splitext_nii_gz, mkdir_p, \
    send_email_notification
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.db.models import Q
from neurovault import settings
from sendfile import sendfile
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from voxel_query_functions import *

import zipfile
import tarfile
import gzip
import shutil
import nibabel as nib
import re
import tempfile
import neurovault
import os
from collections import OrderedDict
from neurovault.apps.statmaps.models import StatisticMap, Atlas
from xml.dom import minidom
from neurovault.apps.statmaps.forms import EditAtlasForm
from django.db.models.aggregates import Count


def owner_or_contrib(request,collection):
    if collection.owner == request.user or request.user in collection.contributors.all():
        return True
    return False


def get_collection(cid,request,mode=None):
    keyargs = {'pk':cid}
    private_url = re.match(r'^[A-Z]{8}$',cid)
    if private_url is not None:
        keyargs = {'private_token':cid}
    try:
        collection = Collection.objects.get(**keyargs)
        if private_url is None and collection.private:
            if owner_or_contrib(request,collection):
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
        if owner_or_contrib(request,image.collection):
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
    if not owner_or_contrib(request,collection):
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
def edit_collection(request, cid=None):
    page_header = "Add new collection"
    if cid:
        collection = get_collection(cid,request)
        is_owner = True if collection.owner == request.user else False
        page_header = 'Edit collection'
        if not owner_or_contrib(request,collection):
            return HttpResponseForbidden()
    else:
        is_owner = True
        collection = Collection(owner=request.user)
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection)
        if is_owner:
            form = OwnerCollectionForm(request.POST, request.FILES, instance=collection)
        if form.is_valid():
            previous_contribs = set()
            if form.instance.pk is not None:
                previous_contribs = set(form.instance.contributors.all())
            collection = form.save(commit=False)
            if collection.private and collection.private_token is None:
                collection.private_token = generate_url_token()
            collection.save()

            if is_owner:
                form.save_m2m()  # save contributors
                current_contribs = set(collection.contributors.all())
                new_contribs = list(current_contribs.difference(previous_contribs))
                context = {
                    'owner': collection.owner.username,
                    'collection': collection.name,
                    'url': request.META['HTTP_ORIGIN'] + collection.get_absolute_url(),
                }
                subj = '%s has added you to a NeuroVault collection' % context['owner']
                send_email_notification('new_contributor', subj, new_contribs, context)

            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        if is_owner:
            form = OwnerCollectionForm(instance=collection)
        else:
            form = CollectionForm(instance=collection)

    context = {"form": form, "page_header": page_header, "is_owner": is_owner}
    return render(request, "statmaps/edit_collection.html.haml", context)


def view_image(request, pk, collection_cid=None):
    image = get_image(pk,collection_cid,request)
    user_owns_image = True if owner_or_contrib(request,image.collection) else False
    api_cid = pk
    if image.collection.private:
        api_cid = '%s-%s' % (image.collection.private_token,pk)
    context = {'image': image, 'user': image.collection.owner, 'user_owns_image': user_owns_image,
               'api_cid':api_cid}
    if isinstance(image, StatisticMap):
        template = 'statmaps/statisticmap_details.html.haml'
    elif isinstance(image, Atlas):
        template = 'statmaps/atlas_details.html.haml'
    else:
        template = 'statmaps/image_details.html.haml'
    return render(request, template, context)


def view_collection(request, cid):
    collection = get_collection(cid,request)
    edit_permission = True if owner_or_contrib(request,collection) else False
    delete_permission = True if collection.owner == request.user else False
    context = {'collection': collection,
            'user': request.user,
            'delete_permission': delete_permission,
            'edit_permission': edit_permission,
            'cid':cid}
    if owner_or_contrib(request,collection):
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
    if isinstance(image, StatisticMap):
        form = EditStatisticMapForm
    elif isinstance(image, Atlas):
        form = EditAtlasForm
    else:
        raise Exception("unsuported image type")
    if not owner_or_contrib(request,image.collection):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = form(request.user, request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = form(request.user, instance=image)

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
    image = StatisticMap(collection=collection)
    if request.method == "POST":
        form = StatisticMapForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = StatisticMapForm(instance=image)

    context = {"form": form}
    return render(request, "statmaps/add_image.html.haml", context)


@login_required
def upload_folder(request, collection_cid):
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

                atlases = {}
                for root, _, filenames in os.walk(tmp_directory, topdown=False):
                    filenames = [f for f in filenames if not f[0] == '.']
                    for fname in filenames:
                        name, ext = splitext_nii_gz(fname)
                        nii_path = os.path.join(root, fname)
                        if ext == '.xml':
                            print "found xml"
                            dom = minidom.parse(os.path.join(root, fname))
                            for atlas in dom.getElementsByTagName("summaryimagefile"):
                                print "found atlas"
                                path, base, ext = split_filename(atlas.lastChild.nodeValue)
                                nifti_name = os.path.join(path, base)
                                atlases[str(os.path.join(root,nifti_name[1:]))] = os.path.join(root, fname)
                        elif ext not in allowed_extensions:
                            continue
                        elif detect_afni4D(nii_path):
                            niftiFiles.extend(split_afni4D_to_3D(nii_path))
                        else:
                            niftiFiles.append((fname,nii_path))
                        

                for label,fpath in niftiFiles:
                    # Read nifti file information
                    nii = nib.load(fpath)
                    if len(nii.get_shape()) > 3 and nii.get_shape()[3] > 1:
                        print "skipping wrong size"
                        continue
                    hdr = nii.get_header()
                    raw_hdr = hdr.structarr

                    # SPM only !!!
                    # Check if filename corresponds to a T-map
                    Tregexp = re.compile('spmT.*')
                    # Fregexp = re.compile('spmF.*')

                    if Tregexp.search(fpath) is not None:
                        map_type = Image.T
                    else:
                        # Check if filename corresponds to a F-map
                        if Tregexp.search(fpath) is not None:
                            map_type = Image.F
                        else:
                            map_type = StatisticMap.OTHER

                    path, name, ext = split_filename(fpath)
                    dname = name + ".nii.gz"
                    spaced_name = name.replace('_',' ').replace('-',' ')

                    if ext.lower() != ".nii.gz":
                        new_file_tmp_directory = tempfile.mkdtemp()
                        nib.save(nii, os.path.join(new_file_tmp_directory, name))
                        f = ContentFile(open(os.path.join(
                                        new_file_tmp_directory, name)).read(), name=dname)
                        shutil.rmtree(new_file_tmp_directory)
                        label += " (old ext: %s)" % ext
                    else:
                        f = ContentFile(open(fpath).read(), name=dname)

                    collection = get_collection(collection_cid,request)

                    if os.path.join(path, name) in atlases:
                        
                        new_image = Atlas(name=spaced_name,
                                          description=raw_hdr['descrip'], collection=collection)

                        new_image.label_description_file = ContentFile(
                                    open(atlases[os.path.join(path,name)]).read(),
                                                                    name=name + ".xml")
                    else:
                        new_image = StatisticMap(name=spaced_name,
                                description=raw_hdr['descrip'] or label, collection=collection)
                        new_image.map_type = map_type

                    new_image.file = f
                    new_image.save()
            finally:
                shutil.rmtree(tmp_directory)

            return HttpResponseRedirect('')
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
    path = os.path.join(settings.PRIVATE_MEDIA_ROOT,'images',str(collection.id),img_name)
    return sendfile(request, path)


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
    
    non_empty_collections_count = Collection.objects.annotate(num_submissions=Count('image')).filter(num_submissions__gt = 0).count()
    public_collections_count = Collection.objects.filter(private=False).annotate(num_submissions=Count('image')).filter(num_submissions__gt = 0).count()
    public_collections_with_DOIs_count = Collection.objects.filter(private=False).exclude(Q(DOI__isnull=True) | Q(DOI__exact='')).annotate(num_submissions=Count('image')).filter(num_submissions__gt = 0).count()
    context = {'collections_by_journals': collections_by_journals,
               'non_empty_collections_count': non_empty_collections_count,
               'public_collections_count': public_collections_count,
               'public_collections_with_DOIs_count': public_collections_with_DOIs_count}
    return render(request, 'statmaps/stats.html.haml', context)


def papaya_js_embed(request, pk, iframe=None):
    tpl = 'papaya_embed.tpl.js'
    mimetype = "text/javascript"
    if iframe is not None:
        tpl = 'papaya_frame.html.haml'
        mimetype = "text/html"
    image = get_image(pk,None,request)
    if image.collection.private:
        return HttpResponseForbidden()
    context = {'image': image, 'request':request}
    return render_to_response('statmaps/%s' % tpl,
                              context, content_type=mimetype)

@csrf_exempt
def atlas_query_region(request):
    # this query is significantly faster (from 2-4 seconds to <1 second) if the synonyms don't need to be queried
    # i was previously in contact with NIF and it seems like it wouldn't be too hard to download all the synonym data
    search = request.GET.get('region','')
    atlas = request.GET.get('atlas','').replace('\'', '')
    neurovault_root = os.path.dirname(os.path.dirname(os.path.realpath(neurovault.__file__)))
    try:
        atlas_image = Atlas.objects.filter(name=atlas)[0].file
        atlas_xml = Atlas.objects.filter(name=atlas)[0].label_description_file
    except IndexError:
        return JSONResponse('could not find %s' % atlas, status=400)
    if request.method == 'GET':       
        atlas_xml.open()
        root = ET.fromstring(atlas_xml.read())
        atlas_xml.close()
        atlasRegions = [x.text.lower() for x in root.find('data').findall('label')]
        if search in atlasRegions:
            searchList = [search]
        else:
            synonymsDict = {}
            with open(os.path.join(neurovault_root, 'neurovault/apps/statmaps/NIFgraph.pkl'),'rb') as input:
                graph = pickle.load(input)
            for atlasRegion in atlasRegions:
                synonymsDict[atlasRegion] = getSynonyms(atlasRegion)
            try:
                searchList = toAtlas(search, graph, atlasRegions, synonymsDict)
            except ValueError:
                return JSONResponse('region not in atlas or ontology', status=400)
            if searchList == 'none':
                return JSONResponse('could not map specified region to region in specified atlas', status=400)
        try:
            data = {'voxels':getAtlasVoxels(searchList, atlas_image, atlas_xml)}
        except ValueError:
            return JSONResponse('region not in atlas', status=400)

        return JSONResponse(data)

@csrf_exempt
def atlas_query_voxel(request):
    X = request.GET.get('x','')
    Y = request.GET.get('y','')
    Z = request.GET.get('z','')
    atlas = request.GET.get('atlas','').replace('\'', '')
    try:
        atlas_image = Atlas.objects.filter(name=atlas)[0].file
        atlas_xml = Atlas.objects.filter(name=atlas)[0].label_description_file
    except IndexError:
        return JSONResponse('could not find %s' % atlas, status=400)
    try:
        data = voxelToRegion(X,Y,Z,atlas_image, atlas_xml)
    except IndexError:
        return JSONResponse('one or more coordinates are out of range', status=400)
    return JSONResponse(data)

# Compare Two Images
def compare_images(request,pk1,pk2):
    image1 = get_object_or_404(Image,pk=pk1)
    image2 = get_object_or_404(Image,pk=pk2)        
    base1, fname1, _ = split_filename(image1.file.path)
    base2, fname2, _ = split_filename(image2.file.path)
    pycortex_dir1 = os.path.join(base1, fname1 + "_pycortex")
    pycortex_dir2 = os.path.join(base2, fname2 + "_pycortex")

    # TODO: Here we will add NeuroVault atlases, something like:
    #atlas_image = Atlas.objects.filter(name=atlas)[0].file
    #atlas_xml = Atlas.objects.filter(name=atlas)[0].label_description_file 
    
    # call image_compare function to read in data, do regional comparisons for different metrics

    if not os.path.exists(pycortex_dir1):
        volume = generate_pycortex_volume(image1)
        generate_pycortex_static({image.name: volume}, pycortex_dir1)

    if not os.path.exists(pycortex_dir2):
        volume = generate_pycortex_volume(image2)
        generate_pycortex_static({image.name: volume}, pycortex_dir2)

    _, _, ext1 = split_filename(image1.file.url)
    _, _, ext2 = split_filename(image1.file.url)
    pycortex_url1 = image1.file.url[:-len(ext1)] + "_pycortex/index.html"
    pycortex_url2 = image1.file.url[:-len(ext1)] + "_pycortex/index.html"
    return redirect(pycortex_url1)

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)
