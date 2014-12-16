from django.contrib import admin
from neurovault.apps.statmaps.models import Collection, Image, StatisticMap, Atlas
from neurovault.apps.statmaps.forms import StatisticMapForm, AtlasForm
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin


class StatisticMapAdmin(PolymorphicChildModelAdmin):
    base_model = StatisticMap
    base_form = StatisticMapForm


class AtlasAdmin(PolymorphicChildModelAdmin):
    base_model = Atlas
    base_form = AtlasForm


class ImageAdmin(PolymorphicParentModelAdmin):
    base_model = Image
    child_models = (
        (StatisticMap, StatisticMapAdmin),
        (Atlas, AtlasAdmin),
    )


admin.site.register(Image, ImageAdmin)
admin.site.register(Collection)
