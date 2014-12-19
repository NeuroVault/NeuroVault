import os
import tempfile
import zipfile
from fnmatch import fnmatch
import rdflib
from rdflib.plugins.parsers.notation3 import BadSyntax
from collections import Counter
from urlparse import urlparse


class NIDMUpload:

    def __init__(self, zip_path,tmp_dir=None,load=True):
        self.path = zip_path
        self.provn_path = ''
        self.ttl_path = ''
        self.ttl_relpath = ''
        self.workdir = tempfile.mkdtemp() if tmp_dir is None else tmp_dir
        self.zipobj = None
        self.raw_ttl = ''
        self.valid_ttl = False
        self.unzipped = False
        self.contrasts = []
        self.statmaps = []

        if load:
            self.get_statmaps()

    class ParseException(Exception):
        pass

    class NoStatMapsException(Exception):
        pass

    def parse_metafiles(self,extract_ttl=False):
        try:
            self.zipobj = zipfile.ZipFile(self.path)
        except Exception:
            raise self.ParseException("Unable to read the zip file.")
        metafiles = {}
        for ext in ['.ttl','.provn']:
            metafiles[ext] = [v for v in self.zipobj.infolist()
                              if fnmatch(v.filename, '*'+ext)
                              # strip terrible random metadata folder on Mac
                              and not fnmatch(v.filename,'__MACOSX*')
                              ]
            if len(metafiles[ext]) > 1:
                raise self.ParseException(
                        "Detected more than one {0} file in zip.".format(ext))
            if not metafiles[ext]:
                raise self.ParseException(
                        "No {0} file found in zip.".format(ext))

        self.ttl_path = metafiles['.ttl'][0].filename
        self.provn_path = metafiles['.provn'][0].filename
        self.raw_ttl = self.zipobj.read(metafiles['.ttl'][0])
        self.ttl_relpath = self.parse_ttl_relative_path(metafiles['.ttl'][0].filename)

        # fix incorrect property format in earlier versions of SPM12 output
        self.raw_ttl = self.raw_ttl.replace("nidm_NoiseModel", "nidm:NoiseModel")

        return self.raw_ttl if extract_ttl else True

    def parse_contrasts(self):
        query = """
        prefix prov: <http://www.w3.org/ns/prov#>
        prefix nidm: <http://www.incf.org/ns/nidash/nidm#>
        prefix spm: <http://www.incf.org/ns/nidash/spm#>
        prefix fsl: <http://www.incf.org/ns/nidash/fsl#>

        SELECT ?contrastName ?statFile ?statType WHERE {
         ?cid a nidm:ContrastMap ;
              nidm:contrastName ?contrastName ;
              prov:atLocation ?cfile .
         ?cea a nidm:ContrastEstimation .
         ?cid prov:wasGeneratedBy ?cea .
         ?sid a nidm:StatisticMap ;
              nidm:statisticType ?statType ;
              prov:atLocation ?statFile .
        }
        """
        nidm_g = rdflib.Graph()

        try:
            nidm_g.parse(data=self.raw_ttl, format='turtle')
            self.valid_ttl = True
        except BadSyntax:
            raise self.ParseException("RDFLib was unable to parse the .ttl file.")

        c_results = nidm_g.query(query)
        for row in c_results.bindings:
            c_row = {}
            for key, val in sorted(row.items()):
                c_row[str(key)] = val.decode()
            self.contrasts.append(c_row)
        return self.contrasts

    def unpack_nidm_zip(self):
        if not self.ttl_path or not self.provn_path:
            self.parse_metafiles()
        if not self.contrasts:
            self.parse_contrasts()

        try:
            self.zipobj.extractall(path=self.workdir)
            self.unzipped = True
        except Exception,e:
            raise self.ParseException("Unable to unzip: %s" % e)

    def get_statmaps(self):
        if not self.unzipped:
            self.unpack_nidm_zip()
        if not self.contrasts:
            raise self.NoStatMapsException("No eligible data found in this file")

        incidences = Counter([v['contrastName'] for v in self.contrasts])
        for contrast in self.contrasts:
            map = {'name':contrast['contrastName'],
                   'type':self.parse_statmap_type(contrast['statType']),
                   'file':self.validate_statmap_uri(contrast)}

            # Make the contrast names unique
            if incidences[contrast['contrastName']] > 1:
                map['name'] = self.get_unique_mapname(contrast)
            self.statmaps.append(map)
        return self.statmaps

    def validate_statmap_uri(self,contrast):
        rel_path = self.uri_to_path(contrast['statFile'])
        path = self.expand_path(rel_path)
        return path
        if not os.path.exists(path):
            raise self.ParseException(
                    "Unable to find image file for map {0}".format(
                        self.parse_statmap_type(contrast['statType'])))
        return path

    def expand_path(self,path):
        for sep in ['.','/']:
            if path.startswith(sep):
                path = path.replace(sep,self.ttl_relpath,1)
        return os.path.join(self.workdir,path)

    @classmethod
    def uri_to_path(self,map_uri):
        # NIDM schema namespace url, or arbitrary string just in case
        uri = urlparse(map_uri)
        if not uri.path or uri.scheme != 'file':
            raise self.ParseException("Invalid location for statistic map file.")
        return '{0}{1}'.format(uri.netloc,uri.path)

    @classmethod
    def get_unique_mapname(self,contrast):
        type = self.parse_statmap_type(contrast['statType'])
        return '{0} {1}'.format(contrast['contrastName'], type)

    @staticmethod
    def parse_statmap_type(stattype):
        return urlparse(stattype).fragment or stattype

    @staticmethod
    def parse_ttl_relative_path(path):
        relpath = os.path.dirname(path)
        # some platforms will have relative path in the file list
        # strip all combinations of ./, ../, ., etc
        for sep in ['.','.','/']:
            if relpath.startswith(sep):
                relpath = relpath.replace(sep,'',1)
        return relpath

    @staticmethod
    def print_sparql_results(res):
        for idx, row in enumerate(res.bindings):
            rowfmt = []
            print "Item %d" % idx
            for key, val in sorted(row.items()):
                rowfmt.append('%s-->%s' % (key, val.decode()))
            print '\n'.join(rowfmt)

