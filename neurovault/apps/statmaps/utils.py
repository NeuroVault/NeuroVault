import os
import tempfile
import subprocess
import shutil
import numpy as np
import string
import random
from .models import Collection, NIDMResults
from neurovault import settings
import urllib2
from lxml import etree
from datetime import datetime,date
import cortex
import pytz
import errno
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import nibabel as nib
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from ast import literal_eval
from subprocess import CalledProcessError
from django.core.exceptions import ValidationError
import zipfile


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
    >>> from nipype.utils.filemanip import split_filename
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
        if (len(fname) > ext_len) and \
                (fname[-ext_len:].lower() == special_ext.lower()):
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
        reference = os.path.join(os.environ['FREESURFER_HOME'],
                                 'subjects', 'fsaverage', 'mri', 'brain.nii.gz')
        shutil.copy(os.path.join(os.environ['FREESURFER_HOME'],
                                 'average', 'mni152.register.dat'), new_mni_dat)
        #this avoids problems with white spaces in file names
        tmp_link = os.path.join(temp_dir, "tmp.nii.gz")
        os.symlink(nifti_file, tmp_link)
        try:
            subprocess.check_output([os.path.join(os.environ['FREESURFER_HOME'],
                                         "bin", "tkregister2"),
                                         "--mov",
                                         tmp_link,
                                         "--targ",
                                         reference,
                                         "--reg",
                                         new_mni_dat,
                                         "--noedit",
                                         "--nofix",
                                         "--fslregout",
                                         mni_mat])
        except CalledProcessError, e:
            raise RuntimeError(str(e.cmd) + " returned code " +
                               str(e.returncode) + " with output " + e.output)

        x = np.loadtxt(mni_mat)
        xfm = cortex.xfm.Transform.from_fsl(x, nifti_file, reference)
        xfm.save("fsaverage", transform_name,'coord')

        dv = cortex.Volume(nifti_file, "fsaverage", transform_name, cmap="RdBu_r",
                    dfilter="trilinear", description=image.description)

        # default colormap range evaluated only at runtime (Dataview.to_json())
        # excludes max/min 1% : np.percentile(np.nan_to_num(self.data), 99)
        use_vmax = dv.to_json()['vmax'][0]
        dv.vmin = use_vmax * -1
        dv.vmax = use_vmax

        return dv

    finally:
        shutil.rmtree(temp_dir)


def generate_pycortex_static(volumes, output_dir):
    app_path = os.path.abspath(os.path.dirname(__file__))
    tpl_path = os.path.join(app_path, 'templates/pycortex/dataview.html')
    ds = cortex.Dataset(**volumes)
    cortex.webgl.make_static(output_dir, ds, template=tpl_path, html_embed=False,
                             copy_ctmfiles=False)


def generate_url_token(length=8):
    chars = string.ascii_uppercase
    token = ''.join(random.choice(chars) for v in range(length))
    if Collection.objects.filter(private_token=token).exists():
        return generate_url_token()
    else:
        return token


def get_paper_properties(doi):
    xmlurl = 'http://doi.crossref.org/servlet/query'
    xmlpath = xmlurl + '?pid=k.j.gorgolewski@sms.ed.ac.uk&format=unixref&id=' + urllib2.quote(doi)
    print xmlpath
    xml_str = urllib2.urlopen(xmlpath).read()
    doc = etree.fromstring(xml_str)
    if len(doc.getchildren()) == 0 or len(doc.findall('.//crossref/error')) > 0:
        raise Exception("DOI %s was not found" % doi)
    journal_name = doc.findall(".//journal/journal_metadata/full_title")[0].text
    title = doc.findall('.//title')[0].text
    authors = [author.findall('given_name')[0].text + " " + author.findall('surname')[0].text
            for author in doc.findall('.//contributors/person_name')]
    if len(authors) > 1:
        authors = ", ".join(authors[:-1]) + " and " + authors[-1]
    else:
        authors = authors[0]
    url = doc.findall('.//doi_data/resource')[0].text
    date_node = doc.findall('.//publication_date')[0]
    if len(date_node.findall('day')) > 0:
        publication_date = date(int(date_node.findall('year')[0].text),
                                int(date_node.findall('month')[0].text),
                                int(date_node.findall('day')[0].text))
    elif len(date_node.findall('month')) > 0:
        publication_date = date(int(date_node.findall('year')[0].text),
                                int(date_node.findall('month')[0].text),
                                1)
    else:
        publication_date = date(int(date_node.findall('year')[0].text),
                                1,
                                1)
    return title, authors, url, publication_date, journal_name


def get_file_ctime(fpath):
    return datetime.fromtimestamp(os.path.getctime(fpath),tz=pytz.utc)


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
    email_from = 'NeuroVault <do_not_reply@neurovault.org>'
    plain_tpl = os.path.join('email','%s.txt' % notif_type)
    html_tpl = os.path.join('email','%s.html' % notif_type)

    for user in users:
        context = dict(tpl_context.items() + [('username', user.username)])
        dest = user.email
        text_content = render_to_string(plain_tpl,context)
        html_content = render_to_string(html_tpl,context)
        msg = EmailMultiAlternatives(subject, text_content, email_from, [dest])
        msg.attach_alternative(html_content, "text/html")
        msg.send()


def detect_afni4D(nii_file):
    # don't split afni files with no subbricks
    return bool(len(get_afni_subbrick_labels(nii_file)) > 1)


def get_afni_subbrick_labels(nii_file):
    # AFNI header is nifti1 header extension 4
    # http://nifti.nimh.nih.gov/nifti-1/AFNIextension1

    extensions = getattr(nib.load(nii_file).get_header(), 'extensions', [])
    header = [ext for ext in extensions if ext.get_code() == 4]
    if not header:
        return []

    # slice labels delimited with '~'
    # <AFNI_atr atr_name="BRICK_LABS" >
    #   "SetA-SetB_mean~SetA-SetB_Zscr~SetA_mean~SetA_Zscr~SetB_mean~SetB_Zscr"
    # </AFNI_atr>
    tree = etree.fromstring(header[0].get_content())
    lnode = [v for v in tree.findall('.//AFNI_atr') if v.attrib['atr_name'] == 'BRICK_LABS']

    # header xml is wrapped in string literals
    return [] + literal_eval(lnode[0].text.strip()).split('~')


def split_afni4D_to_3D(nii_file,with_labels=True,tmp_dir=None):
    outpaths = []
    ext = ".nii.gz"
    base_dir, name = os.path.split(nii_file)
    out_dir = tmp_dir or base_dir
    fname = name.replace(ext,'')

    nii = nib.load(nii_file)
    slices = np.split(nii.get_data(), nii.get_shape()[-1], len(nii.get_shape())-1)
    labels = get_afni_subbrick_labels(nii_file)
    for n,slice in enumerate(slices):
        nifti = nib.Nifti1Image(np.squeeze(slice),nii.get_header().get_best_affine())
        layer_nm = labels[n] if n < len(labels) else 'slice_%s' % n
        outpath = os.path.join(out_dir,'%s__%s%s' % (fname,layer_nm,ext))
        nib.save(nifti,outpath)
        if with_labels:
            outpaths.append((layer_nm,outpath))
        else:
            outpaths.append(outpath)
    return outpaths


def memory_uploadfile(new_file, fname, old_file):
    cfile = ContentFile(open(new_file).read())
    content_type = getattr(old_file,'content_type',False) or 'application/x-gzip',
    charset = getattr(old_file,'charset',False) or None

    return InMemoryUploadedFile(cfile, "file", fname,
                                content_type, cfile.size, charset)


def populate_nidm_results(request,collection):
    inst = NIDMResults(collection=collection)
    # resolves a odd circular import issue
    nidmr_form = NIDMResults.get_form_class()
    request.POST['name'] = 'NIDM'
    request.POST['description'] = 'NIDM Results'
    request.POST['collection'] = collection.pk
    request.FILES['zip_file'] = request.FILES['file']
    form = nidmr_form(request.POST,request.FILES,instance=inst)
    if form.is_valid():
        form.save()
    return form.instance


def populate_feat_directory(request,collection,existing_dir=None):
    from nidmfsl.fsl_exporter.fsl_exporter import FSLtoNIDMExporter
    tmp_dir = tempfile.mkdtemp() if existing_dir is None else existing_dir
    exc = ValidationError

    try:
        if existing_dir is None:
            zip = zipfile.ZipFile(request.FILES['file'])
            zip.extractall(path=tmp_dir)

        rootpaths = [v for v in os.listdir(tmp_dir)
                     if not v.startswith('.') and not v.startswith('__MACOSX')]
        if not rootpaths:
            raise exc("No contents found in the FEAT directory.")
        subdir = os.path.join(tmp_dir,rootpaths[0])
        feat_dir = subdir if len(rootpaths) is 1 and os.path.isdir(subdir) else tmp_dir
    except:
        raise exc("Unable to unzip the FEAT directory: \n{0}.".format(get_traceback()))
    try:
        fslnidm = FSLtoNIDMExporter(feat_dir=feat_dir, version="0.2.0")
        fslnidm.parse()
        export_dir = fslnidm.export()
    except:
        raise exc("Unable to parse the FEAT directory: \n{0}.".format(get_traceback()))

    if not os.path.exists(export_dir):
        raise exc("Unable find nidm export of FEAT directory.")

    try:
        if existing_dir is not None:
            dname = os.path.basename(feat_dir)
            suffix = '.nidm.zip' if dname.endswith('feat') else '.feat.nidm.zip'
            destname = dname + suffix
        else:
            destname = request.FILES['file'].name.replace('feat.zip','feat.nidm.zip')
        destpath = os.path.join(tmp_dir,destname)
        nidm_zip = zipfile.ZipFile(destpath, 'w', zipfile.ZIP_DEFLATED)
        rootlen = len(feat_dir) + 1
        for root, dirs, files in os.walk(export_dir):
            for dfile in files:
                filenm = os.path.join(root, dfile)
                nidm_zip.write(filenm, filenm[rootlen:])
        nidm_zip.close()
        fh = open(destpath,'r')
        request.FILES['file'] = InMemoryUploadedFile(
                                    ContentFile(fh.read()), "file", fh.name.split('/')[-1],
                                    "application/zip", os.path.getsize(destpath), "utf-8")

    except:
        raise exc("Unable to convert NIDM results for NeuroVault: \n{0}".format(get_traceback()))
    else:
        return populate_nidm_results(request,collection)
    finally:
        shutil.rmtree(tmp_dir)


def detect_feat_directory(path):
    if not os.path.isdir(path):
        return False
    # detect FEAT directory, check for for stats/, logs/, logs/feat4_post
    for root, dirs, files in os.walk(path):
        if('stats' in dirs and 'logs' in dirs and 'design.fsf' in files
           and 'feat4_post' in os.listdir(os.path.join(root,'logs'))):
            return True
        else:
            return False


def get_traceback():
    import traceback
    return traceback.format_exc() if settings.DEBUG else ''


def get_server_url(request):
    if request.META.get('HTTP_ORIGIN'):
        return request.META['HTTP_ORIGIN']
    urlpref = 'https://' if request.is_secure() else 'http://'
    return '{0}{1}'.format(urlpref,request.META['HTTP_HOST'])
