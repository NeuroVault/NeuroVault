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
from django.core.files.base import ContentFile
from django.db.models import Max, Q, Exists, OuterRef, DateTimeField 
from django.db.models.aggregates import Count
from django.db.models import Value
from django.http import Http404, HttpResponse, StreamingHttpResponse, JsonResponse
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.encoding import filepath_to_uri
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.urls import reverse
from fnmatch import fnmatch
from guardian.shortcuts import get_objects_for_user
from urllib.parse import urlencode

# from nidmviewer.viewer import generate
# from pybraincompare.compare.scatterplot import scatterplot_compare_vector
from nidmresults.graph import Graph
from rest_framework.renderers import JSONRenderer
from sendfile import sendfile
import joblib

from neurovault.adapters.persistence.models import get_possible_templates, DEFAULT_TEMPLATE

import neurovault
from django.conf import settings
from neurovault.adapters.web.statmaps.ahba import calculate_gene_expression_similarity
from neurovault.adapters.web.statmaps.forms import (
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
from neurovault.adapters.persistence.models import (
    Collection,
    Item,
    NIDMBundle,
    CognitiveAtlasTask,
    CognitiveAtlasContrast,
    DEFAULT_TEMPLATE,
    Metaanalysis,
)
from neurovault.adapters.web.statmaps.utils import (
    split_filename,
    generate_pycortex_volume,
    generate_pycortex_static,
    HttpRedirectException,
    get_file_ctime,
    get_server_url,
    format_image_collection_names,
    is_search_compatible,
    get_similar_images,
)
from neurovault.adapters.web.statmaps.utils import (
    is_target_template_image_pycortex_compatible,
    is_target_template_image_neurosynth_compatible,
)
from neurovault.adapters.web.statmaps.forms import image_changes
from neurovault.core.application.ports import Actor
from neurovault.config.bootstrap import services
from neurovault.core.domain.errors import DomainValidationError, PermissionDenied as DomainPermissionDenied
from neurovault.adapters.web.statmaps.voxel_query_functions import *
from . import image_metadata



NIF_GRAPH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NIFgraph.pkl")


def actor(request):
    if not request.user.is_authenticated:
        return Actor(None)
    return Actor(request.user.pk, request.user.is_superuser)


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
    image = get_object_or_404(Item, pk=pk)
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
            metaanalysis_id = services().metaanalyses.save(
                actor(request), metaanalysis.pk, form.cleaned_data["name"],
                form.cleaned_data.get("description"),
            )
            return HttpResponseRedirect(
                reverse("statmaps:view_metaanalysis", args=[str(metaanalysis_id)])
            )
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

    collection_id = services().metaanalyses.finalize(
        actor(request), metaanalysis.pk, metaanalysis.get_absolute_url()
    )
    new_collection = Collection.objects.get(pk=collection_id)
    return HttpResponseRedirect(new_collection.get_absolute_url())

@login_required
def toggle_active_metaanalysis(request, pk, collection_cid=None):
    image = get_image(pk, collection_cid, request)
    new_status = services().metaanalyses.toggle_map(actor(request), image.pk)
    return JSONResponse({"new_status": new_status})


@login_required
def activate_metaanalysis(request, metaanalysis_id):
    metaanalysis = Metaanalysis.objects.get(pk=metaanalysis_id)
    try:
        services().metaanalyses.activate(actor(request), metaanalysis.pk)
    except DomainPermissionDenied:
        return HttpResponseForbidden()
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
            collection_id = services().collections.save(
                actor(request),
                form.instance.pk,
                collection_changes(form),
                contributor_ids=[u.pk for u in form.cleaned_data["contributors"]] if is_owner else None,
                community_ids=[c.pk for c in form.cleaned_data["communities"]] if is_owner else None,
                absolute_url=lambda cid: get_server_url(request)
                + Collection.objects.get(pk=cid).get_absolute_url(),
            )
            return HttpResponseRedirect(Collection.objects.get(pk=collection_id).get_absolute_url())
    else:
        if is_owner:
            form = OwnerCollectionForm(instance=collection)
        else:
            form = CollectionForm(instance=collection)

    context = {"form": form, "page_header": page_header, "is_owner": is_owner, "preamble": "Please fill in the fields below to create a new collection."}
    return render(request, "statmaps/edit_collection.html", context)


def collection_changes(form):
    """Column changes from a valid collection form (read back from form.instance)."""
    changes = {}
    for name in form.fields:
        if name in ("contributors", "communities"):
            continue
        try:
            field = form.instance._meta.get_field(name)
        except Exception:
            continue
        changes[name] = getattr(form.instance, field.attname)
    return changes


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
    ds = choice_datasources(Item)
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

    collection_images = collection.items.order_by("pk")
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
            "main:view_community", kwargs={"community_label": main_community.label}
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
        image.kind == Item.STATMAP
        and image.source_bundle_id is None
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

    if image.source_bundle_id is not None:
        context["img_basename"] = os.path.basename(image.file.url)
        context["ttl_basename"] = os.path.basename(image.source_bundle.ttl_file.url)

    if image.kind == Item.ATLAS:
        template = "statmaps/atlas_details.html"
    else:
        if np.isnan(image.perc_bad_voxels) or np.isnan(image.perc_voxels_outside):
            context["warning"] = "Warning: This map seems to be empty!"
        elif not image.is_valid:
            context["warning"] = "Warning: This map is missing some mandatory metadata!"
            if user_owns_image:
                edit_url = reverse("statmaps:edit_image", kwargs={"pk": pk})
                context[
                    "warning"
                ] += f" Please <a href='{edit_url}'>edit image details</a> to provide the missing information."
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
    is_empty = collection.item_count() == 0
    pycortex_compatible = all(
        [
            is_target_template_image_pycortex_compatible(image.target_template_image)
            for image in collection.items.all()
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
    if collection.nidm_bundles.exists() or collection.items.exclude(
        kind=Item.STATMAP, source_bundle__isnull=True
    ).exists():
        context["images_visible"] = True
    else:
        context["images_visible"] = False
        if (
            Item.objects.statmaps().filter(collection=collection)
            .filter(analysis_level="G")
            .count()
            > 0
        ):
            context["gimages_visible"] = True
            context["gimages_active"] = True

        if (
            Item.objects.statmaps().filter(collection=collection)
            .filter(analysis_level="S")
            .count()
            > 0
        ):
            context["simages_visible"] = True
            if not context["gimages_visible"]:
                context["simages_active"] = True

        if (
            Item.objects.statmaps().filter(collection=collection)
            .filter(~Q(analysis_level__in=["G", "S"]))
            .count()
            > 0
        ):
            if (
                Item.objects.statmaps().filter(collection=collection)
                .filter(~Q(analysis_level__in=["G", "S"]))
                .filter(is_valid=False)
                .count()
            ):
                context["oimages_title"] = "Needs Metadata"

            context["oimages_visible"] = True
            if not (context["gimages_visible"] or context["simages_visible"]):
                context["oimages_active"] = True
                context["oimages_title"] = "Images"

    communities = collection.communities.all()
    add_communities_context(communities, context)

    if not all(
        collection.items.statmaps().values_list("is_valid", flat=True)
    ):
        msg = "Some of the images in this collection are missing crucial metadata."
        if owner_or_contrib(request, collection):
            msg += " Please add the missing information by <a href='editmetadata'>editing images metadata</a>."
        messages.warning(request, msg)

    if not is_empty:
        first_items = [
            qs.order_by("pk").first() for qs in (collection.items.all(), collection.nidm_bundles.all())
        ]
        context["first_image"] = min((i for i in first_items if i is not None), key=lambda i: i.pk)

    if owner_or_contrib(request, collection):
        form = UploadFileForm()
        context["form"] = UploadFileForm()
    return render(request, "statmaps/collection_details.html", context)


@login_required
def delete_collection(request, cid):
    collection = get_collection(cid, request)
    if not request.user.has_perm("statmaps.delete_collection", collection):
        return HttpResponseForbidden()
    services().collections.delete(actor(request), collection.pk)
    return redirect("statmaps:my_collections")


def _get_sibling_images(current_image):
    collection_images = current_image.collection.items.all()
    image_ids = sorted(list(collection_images.values_list("id", flat=True)))
    current_index = image_ids.index(current_image.id)

    prev_id = image_ids[current_index - 1] if current_index > 0 else None
    next_id = image_ids[current_index + 1] if current_index < len(image_ids) - 1 else None

    prev_image = collection_images.filter(pk=prev_id).first() if prev_id else None
    next_image = collection_images.filter(pk=next_id).first() if next_id else None
    return (prev_image, next_image)


def _serialize_collection(collection_images):
    """
    Return a list of dictionaries representing each image in the collection.
    Each dictionary is also stored in JSON under the 'json_data' key.
    """

    base_fields = [
        "id", "name", "description", "is_valid", "map_type",
        "target_template_image", "figure", "handedness", "age",
        "gender", "race", "ethnicity"
    ]
    statmap_fields = [
        "analysis_level", "modality", "number_of_subjects",
        "contrast_definition", "statistic_parameters", "smoothness_fwhm",
        "cognitive_paradigm_short_description", "cognitive_paradigm_description_url",
        "cognitive_contrast_short_description", "cognitive_paradigm_name"
    ]

    def serialize(img):
        # Start with "base" fields for all images.
        data = {field: getattr(img, field, "") for field in base_fields}
        data["last_edited"] = img.modify_date.strftime('%Y-%m-%d %H:%M:%S') if img.modify_date != img.add_date else None

        # If it's an uploaded statistic map, copy the statmap-specific fields.
        if img.kind == Item.STATMAP and img.source_bundle_id is None:
            for field in statmap_fields:
                data[field] = getattr(img, field, "") or ""
            data["cognitive_atlas_paradigm"] = getattr(img.cognitive_paradigm_cogatlas, "cog_atlas_id", None)
            data["cognitive_atlas_contrast"] = getattr(img.cognitive_contrast_cogatlas, "cog_atlas_id", None)
        else:
            # Non-statmaps still need these keys defined, but empty.
            data["cognitive_atlas_paradigm"] = ""
            data["cognitive_atlas_contrast"] = ""

        # Store the entire dict as JSON as well.
        data["json_data"] = json.dumps(data)
        return data

    # Serialize each image using a list comprehension.
    return [serialize(img) for img in collection_images]


def _get_form_for_image(image):
    """
    Return the appropriate form class (and extra kwargs if needed)
    based on the image's model class.
    """
    if image.kind == Item.STATMAP and image.source_bundle_id is None:
        return EditStatisticMapForm
    elif image.kind == Item.ATLAS:
        return EditAtlasForm
    elif image.kind == Item.STATMAP:
        return EditNIDMResultStatisticMapForm
    else:
        raise Exception("Unsupported image type.")


def _parse_int_param(value, default=""):
    """
    Safely parse a string as an integer.
    Return the default if parsing fails or value is None/empty.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _compute_progress(min_image, max_image):
    """
    Compute the progress of images being processed based on is_valid attribute
    Potential progress is computed by assuming the next image is valid.
    """
    images = Item.objects.filter(pk__gte=min_image, pk__lte=max_image)
    total_images = images.count()
    valid_images = images.filter(is_valid=True).count()
    progress = int((valid_images / total_images) * 100) if total_images > 0 else 0
    potential_progress = int((valid_images + 1 / total_images) * 100) if total_images > 0 else 0
    label = f"{valid_images}/{total_images}"
    return progress, label, potential_progress

@login_required
def edit_image(request, pk):
    image = get_object_or_404(Item, pk=pk)

    show_instructions = request.GET.get("show_instructions") == "True"

    kw_params = {
        "bulk": request.GET.get("bulk") == "True",
        "min_image": _parse_int_param(request.GET.get("min_image")),
        "max_image": _parse_int_param(request.GET.get("max_image")),
    }
    passalong_query = f"?{urlencode(kw_params)}"

    if kw_params["bulk"] and kw_params["min_image"] != "":
        progress, label, potential_progress = _compute_progress(kw_params["min_image"], kw_params["max_image"])
    else:
        progress, label, potential_progress = None, None, None

    collection_images_qs = (
        image.collection.items
        .exclude(pk=image.pk)
    )

    if not owner_or_contrib(request, image.collection):
        return HttpResponseForbidden()

    form_class = _get_form_for_image(image)

    if request.method == "POST":
        form = form_class(
            data=request.POST,
            files=request.FILES,
            instance=image,
            user=request.user,
            **kw_params
        )
        if form.is_valid():
            changes, files, tags = image_changes(form)
            services().items.change(actor(request), image.pk, changes, files, tags=tags)
            if any(key in request.POST for key in ["submit_next", "submit_previous"]):
                prev_img, next_img = _get_sibling_images(image)
                target_img = next_img if "submit_next" in request.POST else prev_img
                if target_img:
                    return HttpResponseRedirect(
                        target_img.get_absolute_url(edit=True) + passalong_query
                        )
            elif "submit_save" in request.POST:
                if kw_params["bulk"]:
                    return HttpResponseRedirect(image.collection.get_absolute_url())
                else:
                    return HttpResponseRedirect(image.get_absolute_url())
        else:
            print(form.errors)
    else:
        if image.kind == Item.STATMAP and kw_params["bulk"] and not image.is_valid:
            image.name = ""
            image.map_type = None

        form = form_class(instance=image, user=request.user, **kw_params)

    context = {
        "form": form,
        "contrasts": json.dumps(get_contrast_lookup()),
        "collection_images": _serialize_collection(collection_images_qs),
        "progress": progress,
        "progress_label": label,
        "potential_progress": potential_progress,
        "show_instructions": show_instructions,
    }
    return render(request, "statmaps/edit_image.html", context)


def view_nidm_results(request, collection_cid, nidm_name):
    raise Http404("Disabled for upgrade")


@login_required
def delete_nidm_results(request, collection_cid, nidm_name):
    collection = get_collection(collection_cid, request)
    nidmr = get_object_or_404(NIDMBundle, collection=collection, name=nidm_name)

    try:
        services().bundles.delete(actor(request), nidmr.pk)
    except DomainPermissionDenied:
        return HttpResponseForbidden()
    return redirect("statmaps:collection_details", cid=collection_cid)


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
        images = Item.objects.statmaps().filter(
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
    temp_collection = Collection.objects.get(
        pk=services().collections.temporary_for(request.user.pk, request.user.username, is_private)
    )
    image = Item(kind=Item.STATMAP, collection=temp_collection)
    if request.method == "POST":
        form = formclass(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            changes, files, tags = image_changes(form)
            collection_id = changes.pop("collection_id")
            image_id = services().items.add(
                actor(request), collection_id, "statmap", changes, files, tags=tags
            )
            redirect = redirect_url % {
                "private_token": temp_collection.private_token,
                "image_id": image_id,
            }
            return HttpResponseRedirect(redirect)
    else:
        form = formclass(user=request.user, instance=image)
    contrasts = get_contrast_lookup()
    context = {"form": form, "contrasts": json.dumps(contrasts), "preamble": preamble, "progress": 0, "potential_progress": 1}
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
    if request.method != "POST":
        return HttpResponseRedirect(collection.get_absolute_url())
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.warning(request, f"{error}")
        return HttpResponseRedirect(collection.get_absolute_url())

    folder = "file" not in request.FILES and "file_input[]" in request.FILES
    try:
        result = services().uploads.ingest(
            actor(request),
            collection.pk,
            upload=request.FILES.get("file"),
            folder_files=request.FILES.getlist("file_input[]"),
            folder_paths=request.POST.getlist("paths[]"),
        )
    except DomainValidationError:
        messages.warning(request, "Invalid NIDM-Results file.")
        return HttpResponseRedirect(collection.get_absolute_url())
    except Exception:
        error = traceback.format_exc().splitlines()[-1]
        messages.warning(request, f"An error occurred with this upload: {error}")
        return HttpResponseRedirect(collection.get_absolute_url())

    for warning in result.warnings:
        messages.warning(request, warning)
    if result.bundle_id is not None:
        return HttpResponseRedirect(collection.get_absolute_url())
    if not result.item_ids:
        if not result.warnings:
            messages.warning(
                request, "No NIFTI files (.nii, .nii.gz, .img/.hdr) found in the upload."
            )
        return HttpResponseRedirect(collection.get_absolute_url())

    first = Item.objects.get(pk=result.item_ids[0])
    params = {
        "bulk": True,
        "show_instructions": True,
        "min_image": result.item_ids[0],
        "max_image": result.item_ids[-1],
    }
    redirect_to = first.get_absolute_url(edit=True) + f"?{urlencode(params)}"
    if folder:
        return JsonResponse({"redirect_url": redirect_to})
    return HttpResponseRedirect(redirect_to)


@login_required
def delete_image(request, pk):
    image = get_object_or_404(Item, pk=pk)
    cid = image.collection.pk
    try:
        services().items.delete(actor(request), image.pk)
    except DomainPermissionDenied:
        return HttpResponseForbidden()
    return redirect(reverse("statmaps:collection_details", kwargs={"cid": cid}))


def view_images_by_tag(request, tag):
    if request.user.is_authenticated:
        images = Item.objects.filter(tags__name__in=[tag]).filter(
            Q(collection__private=False) | Q(collection__owner=request.user)
        )
    else:
        images = Item.objects.filter(tags__name__in=[tag]).filter(
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
    images = collection.items.all()

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
        nidmr = collection.nidm_bundles.get(name=nidmdir)
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
            collection.journal_name = services().collections.refresh_journal_name(collection.pk)
        if collection.journal_name not in list(collections_by_journals.keys()):
            collections_by_journals[collection.journal_name] = 1
        else:
            collections_by_journals[collection.journal_name] += 1
    collections_by_journals = OrderedDict(
        sorted(list(collections_by_journals.items()), key=lambda t: t[1], reverse=True)
    )

    non_empty_collections_count = (
        Collection.objects.filter(Q(items__isnull=False) | Q(nidm_bundles__isnull=False))
        .distinct()
        .count()
    )
    public_collections_count = (
        Collection.objects.filter(private=False)
        .filter(Q(items__isnull=False) | Q(nidm_bundles__isnull=False))
        .distinct()
        .count()
    )
    public_collections_with_DOIs_count = (
        Collection.objects.filter(private=False)
        .exclude(Q(DOI__isnull=True) | Q(DOI__exact=""))
        .filter(Q(items__isnull=False) | Q(nidm_bundles__isnull=False))
        .distinct()
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
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse(
            "error: could not find collection: %s" % collection, status=400
        )
    try:
        atlas_object = Item.objects.atlases().filter(name=atlas, collection=collection_object)[0]
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
                NIF_GRAPH,
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
        atlas_object = Item.objects.atlases().filter(name=atlas, collection=collection_object)[0]
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
                Item.objects.statmaps().filter(analysis_level="G")
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
    """Images and NIDM bundles of a collection (two tables, listed together)."""

    columns = ["file.url", "pk", "type_label", "is_valid"]
    order_columns = ["", "pk", "kind", ""]

    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return sorted(
            list(collection.items.all()) + list(collection.nidm_bundles.all()), key=lambda r: r.pk
        )

    def count_records(self, qs):
        return len(qs) if isinstance(qs, list) else super().count_records(qs)

    def ordering(self, qs):
        if not isinstance(qs, list):
            return super().ordering(qs)
        keys = {"pk": lambda r: r.pk, "kind": lambda r: r.type_label}
        for n in reversed(range(len(self.order_columns))):
            column = self._querydict.get("order[%s][column]" % n)
            if column is None:
                continue
            name = self.order_columns[int(column)]
            if name in keys:
                qs = sorted(qs, key=keys[name],
                            reverse=self._querydict.get("order[%s][dir]" % n) == "desc")
        return qs

    def render_column(self, row, column):
        if row.type_label == "statistic map":
            type = row.get_map_type_display()
        else:
            type = row.type_label

        # We want to render user as a custom column
        if column == "file.url":
            if isinstance(row, Item):
                return get_button_html(
                    filepath_to_uri(row.file.url), type, row.target_template_image
                )
            elif isinstance(row, NIDMBundle):
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
        elif column == "type_label":
            return type
        elif column == "is_valid":
            if isinstance(row, NIDMBundle):
                return True
            else:
                return row.is_valid
        else:
            return super(ImagesInCollectionJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        search = self.request.GET.get("search[value]", None)
        if search:
            if isinstance(qs, list):
                needle = search.lower()
                qs = [r for r in qs if needle in (r.name or "").lower()
                      or needle in (r.description or "").lower()]
            else:
                qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class SingleSubjectImagesInCollectionJson(ImagesInCollectionJson):
    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return Item.objects.statmaps().filter(collection=collection).filter(
            analysis_level="S"
        )


class GroupImagesInCollectionJson(ImagesInCollectionJson):
    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return Item.objects.statmaps().filter(collection=collection).filter(
            analysis_level="G"
        )


class OtherImagesInCollectionJson(ImagesInCollectionJson):
    def get_initial_queryset(self):
        collection = get_collection(self.kwargs["cid"], self.request)
        return Item.objects.statmaps().filter(collection=collection).filter(
            ~Q(analysis_level__in=["G", "S"])
        )


class ImagesByTaskJson(BaseDatatableView):
    columns = ["file.url", "name", "cognitive_contrast_cogatlas", "collection.name"]
    order_columns = ["", "name", "cognitive_contrast_cogatlas", "collection.name"]

    def get_initial_queryset(self):
        # Do not filter by task here, we may want other parameters
        cog_atlas_id = self.kwargs["cog_atlas_id"]
        return Item.objects.statmaps().filter(collection__private=False).filter(
            cognitive_paradigm_cogatlas=cog_atlas_id
        )

    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == "file.url":
            if isinstance(row, Item):
                return get_button_html(
                    filepath_to_uri(row.file.url), type, row.target_template_image
                )
            elif isinstance(row, NIDMBundle):
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
        "type_label",
    ]
    order_columns = ["", "name", "kind"]

    def get_initial_queryset(self):
        # return queryset used as base for further sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        qs = Item.objects.atlases() | Item.objects.statmaps().filter(map_type=Item.Pa)
        qs = qs.filter(collection__private=False).exclude(collection__DOI__isnull=True)
        return qs

    def render_column(self, row, column):
        if row.type_label == "statistic map":
            type = row.get_map_type_display()
        else:
            type = row.type_label

        # We want to render user as a custom column
        if column == "file.url":
            return get_button_html(
                filepath_to_uri(row.file.url), type, row.target_template_image
            )
        elif column == "type_label":
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


class PublicCollections(TemplateView):
    template_name = "statmaps/collections_index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["map_types"] = Item.map_type.field.choices
        '''
        context["modalities"] = list(
            StatisticMap.objects.filter(collection__private=False)
            .exclude(collection__name__endswith="temporary collection")
            .exclude(modality='')
            .values('modality')
            .annotate(count=Count('collection', distinct=True))
            .order_by('-count')
        )

        context["tasks"] = list(
            CognitiveAtlasTask.objects.exclude(pk='None')
            .filter(
                statisticmap__isnull=False,
                statisticmap__collection__private=False
            )
            .values('pk', 'name')
            .annotate(count=Count('statisticmap__collection', distinct=True))
            .order_by('-count')
        )
        '''

        return context


class MyCollections(PublicCollections):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["own_collections"] = True
        return context


class PublicCollectionsJson(BaseDatatableView):
    columns = ["name", "n_images", "description", "has_doi", "latest_image_modify"]
    order_columns = ["name", "", "description", "DOI", "latest_image_modify"]

    def get_initial_queryset(self):
        # return queryset used as base for further sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        return Collection.objects.filter(
            private=False
        ).annotate(
            latest_image_modify=Value(None, output_field=DateTimeField())
        )
        '''
        .prefetch_related('basecollectionitem_set').annotate(
            latest_modified_image=Subquery(
                models.StatisticMap.objects.filter(collection=OuterRef('pk')).order_by('-modify_date').values('modify_date')[:1]))
        ).prefetch_related("basecollectionitem_set").annotate(
            latest_image_modify=Max('basecollectionitem__modify_date')
        '''

    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == "has_doi":
            if row.DOI:
                return "Yes"
            else:
                return ""
        elif column == "n_images":
            return row.item_count()
        elif column == "latest_image_modify":
            return ""
            '''
            if row.latest_image_modify is None:
                return ""
            else:
                return row.latest_image_modify.strftime("%Y-%m-%d")
            '''
        else:
            return super(PublicCollectionsJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset
        # filter_keys = ["hasDoi", "modality", "task"]
        filter_keys = ["hasDoi"]
        filters = {k: self.request.GET.get(k, None) for k in filter_keys}
        hasDOI = filters.pop("hasDoi", None)
        if hasDOI == "true":
            qs = qs.exclude(DOI__isnull=True).exclude(DOI='')

        image_filters = {}
        for key, value in filters.items():
            if value != "false":
                if key == "task":
                    image_filters["cognitive_paradigm_cogatlas"] = value
                else:
                    image_filters[key] = value

        if image_filters:
            # Build a subquery that matches the needed StatisticMap rows
            '''
            matching_subq = StatisticMap.objects.filter(
                collection=OuterRef('pk'),
                **image_filters
            )

            qs = qs.annotate(
                has_match=Exists(matching_subq)
            ).filter(has_match=True)
            '''

        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class MyCollectionsJson(PublicCollectionsJson):
    def get_initial_queryset(self):
        return get_objects_for_user(self.request.user, "statmaps.change_collection").annotate(
            latest_image_modify=Value(None, output_field=DateTimeField())
        )

        '''
        return get_objects_for_user(self.request.user, "statmaps.change_collection").annotate(
            latest_image_modify=Max('basecollectionitem__modify_date'),
        )
        '''

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

    filenames = [bundle.zip_file.path for bundle in collection.nidm_bundles.all()] + [
        img.file.path for img in collection.items.filter(source_bundle__isnull=True)
    ]

    # Folder name in ZIP archive which contains the above files
    # E.g [collection.name.zip]/collection.name/img.id.nii.gz
    zip_subdir = collection.name
    zip_filename = "%s.zip" % collection.name

    zf = zipstream.ZipFile(mode="w", compression=zipstream.ZIP_DEFLATED, allowZip64=True)
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
        services().items.ensure_reduced_representation(image.id)
        image = Item.objects.get(pk=image.id)

    map_data = np.load(image.reduced_representation.file)

    mask = request.GET.get('mask', 'full')
    expression_results = calculate_gene_expression_similarity(map_data, mask)
    dict = expression_results.to_dict("split")
    del dict["index"]
    return JSONResponse(dict)
