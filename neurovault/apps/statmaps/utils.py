import errno
import os
import pickle
import random
import shutil
import string
import subprocess
import tempfile
import urllib.request, urllib.error, urllib.parse
import zipfile
from ast import literal_eval
from datetime import datetime, date
from subprocess import CalledProcessError
import gzip
import tarfile
import re

import cortex
import nibabel as nib
import pandas as pd
import numpy as np
import pytz
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from lxml import etree
from fnmatch import fnmatch

from neurovault.apps.statmaps.models import (
    Collection,
    NIDMResults,
    StatisticMap,
    Comparison,
    NIDMResultStatisticMap,
    BaseStatisticMap,
    get_possible_templates,
    DEFAULT_TEMPLATE,
    Atlas,
)




# see CollectionRedirectMiddleware
class HttpRedirectException(Exception):
    pass


def split_filename(fname):
    """Split a filename into parts: path, base filename and extension.

    Parameters
    ----------
    fname : str
        file or path name

    Returns
    -------
    pth : str
        base path from fname
    fname : str
        filename from fname, without extension
    ext : str
        file extension from fname

    Examples
    --------
    >>> pth, fname, ext = split_filename('/home/data/subject.nii.gz')
    >>> pth
    '/home/data'

    >>> fname
    'subject'

    >>> ext
    '.nii.gz'

    """

    special_extensions = [".nii.gz", ".tar.gz"]

    if fname and fname.endswith(os.path.sep):
        fname = fname[:-1]

    pth, fname = os.path.split(fname)

    ext = None
    for special_ext in special_extensions:
        ext_len = len(special_ext)
        if (len(fname) > ext_len) and (fname[-ext_len:].lower() == special_ext.lower()):
            ext = fname[-ext_len:]
            fname = fname[:-ext_len]
            break
    if not ext:
        fname, ext = os.path.splitext(fname)

    return pth, fname, ext


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
                + e.output
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


def generate_url_token(length=8):
    chars = string.ascii_uppercase
    token = "".join(random.choice(chars) for v in range(length))
    if Collection.objects.filter(private_token=token).exists():
        return generate_url_token()
    else:
        return token


def get_paper_properties(doi):
    xmlurl = "http://doi.crossref.org/servlet/query"
    xmlpath = (
        xmlurl
        + "?pid=k.j.gorgolewski@sms.ed.ac.uk&format=unixref&id="
        + urllib.parse.quote(doi)
    )
    print(xmlpath)
    xml_str = urllib.request.urlopen(xmlpath).read()
    doc = etree.fromstring(xml_str)
    if len(doc.getchildren()) == 0 or len(doc.findall(".//crossref/error")) > 0:
        raise Exception("DOI %s was not found" % doi)
    journal_name = doc.findall(".//journal/journal_metadata/full_title")[0].text
    title = doc.findall(".//title")[0].text
    authors = [
        author.findall("given_name")[0].text + " " + author.findall("surname")[0].text
        for author in doc.findall(".//contributors/person_name")
    ]
    if len(authors) > 1:
        authors = ", ".join(authors[:-1]) + " and " + authors[-1]
    else:
        authors = authors[0]
    url = doc.findall(".//doi_data/resource")[0].text
    date_node = doc.findall(".//publication_date")[0]
    if len(date_node.findall("day")) > 0:
        publication_date = date(
            int(date_node.findall("year")[0].text),
            int(date_node.findall("month")[0].text),
            int(date_node.findall("day")[0].text),
        )
    elif len(date_node.findall("month")) > 0:
        publication_date = date(
            int(date_node.findall("year")[0].text),
            int(date_node.findall("month")[0].text),
            1,
        )
    else:
        publication_date = date(int(date_node.findall("year")[0].text), 1, 1)
    return title, authors, url, publication_date, journal_name


def get_file_ctime(fpath):
    return datetime.fromtimestamp(os.path.getctime(fpath), tz=pytz.utc)


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


def send_email_notification(notif_type, subject, users, tpl_context=None):
    email_from = "NeuroVault <do_not_reply@neurovault.org>"
    plain_tpl = os.path.join("email", "%s.txt" % notif_type)
    html_tpl = os.path.join("email", "%s.html" % notif_type)

    for user in users:
        context = dict(list(tpl_context.items()) + [("username", user.username)])
        dest = user.email
        text_content = render_to_string(plain_tpl, context)
        html_content = render_to_string(html_tpl, context)
        msg = EmailMultiAlternatives(subject, text_content, email_from, [dest])
        msg.attach_alternative(html_content, "text/html")
        msg.send()


def detect_4D(nii):
    shape = nii.shape
    return (len(shape) == 4 and shape[3] > 1 and shape[3] < 20) or (
        len(shape) == 5 and shape[3] == 1
    )


def get_afni_subbrick_labels(nii):
    # AFNI header is nifti1 header extension 4
    # http://nifti.nimh.nih.gov/nifti-1/AFNIextension1

    extensions = getattr(nii.header, "extensions", [])
    header = [ext for ext in extensions if ext.get_code() == 4]
    if not header:
        return []

    # slice labels delimited with '~'
    # <AFNI_atr atr_name="BRICK_LABS" >
    #   "SetA-SetB_mean~SetA-SetB_Zscr~SetA_mean~SetA_Zscr~SetB_mean~SetB_Zscr"
    # </AFNI_atr>
    retval = []
    try:
        tree = etree.fromstring(header[0].get_content())
        lnode = [
            v
            for v in tree.findall(".//AFNI_atr")
            if v.attrib["atr_name"] == "BRICK_LABS"
        ]

        # header xml is wrapped in string literals

        if lnode:
            retval += literal_eval(lnode[0].text.strip()).split("~")
    except:
        pass
    return retval


def split_4D_to_3D(nii, with_labels=True, tmp_dir=None):
    outpaths = []
    ext = ".nii.gz"
    base_dir, name = os.path.split(nii.get_filename())
    out_dir = tmp_dir or base_dir
    fname = name.replace(ext, "")

    slices = np.split(np.asanyarray(nii.dataobj), nii.shape[-1], len(nii.shape) - 1)
    labels = get_afni_subbrick_labels(nii)
    for n, slice in enumerate(slices):
        nifti = nib.Nifti1Image(np.squeeze(slice), nii.header.get_best_affine())
        layer_nm = labels[n] if n < len(labels) else "(volume %s)" % (n + 1)
        outpath = os.path.join(out_dir, "%s__%s%s" % (fname, layer_nm, ext))
        nib.save(nifti, outpath)
        if with_labels:
            outpaths.append((layer_nm, outpath))
        else:
            outpaths.append(outpath)
    return outpaths


def memory_uploadfile(new_file, fname, old_file):
    cfile = ContentFile(open(new_file, "rb").read())
    content_type = (getattr(old_file, "content_type", False) or "application/x-gzip",)
    charset = getattr(old_file, "charset", False) or None

    return InMemoryUploadedFile(cfile, "file", fname, content_type, cfile.size, charset)


# Atomic save for a transform pickle file - save to tmp directory and rename
def save_pickle_atomically(pkl_data, filename, directory=None):
    # Give option to save to specific (not /tmp) directory
    if directory == None:
        tmp_file = tempfile.mktemp()
    else:
        tmp_file = tempfile.mktemp(dir=directory)

    filey = open(tmp_file, "wb")
    # We don't want pickle to close the file
    pickle_text = pickle.dumps(pkl_data)
    filey.writelines(pickle_text)
    # make sure that all data is on disk
    filey.flush()
    os.fsync(filey.fileno())
    filey.close()
    os.rename(tmp_file, filename)


def populate_nidm_results(request, collection):
    inst = NIDMResults(collection=collection)
    # resolves a odd circular import issue
    nidmr_form = NIDMResults.get_form_class()
    request.POST["name"] = "NIDM"
    request.POST["description"] = "NIDM Results"
    request.POST["collection"] = collection.pk
    request.FILES["zip_file"] = request.FILES["file"]
    form = nidmr_form(request.POST, request.FILES, instance=inst)
    if form.is_valid():
        form.save()
        return form.instance
    else:
        return None


def populate_feat_directory(request, collection, existing_dir=None):
    from nidmfsl.fsl_exporter.fsl_exporter import FSLtoNIDMExporter

    tmp_dir = tempfile.mkdtemp() if existing_dir is None else existing_dir
    exc = ValidationError

    try:
        if existing_dir is None:
            zip = zipfile.ZipFile(request.FILES["file"])
            zip.extractall(path=tmp_dir)

        rootpaths = [
            v
            for v in os.listdir(tmp_dir)
            if not v.startswith(".") and not v.startswith("__MACOSX")
        ]
        if not rootpaths:
            raise exc("No contents found in the FEAT directory.")
        subdir = os.path.join(tmp_dir, rootpaths[0])
        feat_dir = subdir if len(rootpaths) == 1 and os.path.isdir(subdir) else tmp_dir
    except:
        raise exc("Unable to unzip the FEAT directory: \n{0}.".format(get_traceback()))
    try:
        fslnidm = FSLtoNIDMExporter(feat_dir=feat_dir, version="1.2.0")
        fslnidm.parse()
        nidm_file = fslnidm.export()
    except:
        raise exc("Unable to parse the FEAT directory: \n{0}.".format(get_traceback()))

    if not os.path.exists(nidm_file):
        raise exc("Unable find nidm export of FEAT directory.")

    try:
        fh = open(nidm_file, "r")
        request.FILES["file"] = InMemoryUploadedFile(
            ContentFile(fh.read()),
            "file",
            fh.name.split("/")[-1],
            "application/zip",
            os.path.getsize(nidm_file),
            "utf-8",
        )

    except:
        raise exc(
            "Unable to convert NIDM results for NeuroVault: \n{0}".format(
                get_traceback()
            )
        )
    else:
        return populate_nidm_results(request, collection)
    finally:
        shutil.rmtree(tmp_dir)


def detect_feat_directory(path):
    if not os.path.isdir(path):
        return False
    # detect FEAT directory, check for for stats/, logs/, logs/feat4_post
    for root, dirs, files in os.walk(path):
        if (
            "stats" in dirs
            and "logs" in dirs
            and "design.fsf" in files
            and "feat4_post" in os.listdir(os.path.join(root, "logs"))
        ):
            return True
        else:
            return False


def get_traceback():
    import traceback

    return traceback.format_exc() if settings.DEBUG else ""


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


# checks if map is thresholded
def is_thresholded(nii_obj, thr=0.85):
    data = np.asanyarray(nii_obj.dataobj)
    zero_mask = data == 0
    nan_mask = np.isnan(data)
    missing_mask = zero_mask | nan_mask
    ratio_bad = float(missing_mask.sum()) / float(missing_mask.size)
    if ratio_bad > thr:
        return (True, ratio_bad)
    else:
        return (False, ratio_bad)


# checks if map is a parcellation or ROI/mask
def infer_map_type(nii_obj):
    data = np.asanyarray(nii_obj.dataobj)
    zero_mask = data == 0
    nan_mask = np.isnan(data)
    missing_mask = zero_mask | nan_mask
    unique_values = np.unique(data[np.logical_not(missing_mask)])
    if len(unique_values) == 1:
        map_type = BaseStatisticMap.R
    elif len(unique_values) > 1200:
        map_type = BaseStatisticMap.OTHER
    else:
        map_type = BaseStatisticMap.Pa
        for val in unique_values:
            if not (
                isinstance(val, np.integer)
                or (isinstance(val, np.floating) and float(val).is_integer())
            ):
                map_type = BaseStatisticMap.OTHER
                break
            if (data == val).sum() == 1:
                map_type = BaseStatisticMap.OTHER
                break
    return map_type


import nibabel as nb
from nilearn.image import resample_img


def not_in_mni(nii, target_template_image=DEFAULT_TEMPLATE, plot=False):
    this_path = os.path.abspath(os.path.dirname(__file__))

    POSSIBLE_TEMPLATES = get_possible_templates()
    mask_path = POSSIBLE_TEMPLATES[target_template_image]["mask"]
    if mask_path == None:
        return False, 100.0, 100.0

    mask_nii = nb.load(os.path.join(this_path, "static", "anatomical", mask_path))

    # resample to the smaller one
    if np.prod(nii.shape) > np.prod(mask_nii.shape):
        nan_mask = np.isnan(np.asanyarray(nii.dataobj))
        if nan_mask.sum() > 0:
            np.asanyarray(nii.dataobj)[nan_mask] = 0
        nii = resample_img(
            nii,
            target_affine=mask_nii.affine,
            target_shape=mask_nii.shape,
            interpolation="nearest",
        )
    else:
        mask_nii = resample_img(
            mask_nii,
            target_affine=nii.affine,
            target_shape=nii.shape,
            interpolation="nearest",
        )

    brain_mask = np.asanyarray(mask_nii.dataobj) > 0
    excursion_set = np.logical_not(
        np.logical_or(np.asanyarray(nii.dataobj) == 0, np.isnan(np.asanyarray(nii.dataobj)))
    )

    # deals with AFNI files
    if len(excursion_set.shape) == 5:
        excursion_set = excursion_set[:, :, :, 0, 0]
    # deal with 4D files
    elif len(excursion_set.shape) == 4:
        excursion_set = excursion_set[:, :, :, 0]
    in_brain_voxels = np.logical_and(excursion_set, brain_mask).sum()
    out_of_brain_voxels = np.logical_and(
        excursion_set, np.logical_not(brain_mask)
    ).sum()

    perc_mask_covered = in_brain_voxels / float(brain_mask.sum()) * 100.0
    if np.isnan(perc_mask_covered):
        perc_mask_covered = 0
    perc_voxels_outside_of_mask = (
        out_of_brain_voxels / float(excursion_set.sum()) * 100.0
    )

    if perc_mask_covered > 50:
        if perc_mask_covered < 90 and perc_voxels_outside_of_mask > 20:
            ret = True
        else:
            ret = False
    elif perc_mask_covered == 0:
        ret = True
    elif perc_voxels_outside_of_mask > 50:
        ret = True
    else:
        ret = False

    return ret, perc_mask_covered, perc_voxels_outside_of_mask


# infers subject species based on target_template_image
def infer_subject_species(target_template_image=DEFAULT_TEMPLATE):
    POSSIBLE_TEMPLATES = get_possible_templates()
    return POSSIBLE_TEMPLATES[target_template_image]["species"]


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
    from neurovault.apps.statmaps.models import Image

    try:
        img = Image.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return False

    if (
        img.polymorphic_ctype.model in ["image", "atlas"]
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
    from neurovault.apps.statmaps.models import (
        StatisticMap,
        NIDMResultStatisticMap,
        Image,
    )

    # if the map in question is invalid do not generate any comparisons
    if not is_search_compatible(pk1):
        return []

    img = Image.objects.get(pk=pk1)
    image_pks = []
    for cls in [StatisticMap, NIDMResultStatisticMap]:
        qs = cls.objects.filter(
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
        StatisticMap.objects.filter(is_thresholded=False, collection__private=False)
        .exclude(pk=pk1)
        .exclude(analysis_level="S")
        .count()
    )
    count_nidm_maps = (
        NIDMResultStatisticMap.objects.filter(
            is_thresholded=False, collection__private=False
        )
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
        if hasattr(image, "map_type") and image.thumbnail:
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


def extract_archive(uploaded_file, destination_dir):
    """
    Extracts the contents of an uploaded archive (.zip, .gz) 
    into the given `destination_dir`.
    Raises an exception if the archive type is unsupported.
    """
    archive_name = uploaded_file.name
    _, archive_ext = os.path.splitext(archive_name)

    if archive_ext == ".zip":
        with zipfile.ZipFile(uploaded_file, 'r') as zf:
            zf.extractall(destination_dir)
    elif archive_ext == ".gz":
        # `uploaded_file` is a Django UploadedFile object
        uploaded_file.open()
        with tarfile.TarFile(fileobj=gzip.GzipFile(fileobj=uploaded_file.file, mode="r"), mode="r") as tf:
            tf.extractall(destination_dir)
    else:
        raise ValueError(f"Unsupported archive type: {archive_ext}")


def collect_nifti_files(root_directory, allowed_extensions):
    """
    Walks through the `root_directory` collecting:
    - standard NIfTI files
    - .gfeat or .feat directories
    - .xml for atlas info
    Returns a tuple of (nifti_files, atlases) or a custom object with everything you need.
    """
    nifti_files = []
    atlases = {}

    for root, subdirs, filenames in os.walk(root_directory):
        
        # detect_feat_directory, detect_4D, and split_4D_to_3D are presumably 
        # your own existing helper functions.

        if detect_feat_directory(root):
            populate_feat_directory(...)  # or store this for later if needed
            # Prevent descending further into this sub-directory
            subdirs[:] = []
            filenames = []
            continue

        # .gfeat parent dir under cope*.feat should not be added as statmaps
        if root.endswith(".gfeat"):
            filenames = []
            continue

        # Filter out hidden files
        filenames = [f for f in filenames if not f.startswith(".")]

        for fname in sorted(filenames):
            name, ext = splitext_nii_gz(fname)
            file_path = os.path.join(root, fname)

            # Atlas XML detection
            if ext == ".xml":
                # parse XML for atlas
                atlas = parse_atlas_xml(file_path)
                atlases.update(atlas)
                continue

            # Normal NIfTI detection
            if ext in allowed_extensions:
                nii = nib.load(file_path)
                if detect_4D(nii):
                    nifti_files.extend(split_4D_to_3D(nii))
                else:
                    nifti_files.append((fname, file_path))

    return nifti_files, atlases


def parse_atlas_xml(xml_path):
    """
    Extracts atlas paths from an XML file. Returns a dict 
    mapping the NIfTI path -> corresponding .xml path.
    """
    from xml.dom import minidom
    dom = minidom.parse(xml_path)
    atlas_map = {}
    for atlas in dom.getElementsByTagName("imagefile"):
        path_str, base = os.path.split(atlas.lastChild.nodeValue)
        nifti_name = os.path.join(path_str, base).lstrip("/")
        atlas_map[nifti_name] = xml_path
    return atlas_map


def create_image_from_nifti(
    collection,
    file_label,
    file_path,
    atlas_xml_path=None
):
    """
    Creates and returns an Image model instance (StatisticMap or Atlas) 
    from a local NIfTI file. Handles:
      - 3D shape checking
      - T/F detection
      - .nii.gz conversion
      - SPM naming
    """
    # 1) Load NIfTI, check shape, handle 3D vs 4D
    nii = nib.load(file_path)
    shape = nii.shape
    if len(shape) > 3 and shape[3] > 1:
        # Skip or raise if not 3D
        raise ValueError(f"Skipping {file_label}: 4D file detected.")

    # 2) Detect map type
    map_type = detect_stat_map_type(file_path)

    # 3) Convert to .nii.gz (or squeeze dimensions)
    name_without_ext = os.path.splitext(os.path.basename(file_path))[0]
    new_img = squeeze_and_save_as_nii_gz(nii, name_without_ext)
    
    # 4) Create model instance
    spaced_name = name_without_ext.replace("_", " ").replace("-", " ")
    if atlas_xml_path:
        new_image = Atlas(name=spaced_name, collection=collection)
        with open(atlas_xml_path, "rb") as xml_file:
            new_image.label_description_file = ContentFile(
                xml_file.read(), 
                name=name_without_ext + ".xml"
            )
    else:
        new_image = StatisticMap(
            name=spaced_name, is_valid=False, collection=collection)

        new_image.map_type = map_type

    # 5) Attach .nii.gz file
    new_image.file = new_img
    new_image.save()
    return new_image


def detect_stat_map_type(file_path):
    """
    Returns T, F, or OTHER based on filename pattern 
    (SPM naming convention).
    """
    Tregexp = re.compile("spmT.*", re.IGNORECASE)
    Fregexp = re.compile("spmF.*", re.IGNORECASE)

    basename = os.path.basename(file_path)
    if Tregexp.match(basename):
        return StatisticMap.T
    elif Fregexp.match(basename):
        return StatisticMap.F
    else:
        return StatisticMap.OTHER


def squeeze_and_save_as_nii_gz(nii, base_name):
    """
    Squeezes single-dimensional axes, ensures .nii.gz extension,
    returns a Django ContentFile ready for saving.
    """
    import tempfile
    import shutil

    # Squeeze dimensions
    squeezed_data = np.squeeze(np.asanyarray(nii.dataobj))
    squeezed_nii = nib.Nifti1Image(squeezed_data, nii.affine, nii.header)

    # Save temporarily
    temp_dir = tempfile.mkdtemp()
    out_path = os.path.join(temp_dir, base_name + ".nii.gz")
    nib.save(squeezed_nii, out_path)

    # Wrap in a Django ContentFile
    try:
        with open(out_path, "rb") as f:
            content = ContentFile(f.read(), name=base_name + ".nii.gz")
    finally:
        shutil.rmtree(temp_dir)

    return content


def extract_multiple_files(file_list, path_list, destination_dir):
    """
    Copies files from `file_list` into the correct relative paths 
    under `destination_dir`.
    
    - file_list: an iterable of Django UploadedFile objects
    - path_list: a parallel iterable of relative paths (from request.POST)
    """
    for uploaded_file, relative_path in zip(file_list, path_list):
        # If it’s .nidm.zip, handle separately (or skip if you want)
        if fnmatch(uploaded_file.name, "*.nidm.zip"):
            # Return something or handle logic externally
            continue

        # Create all missing directories in the path
        final_dir, _ = os.path.split(os.path.join(destination_dir, relative_path))
        mkdir_p(final_dir)

        filename = os.path.join(final_dir, uploaded_file.name)
        with open(filename, "wb") as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
