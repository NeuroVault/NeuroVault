"""Read-side helpers for the web views (queries, viewers, formatting)."""
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from subprocess import CalledProcessError

import cortex
import numpy as np
import pandas as pd
import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from neurovault.adapters.neuroimaging.workspace import split_filename  # noqa: F401

from neurovault.adapters.persistence.models import (
    Comparison,
    Item,
    get_possible_templates,
    DEFAULT_TEMPLATE,
)


# see CollectionRedirectMiddleware
class HttpRedirectException(Exception):
    pass


def generate_pycortex_volume(image):
    nifti_file = str(image.file.path)
    transform_name = "trans_%s" % image.pk
    temp_dir = tempfile.mkdtemp(dir=settings.PYCORTEX_DATASTORE)
    try:
        new_mni_dat = os.path.join(temp_dir, "mni152reg.dat")
        mni_mat = os.path.join(temp_dir, "mni152reg.mat")
        reference = os.path.join(
            os.environ["FREESURFER_HOME"],
            "subjects",
            "fsaverage",
            "mri",
            "brain.nii.gz",
        )
        shutil.copy(
            os.path.join(
                os.environ["FREESURFER_HOME"], "average", "mni152.register.dat"
            ),
            new_mni_dat,
        )
        # this avoids problems with white spaces in file names
        tmp_link = os.path.join(temp_dir, "tmp.nii.gz")
        os.symlink(nifti_file, tmp_link)
        try:
            subprocess.check_output(
                [
                    os.path.join(os.environ["FREESURFER_HOME"], "bin", "tkregister2"),
                    "--mov",
                    tmp_link,
                    "--targ",
                    reference,
                    "--reg",
                    new_mni_dat,
                    "--noedit",
                    "--nofix",
                    "--fslregout",
                    mni_mat,
                ]
            )
        except CalledProcessError as e:
            raise RuntimeError(
                str(e.cmd)
                + " returned code "
                + str(e.returncode)
                + " with output "
                + str(e.output)
            )

        x = np.loadtxt(mni_mat)
        xfm = cortex.xfm.Transform.from_fsl(x, nifti_file, reference)
        xfm.save("fsaverage", transform_name, "coord")

        dv = cortex.Volume(
            nifti_file,
            "fsaverage",
            transform_name,
            cmap="RdBu_r",
            dfilter="trilinear",
            description=image.description,
        )

        # default colormap range evaluated only at runtime (Dataview.to_json())
        # excludes max/min 1% : np.percentile(np.nan_to_num(self.data), 99)
        use_vmax = dv.to_json()["vmax"][0]
        dv.vmin = use_vmax * -1
        dv.vmax = use_vmax

        return dv

    finally:
        shutil.rmtree(temp_dir)


def generate_pycortex_static(volumes, output_dir, title=None):
    """
    Parameters
    ----------

    volumes: dict
        key is volume name; value is a set of images.

    output_dir: str
        file location to dump output html

    title: str (optional)
        HTML title of pycortex viewer.
    """
    app_path = os.path.abspath(os.path.dirname(__file__))
    tpl_path = os.path.join(app_path, "templates/pycortex/dataview.html")
    ds = cortex.Dataset(**volumes)
    title = title or ", ".join(list(volumes.keys()))
    cortex.webgl.make_static(
        output_dir,
        ds,
        template=tpl_path,
        html_embed=False,
        copy_ctmfiles=False,
        title=title,
    )


def get_file_ctime(fpath):
    return datetime.fromtimestamp(os.path.getctime(fpath), tz=pytz.utc)


def get_server_url(request):
    if request.META.get("HTTP_ORIGIN"):
        return request.META["HTTP_ORIGIN"]
    urlpref = "https://" if request.is_secure() else "http://"
    return "{0}{1}".format(urlpref, request.META["HTTP_HOST"])


# Returns string in format image: collection [map_type] to be within total_length
def format_image_collection_names(
    image_name, collection_name, total_length, map_type=None
):
    # 3/5 total length should be collection, 2/5 image
    collection_length = int(np.floor(0.60 * total_length))
    image_length = int(np.floor(total_length - collection_length))
    if len(image_name) > image_length:
        image_name = "%s..." % image_name[0:image_length]
    if len(collection_name) > collection_length:
        collection_name = "%s..." % collection_name[0:collection_length]
    if map_type == None:
        return "%s : %s" % (image_name, collection_name)
    else:
        return "%s : %s [%s]" % (image_name, collection_name, map_type)



def is_target_template_image_pycortex_compatible(
    target_template_image=DEFAULT_TEMPLATE,
):
    POSSIBLE_TEMPLATES = get_possible_templates()
    return POSSIBLE_TEMPLATES[target_template_image]["pycortex_enabled"]


def is_target_template_image_neurosynth_compatible(
    target_template_image=DEFAULT_TEMPLATE,
):
    POSSIBLE_TEMPLATES = get_possible_templates()
    return POSSIBLE_TEMPLATES[target_template_image]["image_search_enabled"]


def is_target_template_image_search_compatible(target_template_image=DEFAULT_TEMPLATE):
    POSSIBLE_TEMPLATES = get_possible_templates()
    return POSSIBLE_TEMPLATES[target_template_image]["image_search_enabled"]


###


# QUERY FUNCTIONS -------------------------------------------------------------------------------


def is_search_compatible(pk):
    try:
        img = Item.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return False

    if (
        img.kind != Item.STATMAP
        or img.is_thresholded
        or img.analysis_level is None
        or img.analysis_level == "S"
        or not is_target_template_image_search_compatible(img.target_template_image)
        or img.not_mni
        or img.map_type in ["R", "Pa", "A"]
        or img.collection.private
    ):
        return False
    else:
        return True


def get_images_to_compare_with(pk1, for_generation=False):
    # if the map in question is invalid do not generate any comparisons
    if not is_search_compatible(pk1):
        return []

    img = Item.objects.get(pk=pk1)
    image_pks = []
    for qs in [Item.objects.statmaps(), Item.objects.nidm_statmaps()]:
        qs = qs.filter(
            collection__private=False, is_thresholded=False, not_mni=False
        )
        if not (for_generation and img.collection.DOI is not None):
            qs = qs.exclude(collection__DOI__isnull=True)
        qs = qs.exclude(collection=img.collection)
        qs = (
            qs.exclude(pk=pk1)
            .exclude(analysis_level__isnull=True)
            .exclude(analysis_level="S")
            .exclude(map_type="R")
            .exclude(map_type="Pa")
        )
        image_pks += list(qs.values_list("pk", flat=True))
    return image_pks


# Returns number of total comparisons, with public, not thresholded maps
def count_existing_comparisons(pk1):
    return get_existing_comparisons(pk1).count()


# Returns number of total comparisons possible
def count_possible_comparisons(pk1):
    # Comparisons possible for one pk is the number of other pks
    count_statistic_maps = (
        Item.objects.statmaps().filter(is_thresholded=False, collection__private=False)
        .exclude(pk=pk1)
        .exclude(analysis_level="S")
        .count()
    )
    count_nidm_maps = (
        Item.objects.nidm_statmaps().filter(is_thresholded=False, collection__private=False)
        .exclude(pk=pk1)
        .exclude(analysis_level="S")
        .count()
    )
    return count_statistic_maps + count_nidm_maps


# Returns image comparisons still processing for a given pk
def count_processing_comparisons(pk1):
    return count_possible_comparisons(pk1) - count_existing_comparisons(pk1)


# Returns existing comparisons for specific pk, or entire database
def get_existing_comparisons(pk1):
    possible_images_to_compare_with_pks = get_images_to_compare_with(pk1) + [pk1]
    comparisons = Comparison.objects.filter(Q(image1__pk=pk1) | Q(image2__pk=pk1))
    comparisons = comparisons.filter(
        image1__id__in=possible_images_to_compare_with_pks,
        image2__id__in=possible_images_to_compare_with_pks,
    )
    comparisons = comparisons.exclude(image1__pk=pk1, image2__pk=pk1)
    return comparisons


# Returns existing comparisons for specific pk in pd format for
def get_similar_images(pk, max_results=100):
    comparisons = (
        get_existing_comparisons(pk)
        .extra(select={"abs_score": "abs(similarity_score)"})
        .order_by("-abs_score")[0:max_results]
    )  # "-" indicates descending

    comparisons_pd = pd.DataFrame(
        {
            "image_id": [],
            "score": [],
            "png_img_path": [],
            "tag": [],
            "name": [],
            "collection_name": [],
        }
    )

    for comp in comparisons:
        # pick the image we are comparing with
        image = [image for image in [comp.image1, comp.image2] if image.id != pk][0]
        if image.kind == Item.STATMAP and image.thumbnail:
            df = pd.DataFrame(
                {
                    "image_id": [image.pk],
                    "score": [comp.similarity_score],
                    "png_img_path": [image.get_thumbnail_url()],
                    "tag": [[str(image.map_type)]],
                    "name": [image.name],
                    "collection_name": [image.collection.name],
                }
            )
        comparisons_pd = comparisons_pd.append(df, ignore_index=True)

    return comparisons_pd


