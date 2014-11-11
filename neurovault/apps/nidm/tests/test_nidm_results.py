from django.test import TestCase
from ..models import StatisticMap

class AnimalTestCase(TestCase):
#     def setUp(self):
#         Animal.objects.create(name="lion", sound="roar")
#         Animal.objects.create(name="cat", sound="meow")

    def test_animals_can_speak(self):
        self.assertEqual("bla", "blad")