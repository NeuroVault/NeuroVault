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
from datetime import datetime,date
import cortex
import pytz
from zipfile import ZipFile
import rdflib
from neurovault.apps.statmaps.nidm import StatisticMap

def get_all_instances(model_class, graph, nidm_file_handle, collection):
    query = """
prefix prov: <http://www.w3.org/ns/prov#>
prefix nidm: <http://www.incf.org/ns/nidash/nidm#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?uri WHERE {
 ?uri a %s .
}
"""%model_class.nidm_identifier
    results = graph.query(query)
    uris = set([])
    for _, row in enumerate(results.bindings):
        uris.add(str(row["uri"]))
        
    instances = []
    for uri in uris:
        instance = model_class.create_from_nidm(uri, graph, nidm_file_handle, collection=collection)
        instance.save()
        instances.append(instance)
        
    return instances

def parse_nidm_results(nidm_file, collection):
    z_fp = ZipFile(nidm_file)
    root = z_fp.infolist()[0].filename
    nidm_filename = root + "nidm.ttl"
    nidm_fp = z_fp.open(nidm_filename, "r")
    nidm_content = nidm_fp.read()
    #A tiny SPM12 factual inaccuracy
    nidm_content = nidm_content.replace("nidm_NoiseModel", "nidm:NoiseModel")
    
    nidm_graph = rdflib.Graph()
    nidm_graph.parse(data=nidm_content, format='turtle')
    
    stat_maps = get_all_instances(StatisticMap, nidm_graph, z_fp, collection)
    for stat_map in stat_maps:
        stat_map.save()
    return stat_maps


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
