from django.forms.models import model_to_dict

from neurovault.apps.statmaps.forms import EditStatisticMapForm
from neurovault.apps.statmaps.models import StatisticMap

count = StatisticMap.objects.count()
for i, image in enumerate(StatisticMap.objects.all()):
    print "Fixing StatisticMap %d (%d/%d)"%(image.pk, i+1, count)
    form = EditStatisticMapForm(model_to_dict(image), instance=image, user=image.collection.owner)
    image.is_valid = form.is_valid()
    image.save()
