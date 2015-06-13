from neurovault.apps.statmaps.models import Collection, Image, Atlas, Comparison, StatisticMap, NIDMResults, NIDMResultStatisticMap,\
    BaseStatisticMap
from neurovault.apps.statmaps.forms import CollectionFormSet, CollectionForm, UploadFileForm, SimplifiedStatisticMapForm,\
    StatisticMapForm, EditStatisticMapForm, OwnerCollectionForm, EditAtlasForm, AtlasForm, \
    EditNIDMResultStatisticMapForm, NIDMResultsForm, NIDMViewForm, AddStatisticMapForm
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from neurovault.apps.statmaps.utils import split_filename, generate_pycortex_volume, \
    generate_pycortex_static, generate_url_token, HttpRedirectException, get_paper_properties, \
    get_file_ctime, detect_afni4D, split_afni4D_to_3D, splitext_nii_gz, mkdir_p, \
    send_email_notification, populate_nidm_results, get_server_url, populate_feat_directory, \
    detect_feat_directory, format_image_collection_names, count_existing_comparisons, \
    count_processing_comparisons, get_existing_comparisons
from neurovault.apps.statmaps.voxel_query_functions import *
from django.contrib.auth.decorators import login_required
from pybraincompare.compare import scatterplot, search
from pybraincompare.mr.datasets import get_mni_atlas
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.fields import FieldDoesNotExist
from neurovault.settings import PRIVATE_MEDIA_ROOT
from django.template.context import RequestContext
from rest_framework.renderers import JSONRenderer
from django.core.files.base import ContentFile
from django.db.models.aggregates import Count
from django.http import Http404, HttpResponse
from django.db.models import Q, Count
from sklearn.externals import joblib
from collections import OrderedDict, defaultdict
from django.contrib import messages
from django.forms import widgets
from neurovault import settings
from sendfile import sendfile
from xml.dom import minidom
from fnmatch import fnmatch
import nibabel as nib
from glob import glob
import neurovault
import traceback
import tempfile
import zipfile
import tarfile
import shutil
import pandas
import gzip
import re
import os
from neurovault.apps.statmaps.tasks import save_resampled_transformation_single
from django.views.decorators.cache import never_cache
import json


def owner_or_contrib(request,collection):
    if collection.owner == request.user or request.user in collection.contributors.all() or request.user.is_superuser:
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
@never_cache
def edit_images(request, collection_cid):
    collection = get_collection(collection_cid,request)
    if not owner_or_contrib(request,collection):
        return HttpResponseForbidden()
    if request.method == "POST":
        formset = CollectionFormSet(request.POST, request.FILES, instance=collection)
        for n,form in enumerate(formset):
            # hack: check fields to determine polymorphic type
            if form.instance.polymorphic_ctype is None:
                atlas_f = 'image_set-{0}-label_description_file'.format(n)
                has_atlas = [v for v in form.files if v == atlas_f]
                if has_atlas:
                    use_model = Atlas
                    use_form = AtlasForm
                else:
                    use_model = StatisticMap
                    use_form = StatisticMapForm
                form.instance = use_model(collection=collection)
                form.base_fields = use_form.base_fields
                form.fields = use_form.base_fields
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        formset = CollectionFormSet(instance=collection)

    blank_statmap = StatisticMapForm(instance=StatisticMap(collection=collection))
    blank_atlas = AtlasForm(instance=Atlas(collection=collection))
    upload_form = UploadFileForm()
    context = {"formset": formset, "blank_statmap": blank_statmap,
               "blank_atlas": blank_atlas, "upload_form":upload_form}

    return render(request, "statmaps/edit_images.html", context)


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
        if is_owner:
            form = OwnerCollectionForm(request.POST, request.FILES, instance=collection)
        else:
            form = CollectionForm(request.POST, request.FILES, instance=collection)
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
                    'url': get_server_url(request) + collection.get_absolute_url(),
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


def dict_factory(header_row, row):
    d = {}
    for idx, field_name in enumerate(header_row):
        d[field_name] = row[idx]
    return d


def convert_to_list(data):
    return [dict_factory(data[0], row) for row in data[1:]]


def list_to_dict(iterable, key):
    return dict((key(item), item) for item in iterable)


def diff_dicts(dict_a, dict_b):
    keys = getattr(dict, 'viewkeys', dict.keys)
    return keys(dict_a) - keys(dict_b)


# TODO: add force flag
def pair_data_and_objects(metadata_dict, image_obj_dict):
    extra_files = diff_dicts(image_obj_dict, metadata_dict)

    if extra_files:
        raise ValidationError(
            "Missing metadata for %s. Specify metadata rows "
            "for every image in the collection." % ', '.join(extra_files))

    for image_filename, metadata in metadata_dict.items():
        image_obj = image_obj_dict.get(image_filename)
        if not image_obj:
            raise ValidationError('File is not found in the collection: %s' %
                                  image_filename,
                                  code='file_not_found')
        yield (metadata, image_obj)


def error_response(exception):
    resp = None

    if hasattr(exception, 'items_messages_dict'):
        resp = {'messages': exception.items_messages_dict}
    else:
        resp = {'message': exception.message}

    return JSONResponse(resp, status=400)


def clean_u_prefix(s):
    return re.sub(r'u(\'[^\']+?\')', '\\1', s)


def clearn_messages(message_dict):
    return dict((k, map(clean_u_prefix, v))
                for k, v in message_dict.items())


class MetadataGridValidationError(ValidationError):
    def __init__(self, items_messages_dict):
        self.items_messages_dict = items_messages_dict


def save_metadata(collection, metadata):
    def file_basename(image_obj):
        return os.path.basename(image_obj.file.name)

    image_obj_errors = defaultdict(list)
    image_obj_list = []

    metadata_list = convert_to_list(metadata)
    metadata_dict = list_to_dict(metadata_list,
                                 key=lambda x: x['Filename'])

    image_obj_list = collection.image_set.all()
    image_obj_dict = list_to_dict(image_obj_list,
                                  key=file_basename)

    pairs = pair_data_and_objects(metadata_dict,
                                  image_obj_dict)
    for metadata_item, image_obj in pairs:
        for key in metadata_item:
            if key in image_obj.get_fixed_fields():
                try:
                    image_obj._meta.get_field_by_name(key)
                except FieldDoesNotExist:
                    raise FieldDoesNotExist("Error in fixed field name in "
                                            "get_fixed_fields. Field %s "
                                            "doesn't exist." % key)
                setattr(image_obj, key, metadata_item[key])
            else:
                if key != 'Filename':
                    if not image_obj.data:
                        image_obj.data = {}
                    image_obj.data[key] = metadata_item[key]

        try:
            image_obj.full_clean()
        except ValidationError as e:
            image_obj_errors[file_basename(image_obj)].append(
                clearn_messages(e.message_dict))

    if image_obj_errors:
        raise MetadataGridValidationError(image_obj_errors)

    for image_obj in image_obj_list:
        image_obj.save()

    return metadata_list


def handle_post_metadata(request, collection, success_message):
    metadata = json.loads(request.body)

    try:
        metadata_list = save_metadata(collection, metadata)
    except ValidationError as e:
        return error_response(e)

    messages.success(request,
                     success_message,
                     extra_tags='alert-success')
    return JSONResponse(metadata_list, status=200)


def get_all_metadata_keys(image_obj_list):
    return set(key for image in image_obj_list if image.data
               for key in image.data)


def get_images_metadata(collection):
    image_obj_list = collection.image_set.all()
    metadata_keys = list(get_all_metadata_keys(image_obj_list))
    fixed_fields = list(StatisticMap.get_fixed_fields())

    def list_metadata(image):
        data = image.data

        return ([os.path.basename(image.file.name)] +
                [getattr(image, field) for field in fixed_fields] +
                [data.get(key, '') for key in metadata_keys])

    return [['Filename'] + fixed_fields + metadata_keys] + map(list_metadata,
                                                               image_obj_list)


@csrf_exempt
@login_required
def import_metadata(request, collection_cid):
    collection = get_collection(collection_cid, request)

    if not owner_or_contrib(request, collection):
        return HttpResponseForbidden()

    if request.method == "POST":
        return handle_post_metadata(request, collection,
                                    'Image metadata have been imported.')

    return render(request, "statmaps/import_metadata.html", {
        'collection': collection})


@csrf_exempt
@login_required
def edit_metadata(request, collection_cid):
    collection = get_collection(collection_cid, request)

    if not owner_or_contrib(request, collection):
        return HttpResponseForbidden()

    if request.method == "POST":
        return handle_post_metadata(request, collection,
                                    'Images metadata have been saved.')

    metadata = get_images_metadata(collection)

    return render(request, "statmaps/edit_metadata.html", {
        'collection': collection,
        'metadata': json.dumps(metadata)})


def view_image(request, pk, collection_cid=None):
    image = get_image(pk,collection_cid,request)
    user_owns_image = owner_or_contrib(request,image.collection)
    api_cid = pk

    comparison_is_possible = (image.collection.private == False and isinstance(image, BaseStatisticMap) and \
                              image.is_thresholded == False)

    if image.collection.private:
        api_cid = '%s-%s' % (image.collection.private_token,pk)
    context = {
        'image': image,
        'user': image.collection.owner,
        'user_owns_image': user_owns_image,
        'api_cid':api_cid,
        'comparison_is_possible':comparison_is_possible
    }

    if isinstance(image, NIDMResultStatisticMap):
        context['img_basename'] = os.path.basename(image.file.url)
        context['ttl_basename'] = os.path.basename(image.nidm_results.ttl_file.url)
        context['provn_basename'] = os.path.basename(image.nidm_results.provn_file.url)

    if isinstance(image, Atlas):
        template = 'statmaps/atlas_details.html.haml'
    else:
        if image.not_mni:
            context['warning'] = "Warning: This map seems not to be in the MNI space (%.4g%% of meaningful voxels are outside of the brain). "%image.perc_voxels_outside
            context['warning'] += "Please transform the map to MNI space. "
        elif image.is_thresholded:
            context['warning'] = "Warning: This map seems to be thresholded, sparse or acquired with limited field of view (%.4g%% of voxels are zeros). "%image.perc_bad_voxels
            context['warning'] += "Some of the NeuroVault functions such as decoding might not work properly. "
            context['warning'] += "Please use unthresholded maps whenever possible."

        template = 'statmaps/statisticmap_details.html.haml'
    return render(request, template, context)


def view_collection(request, cid):
    collection = get_collection(cid,request)
    edit_permission = True if owner_or_contrib(request,collection) else False
    delete_permission = True if collection.owner == request.user else False
    images = collection.image_set.all()
    for image in images:
        if hasattr(image,'nidm_results'):
            image.zip_name = os.path.split(image.nidm_results.zip_file.path)[-1]
    context = {'collection': collection,
            'images': images,
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
    return redirect('my_collections')


@login_required
def edit_image(request, pk):
    image = get_object_or_404(Image,pk=pk)
    if isinstance(image, StatisticMap):
        form = EditStatisticMapForm
    elif isinstance(image, Atlas):
        form = EditAtlasForm
    elif isinstance(image, NIDMResultStatisticMap):
        form = EditNIDMResultStatisticMapForm
    else:
        raise Exception("unsuported image type")
    if not owner_or_contrib(request,image.collection):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = form(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = form(instance=image, user=request.user)

    context = {"form": form}
    return render(request, "statmaps/edit_image.html.haml", context)


def view_nidm_results(request, collection_cid, nidm_name):
    collection = get_collection(collection_cid,request)
    try:
        nidmr = NIDMResults.objects.get(collection=collection,name=nidm_name)
    except NIDMResults.DoesNotExist:
        return Http404("This NIDM Result was not found.")
    if request.method == "POST":
        if not owner_or_contrib(request,collection):
            return HttpResponseForbidden()
        form = NIDMResultsForm(request.POST, request.FILES, instance=nidmr)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            form.save_nidm()
            form.save_m2m()
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        if owner_or_contrib(request,collection):
            form = NIDMResultsForm(instance=nidmr)
        else:
            form = NIDMViewForm(instance=nidmr)

    context = {"form": form}
    return render(request, "statmaps/edit_nidm_results.html.haml", context)


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
                                     private=False,
                                     private_token=priv_token)
        temp_collection.save()
    image = StatisticMap(collection=temp_collection)
    if request.method == "POST":
        form = SimplifiedStatisticMapForm(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect("http://neurosynth.org/decode/?neurovault=%s-%s" % (
                temp_collection.private_token,image.id))
    else:
        form = SimplifiedStatisticMapForm(user=request.user, instance=image)

    context = {"form": form}
    return render(request, "statmaps/add_image_for_neurosynth.html.haml", context)


@login_required
def add_image(request, collection_cid):
    collection = get_collection(collection_cid,request)
    image = StatisticMap(collection=collection)
    if request.method == "POST":
        form = AddStatisticMapForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = AddStatisticMapForm(instance=image)

    context = {"form": form}
    return render(request, "statmaps/add_image.html.haml", context)


@login_required
def upload_folder(request, collection_cid):
    collection = get_collection(collection_cid,request)
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
                    if fnmatch(archive_name,'*.nidm.zip'):
                        populate_nidm_results(request,collection)
                        return HttpResponseRedirect(collection.get_absolute_url())

                    _, archive_ext = os.path.splitext(archive_name)
                    if archive_ext == '.zip':
                        compressed = zipfile.ZipFile(request.FILES['file'])
                    elif archive_ext == '.gz':
                        django_file = request.FILES['file']
                        django_file.open()
                        compressed = tarfile.TarFile(fileobj=gzip.GzipFile(fileobj=django_file.file, mode='r'), mode='r')
                    else:
                        raise Exception("Unsupported archive type %s."%archive_name)
                    compressed.extractall(path=tmp_directory)

                elif "file_input[]" in request.FILES:

                    for f, path in zip(request.FILES.getlist(
                                       "file_input[]"), request.POST.getlist("paths[]")):
                        if fnmatch(f.name,'*.nidm.zip'):
                            request.FILES['file'] = f
                            populate_nidm_results(request,collection)
                            continue

                        new_path, _ = os.path.split(os.path.join(tmp_directory, path))
                        mkdir_p(new_path)
                        filename = os.path.join(new_path,f.name)
                        tmp_file = open(filename, 'w')
                        tmp_file.write(f.read())
                        tmp_file.close()
                else:
                    raise Exception("Unable to find uploaded files.")

                atlases = {}
                for root, subdirs, filenames in os.walk(tmp_directory):
                    if detect_feat_directory(root):
                        populate_feat_directory(request,collection,root)
                        del(subdirs)
                        filenames = []

                    # .gfeat parent dir under cope*.feat should not be added as statmaps
                    # this may be affected by future nidm-results_fsl parsing changes
                    if root.endswith('.gfeat'):
                        filenames = []

                    filenames = [f for f in filenames if not f[0] == '.']
                    for fname in sorted(filenames):
                        name, ext = splitext_nii_gz(fname)
                        nii_path = os.path.join(root, fname)

                        if ext == '.xml':
                            print "found xml"
                            dom = minidom.parse(os.path.join(root, fname))
                            for atlas in dom.getElementsByTagName("summaryimagefile"):
                                print "found atlas"
                                path, base = os.path.split(atlas.lastChild.nodeValue)
                                nifti_name = os.path.join(path, base)
                                atlases[str(os.path.join(root,
                                            nifti_name[1:]))] = os.path.join(root, fname)
                        if ext in allowed_extensions:
                            nii = nib.load(nii_path)
                            if detect_afni4D(nii):
                                niftiFiles.extend(split_afni4D_to_3D(nii))
                            else:
                                niftiFiles.append((fname,nii_path))

                for label,fpath in niftiFiles:
                    # Read nifti file information
                    nii = nib.load(fpath)
                    if len(nii.get_shape()) > 3 and nii.get_shape()[3] > 1:
                        messages.warning(request, "Skipping %s - not a 3D file."%label)
                        continue
                    hdr = nii.get_header()
                    raw_hdr = hdr.structarr

                    # SPM only !!!
                    # Check if filename corresponds to a T-map
                    Tregexp = re.compile('spmT.*')
                    # Fregexp = re.compile('spmF.*')

                    if Tregexp.search(fpath) is not None:
                        map_type = StatisticMap.T
                    else:
                        # Check if filename corresponds to a F-map
                        if Tregexp.search(fpath) is not None:
                            map_type = StatisticMap.F
                        else:
                            map_type = StatisticMap.OTHER

                    path, name, ext = split_filename(fpath)
                    dname = name + ".nii.gz"
                    spaced_name = name.replace('_',' ').replace('-',' ')

                    if ext.lower() != ".nii.gz":
                        new_file_tmp_dir = tempfile.mkdtemp()
                        new_file_tmp = os.path.join(new_file_tmp_dir, name) + '.nii.gz'
                        nib.save(nii, new_file_tmp)
                        f = ContentFile(open(new_file_tmp).read(), name=dname)
                        shutil.rmtree(new_file_tmp_dir)
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

            except:
                raise
                error = traceback.format_exc().splitlines()[-1]
                msg = "An error occurred with this upload: {}".format(error)
                messages.warning(request, msg)
                return HttpResponseRedirect(collection.get_absolute_url())

            finally:
                shutil.rmtree(tmp_directory)
            if not niftiFiles:
                messages.warning(request, "No NIFTI files (.nii, .nii.gz, .img/.hdr) found in the upload.")
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        form = UploadFileForm()
    return render_to_response("statmaps/upload_folder.html",
                              {'form': form},  RequestContext(request))


@login_required
def delete_image(request, pk):
    image = get_object_or_404(Image,pk=pk)
    cid = image.collection.pk
    if not owner_or_contrib(request,image.collection):
        return HttpResponseForbidden()
    image.delete()
    return redirect('collection_details', cid=cid)



def view_images_by_tag(request, tag):
    if request.user.is_authenticated():
        images = Image.objects.filter(tags__name__in=[tag]).filter(
                                        Q(collection__private=False) |
                                        Q(collection__owner=request.user))
    else:
        images = Image.objects.filter(tags__name__in=[tag]).filter(
                                        collection__private=False)
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
    images = collection.image_set.all()

    if not images:
        return redirect(collection)
    else:

        basedir = os.path.join(settings.PRIVATE_MEDIA_ROOT,'images',str(collection.id))
        baseurl = os.path.join(settings.PRIVATE_MEDIA_URL,cid)

        output_dir = os.path.join(basedir, "pycortex_all")
        html_path = os.path.join(basedir, "pycortex_all/index.html")
        pycortex_url = os.path.join(baseurl, "pycortex_all/index.html")

        if os.path.exists(output_dir):
            # check if collection contents have changed
            if (not os.path.exists(html_path)) or collection.modify_date > get_file_ctime(html_path):
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
    return sendfile(request, path, encoding="utf-8")


def serve_pycortex(request, collection_cid, path, pycortex_dir='pycortex_all'):
    collection = get_collection(collection_cid,request,mode='file')
    int_path = os.path.join(settings.PRIVATE_MEDIA_ROOT,
                            'images',str(collection.id),pycortex_dir,path)
    return sendfile(request, int_path)


def serve_nidm(request, collection_cid, nidmdir, sep, path):
    collection = get_collection(collection_cid, request, mode='file')
    basepath = os.path.join(settings.PRIVATE_MEDIA_ROOT,'images')
    fpath = path if sep is '/' else ''.join([nidmdir,sep,path])
    try:
        nidmr = collection.nidmresults_set.get(name=nidmdir)
    except:
        return HttpResponseForbidden

    if path in ['zip','ttl','provn']:
        fieldf = getattr(nidmr,'{0}_file'.format(path))
        fpath = fieldf.path
    else:
        zipfile = nidmr.zip_file.path
        fpathbase = os.path.dirname(zipfile)
        fpath = ''.join([fpathbase,sep,path])

    return sendfile(request, os.path.join(basepath,fpath))


def serve_nidm_image(request, collection_cid, nidmdir, sep, path):
    collection = get_collection(collection_cid,request,mode='file')
    path = os.path.join(settings.PRIVATE_MEDIA_ROOT,'images',str(collection.id),nidmdir,path)
    return sendfile(request, path)


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
    collection = name=request.GET.get('collection','')
    neurovault_root = os.path.dirname(os.path.dirname(os.path.realpath(neurovault.__file__)))
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse('error: could not find collection: %s' % collection, status=400)
    try:
        atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
        atlas_image = atlas_object.file
        atlas_xml = atlas_object.label_description_file
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
                graph = joblib.load(input)
            for atlasRegion in atlasRegions:
                synonymsDict[atlasRegion] = getSynonyms(atlasRegion)
            try:
                searchList = toAtlas(search, graph, atlasRegions, synonymsDict)
            except ValueError:
                return JSONResponse('error: region not in atlas or ontology', status=400)
            if searchList == 'none':
                return JSONResponse('error: could not map specified region to region in specified atlas', status=400)
        try:
            data = {'voxels':getAtlasVoxels(searchList, atlas_image, atlas_xml)}
        except ValueError:
            return JSONResponse('error: region not in atlas', status=400)

        return JSONResponse(data)


@csrf_exempt
def atlas_query_voxel(request):
    X = request.GET.get('x','')
    Y = request.GET.get('y','')
    Z = request.GET.get('z','')
    collection = name = request.GET.get('collection','')
    atlas = request.GET.get('atlas','').replace('\'', '')
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse('error: could not find collection: %s' % collection, status=400)
    try:
        atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
        atlas_image = atlas_object.file
        atlas_xml = atlas_object.label_description_file
    except IndexError:
        return JSONResponse('error: could not find atlas: %s' % atlas, status=400)
    try:
        data = voxelToRegion(X,Y,Z,atlas_image, atlas_xml)
    except IndexError:
        return JSONResponse('error: one or more coordinates are out of range', status=400)
    return JSONResponse(data)


# Compare Two Images
def compare_images(request,pk1,pk2):
    import numpy as np
    image1 = get_image(pk1,None,request)
    image2 = get_image(pk2,None,request)
    images = [image1,image2]

    # Get image: collection: [map_type] names no longer than ~125 characters
    image1_custom_name = format_image_collection_names(image_name=image1.name,
                                                       collection_name=image1.collection.name,
                                                       map_type=image1.map_type,total_length=125)
    image2_custom_name = format_image_collection_names(image_name=image2.name,
                                                       collection_name=image2.collection.name,
                                                       map_type=image2.map_type,total_length=125)

    image_names = [image1_custom_name,image2_custom_name]

    # Create custom links for the visualization
    custom = {
            "IMAGE_1_LINK":"/images/%s" % (image1.pk),
            "IMAGE_2_LINK":"/images/%s" % (image2.pk)
    }

    # create reduced representation in case it's not there
    if not image1.reduced_representation:
        image1 = save_resampled_transformation_single(image1.id) # cannot run this async
    if not image2.reduced_representation:
        image2 = save_resampled_transformation_single(image1.id) # cannot run this async

    # Load image vectors from npy files
    image_vector1 = np.load(image1.reduced_representation.file)
    image_vector2 = np.load(image2.reduced_representation.file)

    # Load atlas pickle, containing vectors of atlas labels, colors, and values for same voxel dimension (4mm)
    this_path = os.path.abspath(os.path.dirname(__file__))
    atlas_pkl_path = os.path.join(this_path, 'static/atlas/atlas_mni_4mm.pkl')
    atlas = joblib.load(atlas_pkl_path)

    # Load the atlas svg, so we don't need to dynamically generate it
    atlas_svg = os.path.join(this_path, 'static/atlas/atlas_mni_2mm_svg.pkl')
    atlas_svg = joblib.load(atlas_svg)

    # Generate html for similarity search, do not specify atlas
    html_snippet, _ = scatterplot.scatterplot_compare_vector(image_vector1=image_vector1,
                                                                 image_vector2=image_vector2,
                                                                 image_names=image_names,
                                                                 atlas_vector=atlas["atlas_vector"],
                                                                 atlas_labels=atlas["atlas_labels"],
                                                                 atlas_colors=atlas["atlas_colors"],
                                                                 corr_type="pearson",
                                                                 subsample_every=10, # subsample every 10th voxel
                                                                 custom=custom,
                                                                 remove_scripts="D3_MIN_JS",
                                                                 width=1000)

    # Add atlas svg to the image, and prepare html for rendering
    html = [h.replace("[coronal]",atlas_svg) for h in html_snippet]
    html = [h.strip("\n").replace("[axial]","").replace("[sagittal]","") for h in html]
    context = {'html': html}

    # Determine if either image is thresholded
    threshold_status = np.array([image_names[i] for i in range(0,2) if images[i].is_thresholded])
    if len(threshold_status) > 0:
        warnings = list()
        for i in range(0,len(image_names)):
            warnings.append('Warning: Thresholded image: %s (%.4g%% of voxels are zeros),' %(image_names[i],images[i].perc_bad_voxels))
        context["warnings"] = warnings

    return render(request, 'statmaps/compare_images.html', context)


# Return search interface for one image vs rest
def find_similar(request,pk):
    image1 = get_image(pk,None,request)
    pk = int(pk)

    # Search only enabled if the image is not thresholded
    if image1.is_thresholded == False:

        # Count the number of comparisons that we have to determine max that we can return
        number_comparisons = count_existing_comparisons(pk)

        max_results = 100
        if number_comparisons < 100:
            max_results = number_comparisons

        # Get only # max_results similarity calculations for this image, and ids of other images
        comparisons = get_existing_comparisons(pk).extra(select={"abs_score": "abs(similarity_score)"}).order_by("-abs_score")[0:max_results] # "-" indicates descending

        images = [image1]
        scores = [1] # pearsonr
        for comp in comparisons:
            # pick the image we are comparing with
            image = [image for image in [comp.image1, comp.image2] if image.id != pk][0]
            if hasattr(image, "map_type") and image.thumbnail:
                images.append(image)
                scores.append(comp.similarity_score)

        # We will need lists of image ids, png paths, query id, query path, tags, names, scores
        image_ids = [image.pk for image in images]
        png_img_paths = [image.get_thumbnail_url() for image in images]
        tags = [[str(image.map_type)] for image in images]

        # The top text will be the collection name, the bottom text the image name
        bottom_text = ["%s" % (image.name) for image in images]
        top_text = ["%s" % (image.collection.name) for image in images]
        compare_url = "/images/compare"  # format will be prefix/[query_id]/[other_id]
        image_url = "/images"  # format will be prefix/[other_id]
        image_title = format_image_collection_names(image_name=image1.name,
                                                    collection_name=image1.collection.name,
                                                    map_type=image1.map_type,total_length=50)

        # Here is the query image
        query_png = image1.thumbnail.url

        # Do similarity search and return html to put in page, specify 100 max results, take absolute value of scores
        html_snippet = search.similarity_search(image_scores=scores,tags=tags,png_paths=png_img_paths,
                                    button_url=compare_url,image_url=image_url,query_png=query_png,
                                    query_id=pk,top_text=top_text,image_ids=image_ids,
                                    bottom_text=bottom_text,max_results=max_results,absolute_value=True,
                                    remove_scripts=["BOOTSTRAP","BOOTSTRAP_MIN"],container_width=1200)

        html = [h.strip("\n") for h in html_snippet]

        # Get the number of images still processing
        images_processing = count_processing_comparisons(pk)

        context = {'html': html,'images_processing':images_processing,
                   'image_title':image_title, 'image_url': '/images/%s' % (image1.pk) }
        return render(request, 'statmaps/compare_search.html', context)
    else:
        error_message = "Image comparison is not enabled for thresholded images."
        context = {'error_message': error_message}
        return render(request, 'statmaps/error_message.html', context)


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)
