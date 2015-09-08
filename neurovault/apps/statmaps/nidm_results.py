import os
import tempfile
import zipfile
from fnmatch import fnmatch
import rdflib
from rdflib.plugins.parsers.notation3 import BadSyntax
from collections import Counter
from urlparse import urlparse
import shutil

class NIDMUpload:

    def __init__(self, zip_path,tmp_dir=None,load=True):
        self.path = zip_path
        self.provn = None
        self.ttl = None
        self.ttl_relpath = ''
        self.workdir = tempfile.mkdtemp() if tmp_dir is None else tmp_dir
        self.zip = None
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
            self.zip = zipfile.ZipFile(self.path)
        except Exception:
            raise self.ParseException("Unable to read the zip file.")
        metafiles = {}
        for ext in ['.ttl','.provn']:
            metafiles[ext] = [v for v in self.zip.infolist()
                              if fnmatch(v.filename, '*'+ext)
                              # strip OS X resource fork
                              and not fnmatch(v.filename,'__MACOSX*')
                              ]
            if len(metafiles[ext]) > 1:
                raise self.ParseException(
                        "Detected more than one {0} file in zip.".format(ext))
            if not metafiles[ext]:
                raise self.ParseException(
                        "No {0} file found in zip.".format(ext))

        self.ttl = metafiles['.ttl'][0]
        self.provn = metafiles['.provn'][0]
        # fix incorrect property format in earlier versions of SPM12 output
        self.raw_ttl = self.fix_spm12_ttl(self.zip.read(metafiles['.ttl'][0]))
        self.ttl_relpath = self.parse_ttl_relative_path(metafiles['.ttl'][0].filename)

        return self.raw_ttl if extract_ttl else True

    def parse_contrasts(self):
        query = """
        prefix prov: <http://www.w3.org/ns/prov#>
        prefix nidm: <http://purl.org/nidash/nidm#>

        prefix contrast_estimation: <http://purl.org/nidash/nidm#NIDM_0000001>
        prefix contrast_map: <http://purl.org/nidash/nidm#NIDM_0000002>
        prefix contrast_name: <http://purl.org/nidash/nidm#NIDM_0000085>
        prefix statistic_map: <http://purl.org/nidash/nidm#NIDM_0000076>
        prefix statistic_type: <http://purl.org/nidash/nidm#NIDM_0000123>

        SELECT ?rdfLabel ?contrastName ?statType ?statFile WHERE {
         ?cid a contrast_map: ;
              contrast_name: ?contrastName .
         ?cea a contrast_estimation: .
         ?cid prov:wasGeneratedBy ?cea .
         ?sid a statistic_map: ;
              statistic_type: ?statType ;
              rdfs:label ?rdfLabel ;
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

        # uniquify contrast values by file
        self.contrasts = {v['statFile']:v for v in self.contrasts}.values()

        return self.contrasts

    def unpack_nidm_zip(self):
        if not self.ttl or not self.provn:
            self.parse_metafiles()
        if not self.contrasts:
            self.parse_contrasts()

        try:
            self.zip.extractall(path=self.workdir)
            self.unzipped = True
        except Exception,e:
            raise self.ParseException("Unable to unzip: %s" % e)

    def get_statmaps(self):
        if not self.unzipped:
            self.unpack_nidm_zip()
        if not self.contrasts:
            raise self.NoStatMapsException("No eligible data found in this file")

        incidences = Counter([v['rdfLabel'] for v in self.contrasts])
        for contrast in self.contrasts:
            map = {'name':contrast['rdfLabel'],
                   'type':self.parse_statmap_type(contrast['statType']),
                   'file':self.validate_statmap_uri(contrast)}

            # Make the contrast names unique
            if incidences[contrast['rdfLabel']] > 1:
                map['name'] = self.get_unique_mapname(contrast)

            self.statmaps.append(map)
        return self.statmaps

    def validate_statmap_uri(self,contrast):
        rel_path = self.uri_to_path(contrast['statFile'])
        path = self.expand_path(rel_path)
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

    def copy_to_dest(self,dest):
        source = os.path.join(self.workdir,self.ttl_relpath)
        flist = [v for v in os.listdir(source) if self.valid_path(v)]
        for dfile in flist:
            sourcepath = os.path.join(source,dfile)
            destpath = os.path.join(dest,dfile)
            if not os.path.exists(destpath):
                shutil.move(sourcepath, destpath)

    def cleanup(self):
        shutil.rmtree(self.workdir)

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
        return '{0} {1}'.format(contrast['rdfLabel'], type)

    @staticmethod
    def parse_statmap_type(stattype_url):
        stato_dict = {"http://purl.obolibrary.org/obo/STATO_0000376": "Z",
                      "http://purl.obolibrary.org/obo/STATO_0000176": "T",
                      "http://purl.obolibrary.org/obo/STATO_0000282": "F"}
        return stato_dict[stattype_url]

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
    def valid_path(path):
        # os x resource fork
        if fnmatch(path,'__MACOSX*'):
            return False
        # ignore hidden, allow relative paths
        if path[0] is '.' and path[1] is not ('/' or '.'):
            return False
        return True

    @staticmethod
    def print_sparql_results(res):
        for idx, row in enumerate(res.bindings):
            rowfmt = []
            print "Item %d" % idx
            for key, val in sorted(row.items()):
                rowfmt.append('%s-->%s' % (key, val.decode()))
            print '\n'.join(rowfmt)

    @staticmethod
    def fix_spm12_ttl(ttl):
        return ttl.replace("nidm_NoiseModel", "nidm:NoiseModel")
