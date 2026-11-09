from django.forms.models import model_to_dict

from neurovault.adapters.persistence.models import Item
from neurovault.adapters.web.statmaps.forms import EditStatisticMapForm
from neurovault.config.bootstrap import services
from neurovault.core.application.ports import SYSTEM

statmaps = Item.objects.statmaps()
count = statmaps.count()
for i, image in enumerate(statmaps):
    print("Fixing statistic map %d (%d/%d)" % (image.pk, i + 1, count))
    form = EditStatisticMapForm(model_to_dict(image), instance=image, user=image.collection.owner)
    services().items.change(SYSTEM, image.pk, {"is_valid": form.is_valid()}, check_access=False)
