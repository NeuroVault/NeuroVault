import os
import tempfile
import subprocess
import shutil
import numpy as np
import string
import random
from .models import Collection
from neurovault import settings
import urllib2
from lxml import etree
import datetime


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


def generate_pycortex_dir(nifti_file, output_dir, transform_name):
    os.environ["XDG_CONFIG_HOME"] = settings.PYCORTEX_CONFIG_HOME
    os.environ["FREESURFER_HOME"] = "/opt/freesurfer"
    os.environ["SUBJECTS_DIR"] = os.path.join(os.environ["FREESURFER_HOME"],"subjects")
    os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"

    import cortex
    temp_dir = tempfile.mkdtemp(dir=settings.PYCORTEX_CONFIG_HOME)
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
        tklog = open(os.path.join(temp_dir,'tkreg2.log'),'w')
        exit_code = subprocess.call([os.path.join(os.environ['FREESURFER_HOME'],
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
                                     mni_mat],stdout=tklog)
        if exit_code:
            raise RuntimeError("tkregister2 exited with status %d" % exit_code)
        x = np.loadtxt(mni_mat)

        xfm = cortex.xfm.Transform.from_fsl(x, nifti_file, reference)
        xfm.save("fsaverage", transform_name,'coord')
        dv = cortex.Volume(nifti_file, "fsaverage", transform_name,
                         cmap="RdBu_r", dfilter="trilinear")

        # range excludes max/min 1%, evaluated at json output runtime
        # Dataview.to_json(): np.percentile(np.nan_to_num(self.data), 99)]

        use_vmax = dv.to_json()['vmax'][0]
        dv.vmin = use_vmax * -1
        dv.vmax = use_vmax

        cortex.webgl.make_static(output_dir, dv)
    finally:
        pass
        #shutil.rmtree(temp_dir)


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
    authors = [author.findall('given_name')[0].text + " " + author.findall('surname')[0].text for author in doc.findall('.//contributors/person_name')]
    if len(authors) > 1:
        authors = ", ".join(authors[:-1]) + " and " + authors[-1]
    else:
        authors = authors[0]
    url = doc.findall('.//doi_data/resource')[0].text
    date_node = doc.findall('.//publication_date')[0]
    if len(date_node.findall('day')) > 0:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         int(date_node.findall('month')[0].text),
                                         int(date_node.findall('day')[0].text))
    elif len(date_node.findall('month')) > 0:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         int(date_node.findall('month')[0].text),
                                         1)
    else:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         1,
                                         1)
    return title, authors, url, publication_date, journal_name
