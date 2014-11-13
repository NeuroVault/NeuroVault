from zipfile import ZipFile
import rdflib
from neurovault.apps.nidm.models import StatisticMap

def get_all_instances(model_class, graph, nidm_file_handle):
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
        instances.append(model_class.create(uri, graph, nidm_file_handle))
        
    return instances

def get_stat_map_instances(graph, nidm_file_handle):
    return get_all_instances(StatisticMap, graph, nidm_file_handle)

def parse_nidm_results(nidm_file):
    z_fp = ZipFile(nidm_file)
    root = z_fp.infolist()[0].filename
    nidm_filename = root + "nidm.ttl"
    nidm_fp = z_fp.open(nidm_filename, "r")
    nidm_content = nidm_fp.read()
    #A tiny SPM12 factual inaccuracy
    nidm_content = nidm_content.replace("nidm_NoiseModel", "nidm:NoiseModel")
    
    nidm_graph = rdflib.Graph()
    nidm_graph.parse(data=nidm_content, format='turtle')
    
    stat_maps = get_stat_map_instances(nidm_graph, z_fp)
    for stat_map in stat_maps:
        stat_map.save()
    
    
if __name__ == '__main__':
    parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/spm_example.nidm.zip")