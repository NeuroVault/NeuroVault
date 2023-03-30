from django.contrib import admin
from neurovault.apps.statmaps.models import (
    Collection,
    Image,
    StatisticMap,
    Atlas,
    NIDMResults,
    NIDMResultStatisticMap,
    Comparison,
    Similarity,
)
from neurovault.apps.statmaps.forms import (
    StatisticMapForm,
    AtlasForm,
    NIDMResultStatisticMapForm,
    NIDMResultsForm,
)
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin


class BaseImageAdmin(admin.ModelAdmin):
    readonly_fields = ["collection"]

    # enforce read only only on edit
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else []


class StatisticMapAdmin(PolymorphicChildModelAdmin, BaseImageAdmin):
    base_model = StatisticMap
    base_form = StatisticMapForm


class AtlasAdmin(PolymorphicChildModelAdmin, BaseImageAdmin):
    base_model = Atlas
    base_form = AtlasForm


class NIDMStatisticMapAdmin(PolymorphicChildModelAdmin, BaseImageAdmin):
    base_model = NIDMResultStatisticMap
    base_form = NIDMResultStatisticMapForm
    readonly_fields = BaseImageAdmin.readonly_fields + ["nidm_results"]


class ImageAdmin(PolymorphicParentModelAdmin):
    base_model = Image
    child_models = (StatisticMap, Atlas, NIDMResultStatisticMap)


class NIDMResultsAdmin(BaseImageAdmin):
    form = NIDMResultsForm

    def save_model(self, request, obj, form, change):
        instance = form.save(commit=False)
        instance.save()
        form.save_nidm()
        form.update_ttl_urls()
        form.save_m2m()


admin.site.register(StatisticMap, StatisticMapAdmin),
admin.site.register(Atlas, AtlasAdmin),
admin.site.register(NIDMResultStatisticMap, NIDMStatisticMapAdmin)

admin.site.register(Image, ImageAdmin)
admin.site.register(Collection)
admin.site.register(NIDMResults, NIDMResultsAdmin)
admin.site.register(Comparison)
admin.site.register(Similarity)
