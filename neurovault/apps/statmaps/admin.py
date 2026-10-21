"""Back-office admin. Edits of collection items go through the use cases so
files and processing stay consistent; other models are edited directly."""
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
    image_changes,
)
from neurovault.application.ports import SYSTEM
from neurovault.bootstrap import services
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin

KINDS = {StatisticMap: "statmap", Atlas: "atlas"}


class BaseImageAdmin(admin.ModelAdmin):
    readonly_fields = ["collection"]

    # enforce read only only on edit
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else []

    def save_model(self, request, obj, form, change):
        changes, files, tags = image_changes(form)
        items = services().items
        if change:
            items.change(SYSTEM, obj.pk, changes, files, tags=tags)
        else:
            obj.pk = items.add(
                SYSTEM, changes.pop("collection_id"), KINDS[type(obj)], changes, files, tags=tags
            )

    def save_related(self, request, form, formsets, change):
        pass

    def delete_model(self, request, obj):
        services().items.delete(SYSTEM, obj.pk)


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


class NIDMResultsAdmin(admin.ModelAdmin):
    form = NIDMResultsForm
    readonly_fields = ["collection"]

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else []

    def save_model(self, request, obj, form, change):
        form.save()

    def save_related(self, request, form, formsets, change):
        pass

    def delete_model(self, request, obj):
        services().bundles.delete(SYSTEM, obj.pk)


class CollectionAdmin(admin.ModelAdmin):
    def delete_model(self, request, obj):
        services().collections.delete(SYSTEM, obj.pk)


admin.site.register(StatisticMap, StatisticMapAdmin)
admin.site.register(Atlas, AtlasAdmin)
admin.site.register(NIDMResultStatisticMap, NIDMStatisticMapAdmin)

admin.site.register(Image, ImageAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(NIDMResults, NIDMResultsAdmin)
admin.site.register(Comparison)
admin.site.register(Similarity)
