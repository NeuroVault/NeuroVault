from django.test import TestCase
from neurovault.apps.statmaps.utils import parse_nidm_results
from neurovault.apps.statmaps.models import Collection
from django.contrib.auth.models import User

class NIDMResultsTestCase(TestCase):

    def test_parse_nidm_results(self):
        user = User(username='test')
        user.save()
        collection = Collection(name='test', owner=user)
        collection.save()
        parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/spm_example.nidm.zip", collection)