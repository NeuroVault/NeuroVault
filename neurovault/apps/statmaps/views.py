import csv
import functools
import json
import shutil
import numpy as np
import os
import re
import shutil
import tempfile
import traceback
import urllib.request, urllib.parse, urllib.error
import zipstream
from collections import OrderedDict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models import Q
from django.db.models.aggregates import Count
from django.http import Http404, HttpResponse, StreamingHttpResponse, JsonResponse
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.encoding import filepath_to_uri
from django.views.decorators.csrf import csrf_exempt
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.urls import reverse
from fnmatch import fnmatch
from guardian.shortcuts import get_objects_for_user

# from nidmviewer.viewer import generate
# from pybraincompare.compare.scatterplot import scatterplot_compare_vector
from nidmresults.graph import Graph
from rest_framework.renderers import JSONRenderer
from sendfile import sendfile
import joblib

from neurovault.apps.statmaps.models import get_possible_templates, DEFAULT_TEMPLATE

import neurovault
from neurovault import settings
from neurovault.apps.statmaps.ahba import calculate_gene_expression_similarity
from neurovault.apps.statmaps.forms import (
    CollectionForm,
    UploadFileForm,
    SimplifiedStatisticMapForm,
    NeuropowerStatisticMapForm,
    EditStatisticMapForm,
    OwnerCollectionForm,
    EditAtlasForm,
    EditNIDMResultStatisticMapForm,
    MetaanalysisForm,
)
from neurovault.apps.statmaps.models import (
    Collection,
    Image,
    Atlas,
    StatisticMap,
    NIDMResults,
    NIDMResultStatisticMap,
    CognitiveAtlasTask,
    CognitiveAtlasContrast,
    BaseStatisticMap,
    DEFAULT_TEMPLATE,
    Metaanalysis,
)
from neurovault.apps.statmaps.tasks import save_resampled_transformation_single
from neurovault.apps.statmaps.utils import (
    split_filename,
    generate_pycortex_volume,
    generate_pycortex_static,
    generate_url_token,
    HttpRedirectException,
    get_paper_properties,
    get_file_ctime,
    send_email_notification,
    populate_nidm_results,
    get_server_url,
    format_image_collection_names,
    is_search_compatible,
    get_similar_images,
    extract_archive,
    collect_nifti_files,
    extract_multiple_files,
    create_image_from_nifti,
    write_file_to_disk
)
from neurovault.apps.statmaps.utils import (
    is_target_template_image_pycortex_compatible,
    is_target_template_image_neurosynth_compatible,
)
from neurovault.apps.statmaps.meta import (
    load_default_mask,
    create_collection_for_metaanalysis,
    gather_images_and_sizes,
    set_collection_description,
    run_meta_analysis,
    create_and_save_statmaps,
)
from neurovault.apps.statmaps.voxel_query_functions import *
from . import image_metadata



def owner_or_contrib(request, collection):
    """owner_or_contrib determines if user is an owner or contributor to a collection
    :param collection: statmaps.models.Collection
    """
    return (
        request.user.has_perm("statmaps.change_collection", collection)
        or request.user.is_superuser
    )


def get_button_html(url, type, target_template_image):
    return (
        '<a role="button" class="btn btn-outline-secondary btn-sm viewimage" '
        'onclick="viewimage(this)" filename="%s" type="%s" '
        'target_template_image="%s"><i class="fa fa-lg '
        'fa-eye"></i></a>' % (url, type, target_template_image)
    )


def get_collection(cid, request, mode=None):
    """get_collection returns collection object based on a primary key (cid)
    :param cid: statmaps.models.Collection.pk the primary key of the collection
    """
    keyargs = {"pk": cid}
    private_url = re.match(r"^[A-Z]{8}$", cid)
    if private_url is not None:
        keyargs = {"private_token": cid}
    try:
        collection = Collection.objects.get(**keyargs)

        if private_url is None and collection.private:
            if owner_or_contrib(request, collection):
                if mode in ["file", "api"]:
                    raise PermissionDenied()
                else:
                    raise HttpRedirectException(collection.get_absolute_url())
            else:
                raise PermissionDenied()
    except Collection.DoesNotExist:
        raise Http404
    else:
        return collection


def get_image(pk, collection_cid, request, mode=None):
    """get_image returns image object from a collection based on a primary key (pk)
    :param pk: statmaps.models.Image.pk the primary key of the image
    :param collection_cid: the primary key of the image collection
    """
    image = get_object_or_404(Image, pk=pk)
    if image.collection.private and image.collection.private_token != collection_cid:
        if owner_or_contrib(request, image.collection):
            if mode == "api":
                raise PermissionDenied()
            else:
                raise HttpRedirectException(image.get_absolute_url())
        else:
            raise PermissionDenied()
    else:
        return image


@login_required
def edit_metaanalysis(request, metaanalysis_id=None):
    """edit_collection is a view to edit a collection, meaning showing the edit form for an existing collection, creating a new collection, or passing POST data to update an existing collection
    :param cid: statmaps.models.Collection.pk the primary key of the collection. If none, will generate form to make a new collection.
    """
    page_header = "Start a new metaanalysis"
    if metaanalysis_id:
        metaanalysis = Metaanalysis.objects.get(pk=metaanalysis_id)
        page_header = "Edit metaanalysis"
        if request.user != metaanalysis.owner:
            return HttpResponseForbidden()
    else:
        metaanalysis = Metaanalysis(owner=request.user)
    if request.method == "POST":
        form = MetaanalysisForm(request.POST, request.FILES, instance=metaanalysis)
        if form.is_valid():
            metaanalysis.save()
            return HttpResponseRedirect(metaanalysis.get_absolute_url())
    else:
        form = MetaanalysisForm(instance=metaanalysis)

    context = {"form": form, "page_header": page_header}
    return render(request, "statmaps/edit_metaanalysis.html", context)

@login_required
def finalize_metaanalysis(request, metaanalysis_id):
    metaanalysis = get_object_or_404(Metaanalysis, pk=metaanalysis_id)

    # 1. Check permissions and status
    if request.user != metaanalysis.owner or metaanalysis.status == "completed":
        return HttpResponseForbidden()

    # 2. Create a new collection
    new_collection = create_collection_for_metaanalysis(metaanalysis)

    # 3. Load default mask
    #    (Use your actual get_possible_templates function to pass to the helper)
    mask_img = load_default_mask(get_possible_templates, DEFAULT_TEMPLATE)

    # 4. Gather Z images (and T->Z conversions) + sizes
    z_imgs, sizes = gather_images_and_sizes(metaanalysis, mask_img)

    # 5. Determine if weighted is possible (if sizes match #images)
    #    Then update new_collection description
    do_weighted = (len(sizes) == len(z_imgs)) and len(z_imgs) > 0
    set_collection_description(new_collection, z_imgs, do_weighted)

    # 6. Run meta-analysis
    result, actually_weighted = run_meta_analysis(z_imgs, sizes, mask_img)

    # 7. Create & save StatisticMap objects (Z/P/FFX)
    tmp_dir = tempfile.mkdtemp()
    try:
        create_and_save_statmaps(result, actually_weighted, new_collection, tmp_dir)
    finally:
        shutil.rmtree(tmp_dir)

    # 8. Finalize meta-analysis status
    metaanalysis.output_maps = new_collection
    metaanalysis.status = "completed"
    metaanalysis.save()

    return HttpResponseRedirect(new_collection.get_absolute_url())

@login_required
def toggle_active_metaanalysis(request, pk, collection_cid=None):
    image = get_image(pk, collection_cid, request)
    metaanalysis = Metaanalysis.objects.filter(owner=request.user).filter(
        status="active"
    )[0]
    if request.user != metaanalysis.owner:
        return HttpResponseForbidden()
    if metaanalysis in image.metaanalysis_set.all():
        metaanalysis.maps.remove(image)
        new_status = "out"
    else:
        metaanalysis.maps.add(image)
        new_status = "in"
    return JSONResponse({"new_status": new_status})


@login_required
def activate_metaanalysis(request, metaanalysis_id):
    metaanalysis = Metaanalysis.objects.get(pk=metaanalysis_id)
    if request.user != metaanalysis.owner or metaanalysis.status == "completed":
        return HttpResponseForbidden()
    metaanalysis.status = "active"
    metaanalysis.save()
    return HttpResponseRedirect(metaanalysis.get_absolute_url())


@login_required
def edit_collection(request, cid=None):
    """edit_collection is a view to edit a collection, meaning showing the edit form for an existing collection, creating a new collection, or passing POST data to update an existing collection
    :param cid: statmaps.models.Collection.pk the primary key of the collection. If none, will generate form to make a new collection.
    """
    page_header = "Add new collection"
    if cid:
        collection = get_collection(cid, request)
        edit_permission = request.user.has_perm(
            "statmaps.change_collection", collection
        )
        is_owner = request.user.has_perm("statmaps.delete_collection", collection)
        page_header = "Edit collection"
        if not edit_permission:
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
                    "owner": collection.owner.username,
                    "collection": collection.name,
                    "url": get_server_url(request) + collection.get_absolute_url(),
                }
                subj = "%s has added you to a NeuroVault collection" % context["owner"]
                send_email_notification("new_contributor", subj, new_contribs, context)

            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        if is_owner:
            form = OwnerCollectionForm(instance=collection)
        else:
            form = CollectionForm(instance=collection)

    context = {"form": form, "page_header": page_header, "is_owner": is_owner}
    return render(request, "statmaps/edit_collection.html", context)


def choice_datasources(model):
    statmap_field_obj = functools.partial(image_metadata.get_field_by_name, model)
    pick_second_item = functools.partial(map, lambda x: x[1])
    fixed_fields = list(model.get_fixed_fields())
    field_choices = ((f, statmap_field_obj(f).choices) for f in fixed_fields)
    fields_with_choices = (t for t in field_choices if t[1])
    return dict(
        (field_name, list(pick_second_item(choices)))
        for field_name, choices in fields_with_choices
    )


def get_field_datasources():
    ds = choice_datasources(StatisticMap)
    ds["cognitive_paradigm_cogatlas"] = [
        x.name for x in (CognitiveAtlasTask.objects.all())
    ]
    return ds


def get_contrast_lookup():
    """get_contrast_lookup returns a dictionary with keys being cognitive atlas task primary keys, and keys a list of contrasts, each a dictionary with keys "name" and "value" """
    contrasts = dict()
    for task in CognitiveAtlasTask.objects.all():
        task_contrasts = CognitiveAtlasContrast.objects.filter(task=task)
        contrasts[task.pk] = [
            {"name": contrast.name, "value": contrast.pk} for contrast in task_contrasts
        ]
    return contrasts


@csrf_exempt
@login_required
def edit_metadata(request, collection_cid):
    collection = get_collection(collection_cid, request)

    if not owner_or_contrib(request, collection):
        return HttpResponseForbidden()

    if not collection.is_statisticmap_set:
        return HttpResponseForbidden(
            "Editing image metadata of collections "
            "that include not only statistical "
            "maps is forbidden."
        )

    if request.method == "POST":
        return JSONResponse(
            **image_metadata.handle_post_metadata(
                request, collection, "Images metadata have been saved."
            )
        )

    collection_images = collection.basecollectionitem_set.instance_of(Image).order_by(
        "pk"
    )
    data_headers = image_metadata.get_data_headers(collection_images)
    metadata = image_metadata.get_images_metadata(collection_images)
    datasources = get_field_datasources()

    return render(
        request,
        "statmaps/edit_metadata.html",
        {
            "collection": collection,
            "datasources": json.dumps(datasources),
            "data_headers": json.dumps(data_headers),
            "metadata": json.dumps(metadata),
        },
    )


@login_required
def export_images_filenames(request, collection_cid):
    collection = get_collection(collection_cid, request)
    images_filenames = image_metadata.get_images_filenames(collection)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; " 'filename="collection_%s.csv"' % (
        collection.id
    )

    writer = csv.writer(response)
    writer.writerows([["Filename"]] + [[name] for name in images_filenames])

    return response


def add_communities_context(communities, context):
    if len(communities) == 1:
        main_community = communities[0]
        context["name_subscript"] = main_community.label
        context["name_subscript_url"] = reverse(
            "statmaps:view_community", kwargs={"community_label": main_community.label}
        )


def view_image(request, pk, collection_cid=None):
    """view_image returns main view to see an image and associated meta data. If the image is in a collection with a DOI and has a generated thumbnail, it is a contender for image comparison, and a find similar button is exposed.
    :param pk: statmaps.models.Image.pk the primary key of the image
    :param collection_cid: statmaps.models.Collection.pk the primary key of the collection. Default None
    """
    image = get_image(pk, collection_cid, request)
    user_owns_image = owner_or_contrib(request, image.collection)
    api_cid = pk

    # if no template is specified use MNI152
    if not image.target_template_image:
        image.target_template_image = DEFAULT_TEMPLATE

    comparison_is_possible = is_search_compatible(pk) and image.thumbnail
    pycortex_compatible = is_target_template_image_pycortex_compatible(
        image.target_template_image
    )
    neurosynth_compatible = is_target_template_image_neurosynth_compatible(
        image.target_template_image
    )

    is_there_an_active_metaanalysis = request.user.is_authenticated and (
        Metaanalysis.objects.filter(owner=request.user).filter(status="active").count()
        != 0
    )
    is_metaanalysis_compatible = (
        isinstance(image, StatisticMap)
        and image.analysis_level == "G"
        and image.map_type in ["T", "Z"]
    )
    show_metaanalysis_button = (
        is_there_an_active_metaanalysis and is_metaanalysis_compatible
    )

    if not show_metaanalysis_button:
        meta_status = "invalid"
    else:
        metaanalysis = Metaanalysis.objects.filter(owner=request.user).filter(
            status="active"
        )[0]
        if metaanalysis in image.metaanalysis_set.all():
            meta_status = "in"
        else:
            meta_status = "out"

    if image.collection.private:
        api_cid = "%s-%s" % (image.collection.private_token, pk)
    context = {
        "image": image,
        "user": image.collection.owner,
        "user_owns_image": user_owns_image,
        "api_cid": api_cid,
        "neurosynth_compatible": neurosynth_compatible,
        "pycortex_compatible": pycortex_compatible,
        "comparison_is_possible": comparison_is_possible,
        "show_metaanalysis_button": show_metaanalysis_button,
        "meta_status": meta_status,
    }

    communities = image.collection.communities.all()
    add_communities_context(communities, context)

    if isinstance(image, NIDMResultStatisticMap):
        context["img_basename"] = os.path.basename(image.file.url)
        context["ttl_basename"] = os.path.basename(image.nidm_results.ttl_file.url)

    if isinstance(image, Atlas):
        template = "statmaps/atlas_details.html"
    else:
        if np.isnan(image.perc_bad_voxels) or np.isnan(image.perc_voxels_outside):
            context["warning"] = "Warning: This map seems to be empty!"
        elif not image.is_valid:
            context["warning"] = "Warning: This map is missing some mandatory metadata!"
            if user_owns_image:
                context[
                    "warning"
                ] += " Please <a href='edit'>edit image details</a> to provide the missing information."
        elif image.not_mni:
            context["warning"] = (
                "Warning: This map seems not to be in the MNI space (%.4g%% of meaningful voxels are outside of the brain). "
                % image.perc_voxels_outside
            )
            context["warning"] += "Please transform the map to MNI space. "
        elif image.is_thresholded:
            context["warning"] = (
                "Warning: This map seems to be thresholded, sparse or acquired with limited field of view (%.4g%% of voxels are zeros). "
                % image.perc_bad_voxels
            )
            context[
                "warning"
            ] += "Some of the NeuroVault functions such as decoding might not work properly. "
            context["warning"] += "Please use unthresholded maps whenever possible."

        template = "statmaps/statisticmap_details.html"
    return render(request, template, context)


def view_metaanalysis(request, metaanalysis_id):
    """view_collection returns main view to see an entire collection of images, meaning a viewer and list of images to load into it.
    :param cid: statmaps.models.Collection.pk the primary key of the collection
    """
    metaanalysis = get_object_or_404(Metaanalysis, pk=metaanalysis_id)
    context = {"metaanalysis": metaanalysis}
    return render(request, "statmaps/metaanalysis_details.html", context)


def view_collection(request, cid):
    """view_collection returns main view to see an entire collection of images, meaning a viewer and list of images to load into it.
    :param cid: statmaps.models.Collection.pk the primary key of the collection
    """
    collection = get_collection(cid, request)
    edit_permission = request.user.has_perm("statmaps.change_collection", collection)
    delete_permission = request.user.has_perm("statmaps.delete_collection", collection)
    is_empty = not collection.basecollectionitem_set.exists()
    pycortex_compatible = all(
        [
            is_target_template_image_pycortex_compatible(image.target_template_image)
            for image in collection.basecollectionitem_set.instance_of(Image)
        ]
    )

    context = {
        "collection": collection,
        "is_empty": is_empty,
        "user": request.user,
        "delete_permission": delete_permission,
        "edit_permission": edit_permission,
        "pycortex_compatible": pycortex_compatible,
        "cid": cid,
    }

    for i in ["gimages_visible", "simages_visible", "oimages_visible", "images_visible", 
              "gimages_active", "simages_active", "oimages_active"]:
        context[i] = False

    context["oimages_title"] = "Other"
    if collection.basecollectionitem_set.not_instance_of(StatisticMap).count() > 0:
        context["images_visible"] = True
    else:
        context["images_visible"] = False
        if (
            StatisticMap.objects.filter(collection=collection)
            .filter(analysis_level="G")
            .count()
            > 0
        ):
            context["gimages_visible"] = True
            context["gimages_active"] = True

        if (
            StatisticMap.objects.filter(collection=collection)
            .filter(analysis_level="S")
            .count()
            > 0
        ):
            context["simages_visible"] = True
            if not context["gimages_visible"]:
                context["simages_active"] = True

        if (
            StatisticMap.objects.filter(collection=collection)
            .filter(~Q(analysis_level__in=["G", "S"]))
            .count()
            > 0
        ):
            context["oimages_visible"] = True
            if not (context["gimages_visible"] or context["simages_visible"]):
                context["oimages_active"] = True
                context["oimages_title"] = "Images"

    communities = collection.communities.all()
    add_communities_context(communities, context)

    if not all(
        collection.basecollectionitem_set.instance_of(StatisticMap).values_list(
            "is_valid", flat=True
        )
    ):
        msg = "Some of the images in this collection are missing crucial metadata."
        if owner_or_contrib(request, collection):
            msg += " Please add the missing information by <a href='editmetadata'>editing images metadata</a>."
        context["messages"] = [msg]

    if not is_empty:
        context["first_image"] = collection.basecollectionitem_set.order_by("pk")[0]

    if owner_or_contrib(request, collection):
        form = UploadFileForm()
        context["form"] = UploadFileForm()
    return render(request, "statmaps/collection_details.html", context)


@login_required
def delete_collection(request, cid):
    collection = get_collection(cid, request)
    if not request.user.has_perm("statmaps.delete_collection", collection):
        return HttpResponseForbidden()
    collection.delete()
    return redirect("statmaps:my_collections")


def get_sibling_images(current_image):
    collection_images = current_image.collection.basecollectionitem_set.instance_of(
        Image
    )
    image_ids = sorted(list(collection_images.values_list("id", flat=True)))
    current_index = image_ids.index(current_image.id)

    prev_id = image_ids[current_index - 1] if current_index > 0 else None
    next_id = image_ids[current_index + 1] if current_index < len(image_ids) - 1 else None

    prev_image = collection_images.filter(pk=prev_id).first() if prev_id else None
    next_image = collection_images.filter(pk=next_id).first() if next_id else None
    return (prev_image, next_image)

@login_required
def edit_image(request, pk):
    image = get_object_or_404(Image, pk=pk)

    first_time_param = request.GET.get("first", "false").lower()
    first = (first_time_param == "true")

    min_image_id = request.GET.get("min_image", False)

    try:
        min_image_id = int(min_image_id)
    except ValueError:
        min_image_id = None

    max_image_id = request.GET.get("max_image", False)

    try:
        max_image_id = int(max_image_id)
    except ValueError:
        max_image_id = None

    collection_images = image.collection.basecollectionitem_set.instance_of(
        Image
    )

    passalong = f"?first={first_time_param}&min_image={min_image_id}&max_image={max_image_id}"
    kwargs = {}
    if isinstance(image, StatisticMap):
        form = EditStatisticMapForm
        image.name = ''
        kwargs = {
            'first': first,
            'min_image': min_image_id,
            'max_image': max_image_id
        }
    elif isinstance(image, Atlas):
        form = EditAtlasForm
    elif isinstance(image, NIDMResultStatisticMap):
        form = EditNIDMResultStatisticMapForm
    else:
        raise Exception("unsupported image type")
    if not owner_or_contrib(request, image.collection):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = form(
            request.POST, request.FILES, instance=image, user=request.user,
            **kwargs)
        print(request.POST)
        if form.is_valid():
            form.save()
            if "submit_previous" in request.POST:
                prev_img, _ = get_sibling_images(image)
                if prev_img:
                    return HttpResponseRedirect(prev_img.get_absolute_url(edit=True) + passalong)
            elif "submit_next" in request.POST:
                _, next_img = get_sibling_images(image)
                if next_img:
                    return HttpResponseRedirect(next_img.get_absolute_url(edit=True) + passalong)
            elif "submit_save" in request.POST:
                return HttpResponseRedirect(image.get_absolute_url())
            
    else:
        form = form(instance=image, user=request.user, **kwargs)


    # Serialize collection images
    serialized_images = []
    for img in collection_images:
        modify_date = img.modify_date.strftime('%Y-%m-%d %H:%M:%S') if img.modify_date != img.add_date else None
        serialized_images.append({
            "id": img.id,
            "name": img.name,
            "description": img.description,
            "last_edited": modify_date,
            "is_valid": img.is_valid,
            "analysis_level": (img.analysis_level if isinstance(img, StatisticMap) else None) or "",
            "modality": (img.modality if isinstance(img, StatisticMap) else None) or "",
        })
    contrasts = get_contrast_lookup()
    context = {
        "form": form, "contrasts": json.dumps(contrasts),
        "collection_images": serialized_images,
    }
    return render(request, "statmaps/edit_image.html", context)


def view_nidm_results(request, collection_cid, nidm_name):
    raise Http404("Disabled for upgrade")


@login_required
def delete_nidm_results(request, collection_cid, nidm_name):
    collection = get_collection(collection_cid, request)
    nidmr = get_object_or_404(NIDMResults, collection=collection, name=nidm_name)

    if request.user.has_perm("statmaps.delete_basecollectionitem", nidmr):
        nidmr.delete()
        return redirect("statmaps:collection_details", cid=collection_cid)
    else:
        return HttpResponseForbidden()


def view_task(request, cog_atlas_id=None):
    """view_task returns a view to see a group of images associated with a particular cognitive atlas task.
    :param cog_atlas_id: statmaps.models.CognitiveAtlasTask the id for the task defined in the Cognitive Atlas
    """
    from .cogat_functions import get_task_graph

    # Get the cognitive atlas id
    if not cog_atlas_id:
        return search(
            request,
            error_message="Please search for a Cognitive Atlas task to see the task view.",
        )

    try:
        task = CognitiveAtlasTask.objects.get(cog_atlas_id=cog_atlas_id)
    except ObjectDoesNotExist:
        return search(request, error_message="Invalid search for Cognitive Atlas.")

    if task:
        images = StatisticMap.objects.filter(
            cognitive_paradigm_cogatlas=cog_atlas_id, collection__private=False
        ).order_by("pk")

        if len(images) > 0:
            first_image = images[0]
            graph = get_task_graph(cog_atlas_id, images=images)

            # Which images aren't tagged with contrasts?
            not_tagged = images.filter(cognitive_contrast_cogatlas__isnull=True)

            context = {
                "task": task,
                "first_image": first_image,
                "cognitive_atlas_tree": graph,
                "tree_divid": "tree",  # div id in template to append tree svg to
                "images_without_contrasts": not_tagged,
            }

            return render(request, "cogatlas/cognitive_atlas_task.html", context)

    # If task does not have images
    context = {
        "no_task_images": True,  # robots won't index page if defined
        "task": task,
    }
    return render(request, "cogatlas/cognitive_atlas_task.html", context)


def add_image_redirect(request, formclass, redirect_url, is_private, preamble):
    temp_collection_name = "%s's temporary collection" % request.user.username
    # this is a hack we need to make sure this collection can be only
    # owned by the same user
    try:
        temp_collection = Collection.objects.get(name=temp_collection_name)
    except Collection.DoesNotExist:
        priv_token = generate_url_token()
        temp_collection = Collection(
            name=temp_collection_name,
            owner=request.user,
            private=is_private,
            private_token=priv_token,
        )
        temp_collection.save()
    image = StatisticMap(collection=temp_collection)
    if request.method == "POST":
        form = formclass(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            image = form.save()
            redirect = redirect_url % {
                "private_token": temp_collection.private_token,
                "image_id": image.id,
            }
            return HttpResponseRedirect(redirect)
    else:
        form = formclass(user=request.user, instance=image)
    contrasts = get_contrast_lookup()
    context = {"form": form, "contrasts": json.dumps(contrasts), "preamble": preamble}
    return render(request, "statmaps/edit_image.html", context)


@login_required
def add_image_for_neurosynth(request):
    redirect_url = (
        "http://neurosynth.org/decode/?neurovault=%(private_token)s-%(image_id)s"
    )
    preamble = """Welcome to NeuroVault - a  public web repository for statistical 
maps of the brain. After filling in the minimum
information outlined below (only the fields with an 
asterisk [*] are compulsory), your map 
will be sent back to <a href="http://neurosynth.org">Neurosynth.org</a> for
decoding. <b>Remember that your map needs to be unthresholded and in MNI152
space for decoding to work correctly!</b>.
<b>By uploading your map you agree to make it publicly available under <a href="http://creativecommons.org/about/cc0">CC0 license</a>.</b>
You can always come back to <a href="/">NeuroVault.org</a> to 
inspect, modify, and/or delete your maps. If you wish to use Neurosynth decoding, but keep 
your maps private, consider creating a private collection."""

    return add_image_redirect(
        request, SimplifiedStatisticMapForm, redirect_url, False, preamble
    )


@login_required
def add_image_for_neuropower(request):
    redirect_url = "http://neuropowertools.org/neuropower/neuropowerinput/?neurovault=%(private_token)s-%(image_id)s"
    preamble = """Welcome to NeuroVault - a  public web repository for statistical
maps of the brain. After filling in the minimum
information outlined below (only the fields with an
asterisk [*] are compulsory), your map
will be sent back to <a href="http://neuropowertools.org">Neuropowertools.org</a> for
a power analysis. Your (pilot or preliminary) data will not be public, but we strongly encourage you to upload your full dataset after collection to Neurovault and make it public.
You can always come back to <a href="/">NeuroVault.org</a> to
inspect, modify, and/or delete your maps."""
    return add_image_redirect(
        request, NeuropowerStatisticMapForm, redirect_url, True, preamble
    )


@login_required
def upload_folder(request, collection_cid):
    collection = get_collection(collection_cid, request)
    allowed_extensions = [".nii", ".img", ".nii.gz"]
    images_added = []    
    if request.method == "POST":
        folder = False
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            with tempfile.TemporaryDirectory() as tmp_directory:
                try:
                    # 1. Check if "file" is an archive or NIDM
                    if "file" in request.FILES:
                        uploaded_file = request.FILES["file"]
                        if fnmatch(uploaded_file.name, "*.nidm.zip"):
                            new_form = populate_nidm_results(request, collection)
                            if not new_form:
                                messages.warning(request, "Invalid NIDM-Results file.")
                            return HttpResponseRedirect(collection.get_absolute_url())
                        
                        elif fnmatch(uploaded_file.name, "*.zip") or fnmatch(uploaded_file.name, "*.tar.gz"):
                            extract_archive(uploaded_file, tmp_directory)
                        else:
                            write_file_to_disk(uploaded_file, tmp_directory)

                    # 2. Or check if multiple files have been uploaded
                    elif "file_input[]" in request.FILES:
                        folder = True
                        file_list = request.FILES.getlist("file_input[]")
                        path_list = request.POST.getlist("paths[]")
                        extract_multiple_files(file_list, path_list, tmp_directory)
                        print("Com")
                    else:
                        raise ValueError("No uploaded files found.")


                    # 3. Collect NIfTI files and atlas xml info
                    nifti_files, atlases = collect_nifti_files(tmp_directory, allowed_extensions)

                    # 4. Create model objects for each NIfTI
                    if not nifti_files:
                        messages.warning(
                            request,
                            "No NIFTI files (.nii, .nii.gz, .img/.hdr) found in the upload."
                        )
                    else:
                        for label, fpath in nifti_files:
                            # If file is in an atlas map, pass the xml path
                            # (note: we need to handle possible path differences)
                            path, name_ext = os.path.split(fpath)
                            name_no_ext, _ = os.path.splitext(name_ext)
                            atlas_xml = None

                            # For matching, you might need to store the 
                            # *relative path* to match exactly. This will depend on how 
                            # parse_atlas_xml() builds its keys.
                            possible_key = os.path.join(path, name_no_ext)
                            if possible_key in atlases:
                                atlas_xml = atlases[possible_key]

                            try:
                                new_image = create_image_from_nifti(
                                    collection,
                                    label,
                                    fpath,
                                    atlas_xml_path=atlas_xml
                                )
                                images_added.append(new_image)
                            except Exception as e:
                                messages.warning(request, f"Skipping {label}: {str(e)}")

                except Exception:
                    error = traceback.format_exc().splitlines()[-1]
                    messages.warning(request, f"An error occurred with this upload: {error}")
                    return HttpResponseRedirect(collection.get_absolute_url())

            # If we added images, redirect to the edit page for the first one
            if images_added:
                min_image = images_added[0].id
                max_image = images_added[-1].id
                redirect = f"{images_added[0].get_absolute_url(edit=True)}?first=true&min_image={min_image}&max_image={max_image}"
                if folder:
                    return JsonResponse(
                        {"redirect_url": redirect}
                    )
                else:
                    return HttpResponseRedirect(redirect)
            else:
                return HttpResponseRedirect(
                    collection.get_absolute_url()
                )

    else:
        # GET request do nothing
        return HttpResponseRedirect(collection.get_absolute_url())

@login_required
def delete_image(request, pk):
    image = get_object_or_404(Image, pk=pk)
    cid = image.collection.pk
    if not request.user.has_perm("statmaps.delete_basecollectionitem", image):
        return HttpResponseForbidden()
    image.delete()
    return redirect("collection_details", cid=cid)


def view_images_by_tag(request, tag):
    if request.user.is_authenticated:
        images = Image.objects.filter(tags__name__in=[tag]).filter(
            Q(collection__private=False) | Q(collection__owner=request.user)
        )
    else:
        images = Image.objects.filter(tags__name__in=[tag]).filter(
            collection__private=False
        )
    context = {"images": images, "tag": tag}
    return render(request, "statmaps/images_by_tag.html", context)


def view_image_with_pycortex(request, pk, collection_cid=None):
    image = get_image(pk, collection_cid, request)
    base, fname, _ = split_filename(image.file.path)
    pycortex_dir = os.path.join(base, fname + "_pycortex")

    if not os.path.exists(pycortex_dir):
        volume = generate_pycortex_volume(image)
        generate_pycortex_static({image.name: volume}, pycortex_dir)

    _, _, ext = split_filename(image.file.url)
    pycortex_url = image.file.url[: -len(ext)] + "_pycortex/index.html"
    return redirect(pycortex_url)


def view_collection_with_pycortex(request, cid):
    volumes = {}
    collection = get_collection(cid, request, mode="file")
    images = collection.basecollectionitem_set.instance_of(Image)

    if not images:
        return redirect(collection)

    else:
        basedir = os.path.join(
            settings.PRIVATE_MEDIA_ROOT, "images", str(collection.id)
        )
        baseurl = os.path.join(settings.PRIVATE_MEDIA_URL, cid)

        output_dir = os.path.join(basedir, "pycortex_all")
        html_path = os.path.join(basedir, "pycortex_all/index.html")
        pycortex_url = os.path.join(baseurl, "pycortex_all/index.html")

        if os.path.exists(output_dir):
            # check if collection contents have changed
            if (
                not os.path.exists(html_path)
            ) or collection.modify_date > get_file_ctime(html_path):
                shutil.rmtree(output_dir)
                return view_collection_with_pycortex(request, cid)
        else:
            for image in images:
                vol = generate_pycortex_volume(image)
                volumes[image.name] = vol
            generate_pycortex_static(volumes, output_dir, title=collection.name)

        return redirect(pycortex_url)


def serve_image(request, collection_cid, img_name):
    collection = get_collection(collection_cid, request, mode="file")
    path = os.path.join(
        settings.PRIVATE_MEDIA_ROOT, "images", str(collection.id), img_name
    )
    return sendfile(request, path, encoding="utf-8")


def serve_pycortex(request, collection_cid, path, pycortex_dir="pycortex_all"):
    collection = get_collection(collection_cid, request, mode="file")
    int_path = os.path.join(
        settings.PRIVATE_MEDIA_ROOT, "images", str(collection.id), pycortex_dir, path
    )
    return sendfile(request, int_path)


def serve_nidm(request, collection_cid, nidmdir, sep, path):
    collection = get_collection(collection_cid, request, mode="file")
    basepath = os.path.join(settings.PRIVATE_MEDIA_ROOT, "images")
    fpath = path if sep == "/" else "".join([nidmdir, sep, path])
    try:
        nidmr = collection.basecollectionitem_set.instance_of(NIDMResults).get(
            name=nidmdir
        )
    except ObjectDoesNotExist:
        return HttpResponseForbidden()

    if path in ["zip", "ttl"]:
        fieldf = getattr(nidmr, "{0}_file".format(path))
        fpath = fieldf.path
    else:
        zipfile = nidmr.zip_file.path
        fpathbase = os.path.dirname(zipfile)
        fpath = "".join([fpathbase, sep, path])

    return sendfile(request, os.path.join(basepath, fpath), encoding="utf-8")


def serve_nidm_image(request, collection_cid, nidmdir, sep, path):
    collection = get_collection(collection_cid, request, mode="file")
    path = os.path.join(
        settings.PRIVATE_MEDIA_ROOT, "images", str(collection.id), nidmdir, path
    )
    return sendfile(request, path, encoding="utf-8")


def stats_view(request):
    collections_by_journals = {}
    for collection in Collection.objects.filter(private=False).exclude(
        Q(DOI__isnull=True) | Q(DOI__exact="")
    ):
        if not collection.journal_name:
            _, _, _, _, collection.journal_name = get_paper_properties(collection.DOI)
            collection.save()
        if collection.journal_name not in list(collections_by_journals.keys()):
            collections_by_journals[collection.journal_name] = 1
        else:
            collections_by_journals[collection.journal_name] += 1
    collections_by_journals = OrderedDict(
        sorted(list(collections_by_journals.items()), key=lambda t: t[1], reverse=True)
    )

    non_empty_collections_count = (
        Collection.objects.annotate(num_submissions=Count("basecollectionitem"))
        .filter(num_submissions__gt=0)
        .count()
    )
    public_collections_count = (
        Collection.objects.filter(private=False)
        .annotate(num_submissions=Count("basecollectionitem"))
        .filter(num_submissions__gt=0)
        .count()
    )
    public_collections_with_DOIs_count = (
        Collection.objects.filter(private=False)
        .exclude(Q(DOI__isnull=True) | Q(DOI__exact=""))
        .annotate(num_submissions=Count("basecollectionitem"))
        .filter(num_submissions__gt=0)
        .count()
    )
    context = {
        "collections_by_journals": collections_by_journals,
        "non_empty_collections_count": non_empty_collections_count,
        "public_collections_count": public_collections_count,
        "public_collections_with_DOIs_count": public_collections_with_DOIs_count,
    }
    return render(request, "statmaps/stats.html", context)


def papaya_js_embed(request, pk, iframe=None):
    tpl = "papaya_embed.tpl.js"
    mimetype = "text/javascript"
    if iframe is not None:
        tpl = "papaya_frame.html"
        mimetype = "text/html"
    image = get_image(pk, None, request)
    if image.collection.private:
        return HttpResponseForbidden()
    context = {"image": image, "request": request}
    return render(request, "statmaps/%s" % tpl, context, content_type=mimetype)


@csrf_exempt
def atlas_query_region(request):
    # this query is significantly faster (from 2-4 seconds to <1 second) if the synonyms don't need to be queried
    # i was previously in contact with NIF and it seems like it wouldn't be too hard to download all the synonym data
    search = request.GET.get("region", "")
    atlas = request.GET.get("atlas", "").replace("'", "")
    collection = name = request.GET.get("collection", "")
    neurovault_root = os.path.dirname(
        os.path.dirname(os.path.realpath(neurovault.__file__))
    )
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse(
            "error: could not find collection: %s" % collection, status=400
        )
    try:
        atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
        atlas_image = atlas_object.file
        atlas_xml = atlas_object.label_description_file
    except IndexError:
        return JSONResponse("could not find %s" % atlas, status=400)
    if request.method == "GET":
        atlas_xml.open()
        root = ET.fromstring(atlas_xml.read())
        atlas_xml.close()
        atlasRegions = [x.text.lower() for x in root.find("data").findall("label")]
        if search in atlasRegions:
            searchList = [search]
        else:
            synonymsDict = {}
            with open(
                os.path.join(neurovault_root, "neurovault/apps/statmaps/NIFgraph.pkl"),
                "rb",
            ) as input:
                graph = joblib.load(input)
            for atlasRegion in atlasRegions:
                synonymsDict[atlasRegion] = getSynonyms(atlasRegion)
            try:
                searchList = toAtlas(search, graph, atlasRegions, synonymsDict)
            except ValueError:
                return JSONResponse(
                    "error: region not in atlas or ontology", status=400
                )
            if searchList == "none":
                return JSONResponse(
                    "error: could not map specified region to region in specified atlas",
                    status=400,
                )
        try:
            data = {"voxels": getAtlasVoxels(searchList, atlas_image, atlas_xml)}
        except ValueError:
            return JSONResponse("error: region not in atlas", status=400)

        return JSONResponse(data)


@csrf_exempt
def atlas_query_voxel(request):
    X = request.GET.get("x", "")
    Y = request.GET.get("y", "")
    Z = request.GET.get("z", "")
    collection = name = request.GET.get("collection", "")
    atlas = request.GET.get("atlas", "").replace("'", "")
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse(
            "error: could not find collection: %s" % collection, status=400
        )
    try:
        atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
        atlas_image = atlas_object.file
        atlas_xml = atlas_object.label_description_file
    except IndexError:
        return JSONResponse("error: could not find atlas: %s" % atlas, status=400)
    try:
        data = voxelToRegion(X, Y, Z, atlas_image, atlas_xml)
    except IndexError:
        return JSONResponse(
            "error: one or more coordinates are out of range", status=400
        )
    return JSONResponse(data)


def compare_images(request, pk1, pk2):
    raise Http404("Disabled for upgrade") 


# Return search interface for one image vs rest
def find_similar(request, pk):
    image1 = get_image(pk, None, request)
    pk = int(pk)
    max_results = 10

    # Search only enabled if the image is not thresholded
    if image1.is_thresholded:
        error_message = "Image comparison is not enabled for thresholded images."
        context = {"error_message": error_message}
        return render(request, "statmaps/error_message.html", context)

    image_title = format_image_collection_names(
        image_name=image1.name,
        collection_name=image1.collection.name,
        map_type=image1.map_type,
        total_length=50,
    )
    # Here is the query image
    query_png = image1.thumbnail.url

    context = {"image": image1, "image_title": image_title, "query_png": query_png}
    template = "statmaps/compare_search.html"
    return render(request, template, context)


def find_similar_json(request, pk, collection_cid=None):
    limit = 500  # maximum number of Comparisons allowed to retrieve
    max_results = int(request.GET.get("q", "100"))
    if max_results > limit:
        max_results = limit

    image1 = get_image(pk, None, request)
    pk = int(pk)

    # Search only enabled if the image is not thresholded
    if image1.is_thresholded:
        return JSONResponse(
            "error: Image comparison is not enabled for thresholded images.", status=400
        )
    else:
        similar_images = get_similar_images(pk, max_results)

    dict = similar_images.to_dict("split")
    del dict["index"]
    return JSONResponse(dict)


# Return search interface
def search(request, error_message=None):
    cogatlas_task = CognitiveAtlasTask.objects.all()
    context = {"message": error_message, "cogatlas_task": cogatlas_task}
    return render(request, "statmaps/search.html", context)


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """

    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs["content_type"] = "application/json"
        super(JSONResponse, self).__init__(content, **kwargs)


class AllDOIPublicGroupImages(BaseDatatableView):
    columns = [
        "collection.name",
        "collection.description",
        "name",
        "description",
        "modality",
    ]
    order_columns = [
        "collection.name",
        "collection.description",
        "name",
        "description",
        "modality",
    ]

    def get_initial_queryset(self):
        if "metaanalysis_id" in list(self.kwargs.keys()):
            metaanalysis = Metaanalysis.objects.get(pk=self.kwargs["metaanalysis_id"])
            return metaanalysis.maps.all()
        else:
            public_collections_ids = (
                Collection.objects.exclude(DOI__isnull=True)
                .exclude(private=True)
                .values_list("id", flat=True)
            )
            return (
                StatisticMap.objects.filter(analysis_level="G")
                .filter(map_type__in=["T", "Z"])
                .filter(collection_id__in=public_collections_ids)
            )

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(collection__name__icontains=search)
                | Q(collection__description__icontains=search)
            )
        return qs


class ImagesInCollectionJson(BaseDatatableView):
    columns = ["file.url", "pk", "name", "polymorphic_ctype.name", "is_valid"]
    order_columns = ["", "pk", "name", "polymorphic_ctype.name", ""]

    def get_initial_queryset(self):
        # return queryset used as base for further sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        collection = get_collection(self.kwargs["cid"], self.request)
        return collection.basecollectionitem_set.all()

    def render_column(self, row, column):
        if row.polymorphic_ctype.name == "statistic map":
            type = row.get_map_type_display()
        else:
            type = row.polymorphic_ctype.name

        # We want to render user as a custom column
        if column == "file.url":
            if isinstance(row, Image):
                return get_button_html(
                    filepath_to_uri(row.file.url), type, row.target_template_image
                )
            elif isinstance(row, NIDMResults):
                try:
                    excursion_sets = list(
                        Graph(row.zip_file.path).get_excursion_set_maps().values()
                    )
                    map_url = (
                        row.get_absolute_url() + "/" + str(excursion_sets[0].file.path)
                    )
                except KeyError:
                    maps = Graph(row.zip_file.path).get_statistic_maps()
                    map_url = row.get_absolute_url() + "/" + str(maps[0].file.path)
                return get_button_html(map_url, type, DEFAULT_TEMPLATE)
        elif column == "polymorphic_ctype.name":
            return type
        elif column == "is_valid":
            if row.polymorphic_ctype.name == "nidm results":
                return True
            else:
                return row.is_valid
        else:
            return super(ImagesInCollectionJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class SingleSubjectImagesInCollectionJson(ImagesInCollectionJson):
    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return StatisticMap.objects.filter(collection=collection).filter(
            analysis_level="S"
        )


class GroupImagesInCollectionJson(ImagesInCollectionJson):
    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return StatisticMap.objects.filter(collection=collection).filter(
            analysis_level="G"
        )


class OtherImagesInCollectionJson(ImagesInCollectionJson):
    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return StatisticMap.objects.filter(collection=collection).filter(
            ~Q(analysis_level__in=["G", "S"])
        )


class ImagesByTaskJson(BaseDatatableView):
    columns = ["file.url", "name", "cognitive_contrast_cogatlas", "collection.name"]
    order_columns = ["", "name", "cognitive_contrast_cogatlas", "collection.name"]

    def get_initial_queryset(self):
        # Do not filter by task here, we may want other parameters
        cog_atlas_id = self.kwargs["cog_atlas_id"]
        return StatisticMap.objects.filter(collection__private=False).filter(
            cognitive_paradigm_cogatlas=cog_atlas_id
        )

    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == "file.url":
            if isinstance(row, Image):
                return get_button_html(
                    filepath_to_uri(row.file.url), type, row.target_template_image
                )
            elif isinstance(row, NIDMResults):
                return ""
        else:
            return super(ImagesByTaskJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset
        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(id__icontains=search))
        return qs


class AtlasesAndParcellationsJson(BaseDatatableView):
    columns = [
        "file.url",
        "name",
        "collection.name",
        "collection.authors",
        "polymorphic_ctype.name",
    ]
    order_columns = ["", "name", "polymorphic_ctype.name"]

    def get_initial_queryset(self):
        # return queryset used as base for further sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        qs = Image.objects.instance_of(Atlas) | Image.objects.instance_of(
            StatisticMap
        ).filter(statisticmap__map_type=BaseStatisticMap.Pa)
        qs = qs.filter(collection__private=False).exclude(collection__DOI__isnull=True)
        return qs

    def render_column(self, row, column):
        if row.polymorphic_ctype.name == "statistic map":
            type = row.get_map_type_display()
        else:
            type = row.polymorphic_ctype.name

        # We want to render user as a custom column
        if column == "file.url":
            return get_button_html(
                filepath_to_uri(row.file.url), type, row.target_template_image
            )
        elif column == "polymorphic_ctype.name":
            return type
        if column == "collection.authors" and row.collection.authors:
            return row.collection.authors.split(",")[0].split(" ")[-1] + " et al."
        if column == "collection.name":
            return (
                "<a href='"
                + row.collection.get_absolute_url()
                + "'>"
                + row.collection.name
                + "</a>"
            )
        else:
            return super(AtlasesAndParcellationsJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class PublicCollectionsJson(BaseDatatableView):
    columns = ["name", "n_images", "description", "has_doi"]
    order_columns = ["name", "", "description", ""]

    def get_initial_queryset(self):
        # return queryset used as base for further sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        return Collection.objects.filter(
            ~Q(name__endswith="temporary collection"), private=False
        )

    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == "has_doi":
            if row.DOI:
                return "Yes"
            else:
                return ""
        elif column == "n_images":
            return row.basecollectionitem_set.count()
        else:
            return super(PublicCollectionsJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class MyCollectionsJson(PublicCollectionsJson):
    def get_initial_queryset(self):
        return get_objects_for_user(self.request.user, "statmaps.change_collection")


class MyMetaanalysesJson(PublicCollectionsJson):
    columns = ["name", "description", "n_images", "status"]
    order_columns = ["name", "description", "", ""]

    def get_initial_queryset(self):
        return Metaanalysis.objects.filter(owner=self.request.user)

    def render_column(self, row, column):
        if column == "n_images":
            return row.maps.count()
        elif column == "name":
            return (
                "<a href='"
                + reverse(
                    "statmaps:view_metaanalysis", kwargs={"metaanalysis_id": row.pk}
                )
                + "'>"
                + row.name
                + "</a>"
            )
        else:
            return super(PublicCollectionsJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


def download_collection(request, cid):
    # Files (local path) to put in the .zip
    collection = get_collection(cid, request)

    filenames = [
        img.zip_file.path
        for img in collection.basecollectionitem_set.instance_of(NIDMResults)
    ] + [
        img.file.path
        for img in (
            collection.basecollectionitem_set.instance_of(Image).not_instance_of(
                NIDMResultStatisticMap
            )
        )
    ]

    # Folder name in ZIP archive which contains the above files
    # E.g [collection.name.zip]/collection.name/img.id.nii.gz
    zip_subdir = collection.name
    zip_filename = "%s.zip" % collection.name

    zf = zipstream.ZipFile(mode="w", compression=zipstream.ZIP_DEFLATED)
    for fpath in filenames:
        # Calculate path for file in zip
        fdir, fname = os.path.split(fpath)
        zip_path = os.path.join(zip_subdir, fname)

        # Add file, at correct path
        zf.write(fpath, zip_path)

    response = StreamingHttpResponse(zf, content_type="application/zip")
    response[
        "Content-Disposition"
    ] = "attachment; filename=%s" % urllib.parse.quote_plus(
        zip_filename.encode("utf-8")
    )

    return response


def serve_surface_archive(request, pk, collection_cid=None):
    img = get_image(pk, collection_cid, request)
    user_owns_image = owner_or_contrib(request, img.collection)
    api_cid = pk

    filenames = [img.surface_left_file.path, img.surface_right_file.path]

    # Folder name in ZIP archive which contains the above files
    # E.g [collection.name.zip]/collection.name/img.id.nii.gz
    zip_subdir = img.name
    zip_filename = "%s.zip" % img.name

    zf = zipstream.ZipFile(mode="w", compression=zipstream.ZIP_DEFLATED)

    for fpath in filenames:
        # Calculate path for file in zip
        fdir, fname = os.path.split(fpath)
        zip_path = os.path.join(zip_subdir, fname)

        # Add file, at correct path
        zf.write(fpath, zip_path)

    response = StreamingHttpResponse(zf, content_type="application/zip")
    response["Content-Disposition"] = "attachment; filename=%s" % zip_filename
    return response


def gene_expression(request, pk, collection_cid=None):
    '''view_image returns main view to see an image and associated meta data. If the image is in a collection with a DOI and has a generated thumbnail, it is a contender for image comparison, and a find similar button is exposed.
    :param pk: statmaps.models.Image.pk the primary key of the image
    :param collection_cid: statmaps.models.Collection.pk the primary key of the collection. Default None
    '''
    image = get_image(pk, collection_cid, request)
    if image.is_thresholded:
        raise Http404
    api_cid = pk
    if image.collection.private:
        api_cid = '%s-%s' % (image.collection.private_token,pk)
    context = {
        'image': image,
        'api_cid': api_cid,
        'mask': request.GET.get('mask', 'full')
    }
    template = 'statmaps/gene_expression.html'
    return render(request, template, context)

def gene_expression_json(request, pk, collection_cid=None):
    image = get_image(pk, collection_cid, request)
    if image.is_thresholded:
        raise Http404

    if not image.reduced_representation or not os.path.exists(image.reduced_representation.path):
        image = save_resampled_transformation_single(image.id)

    map_data = np.load(image.reduced_representation.file)

    mask = request.GET.get('mask', None)
    expression_results = calculate_gene_expression_similarity(map_data, mask)
    dict = expression_results.to_dict("split")
    del dict["index"]
    return JSONResponse(dict)
