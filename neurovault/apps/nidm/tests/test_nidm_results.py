from django.test import TestCase
from ..models import StatisticMap
from neurovault.apps.nidm.utils import parse_nidm_results

class AnimalTestCase(TestCase):
#     def setUp(self):
#         Animal.objects.create(name="lion", sound="roar")
#         Animal.objects.create(name="cat", sound="meow")

    def test_animals_can_speak(self):
        parse_nidm_results("/Users/filo/krzysztof.gorgolewski@gmail.com/NeuroVault/NIDM/spm_example.nidm.zip")