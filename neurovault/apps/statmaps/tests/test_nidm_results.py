from django.test import TestCase
from neurovault.apps.statmaps.utils import parse_nidm_results
from neurovault.apps.statmaps.models import Collection
from django.contrib.auth.models import User

class NIDMResultsTestCase(TestCase):

    def test_parse_nidm_results_spm_example(self):
        user = User(username='test')
        user.save()
        collection = Collection(name='test_spm_example', owner=user)
        collection.save()
        for stat_map in parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/spm_example.nidm.zip", collection):
            print stat_map.name
         
    def test_parse_nidm_results_auditory(self):
        user = User(username='test')
        user.save()
        collection = Collection(name='test_auditory', owner=user)
        collection.save()
        parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/auditory.nidm.zip", collection)
        
    def test_parse_nidm_fsl(self):
        user = User(username='test')
        user.save()
        collection = Collection(name='test_nidm_fsl', owner=user)
        collection.save()
        parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/fsl.nidm.zip", collection)