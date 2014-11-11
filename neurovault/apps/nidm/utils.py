from zipfile import ZipFile
import rdflib
from neurovault.apps.nidm.models import CoordinateSpace, ContrastEstimation, Map, StatisticMap
from django.core.files.base import ContentFile
import os

def get_stat_map_instances(graph, nidm_file_handle):
    translation = {'http://www.incf.org/ns/nidash/nidm#errorDegreesOfFreedom': ("errorDegreesOfFreedomu", float),
                   'http://www.w3.org/ns/prov#atLocation': ("file", file),
                   'http://www.incf.org/ns/nidash/nidm#contrastName': ('contrastName', str),
                   'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': ('prov_type', str),
                   #'http://www.incf.org/ns/nidash/nidm#atCoordinateSpace': ("atCoordinateSpace", CoordinateSpace),
                   #'http://www.w3.org/ns/prov#wasGeneratedBy': ("contrastEstimation", ContrastEstimation),
                   #'http://www.w3.org/ns/prov#wasDerivedFrom': ("map", Map),
                   'http://www.incf.org/ns/nidash/nidm#statisticType': ("statisticType", str),
                   'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                   'http://www.w3.org/2000/01/rdf-schema#label': ("prov_label", str),
                   'http://www.incf.org/ns/nidash/nidm#effectDegreesOfFreedom': ("effectDegreesOfFreedom", float)
                   }
    
    query = """
prefix prov: <http://www.w3.org/ns/prov#>
prefix nidm: <http://www.incf.org/ns/nidash/nidm#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?uri ?property ?value WHERE {
 ?uri a nidm:StatisticMap .
 ?uri ?property ?value .
}
"""
    results = graph.query(query)
    stat_maps = {}
    for idx, row in enumerate(results.bindings):
        if str(row["uri"]) not in stat_maps:
            stat_maps[str(row["uri"])] = {}
        stat_maps[str(row["uri"])][str(row["property"])] = row["value"].decode()
    
    for uri in stat_maps.keys():
        stat_map = StatisticMap()
        stat_map.prov_URI = uri
        for property_uri, (property_name, property_type) in translation.iteritems():
            if property_uri in stat_maps[uri]:
                if property_type is file:
                    file_field = getattr(stat_map, property_name)
                    root = nidm_file_handle.infolist()[0].filename
                    _,  filename = os.path.split(stat_maps[uri][property_uri])
                    file_path = os.path.join(root + filename)
                    file_handle = nidm_file_handle.open(file_path, "r")
                    file_field.save(filename, ContentFile(file_handle.read()))
                else:
                    setattr(stat_map, property_name, property_type(stat_maps[uri][property_uri]))
        
        return stat_map

def parse_nidm_results(nidm_file):
    z_fp = ZipFile(nidm_file)
    root = z_fp.infolist()[0].filename
    nidm_filename = root + "nidm.ttl"
    nidm_fp = z_fp.open(nidm_filename, "r")
    nidm_content = nidm_fp.read()
    #SPM12 bug
    nidm_content = nidm_content.replace("nidm_NoiseModel", "nidm:NoiseModel")
    
    nidm_graph = rdflib.Graph()
    nidm_graph.parse(data=nidm_content, format='turtle')
    
    stat_map = get_stat_map_instances(nidm_graph, z_fp)
    stat_map.save()
    
    
if __name__ == '__main__':
    parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/spm_example.nidm.zip")