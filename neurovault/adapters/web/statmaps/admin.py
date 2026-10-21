"""Back-office admin. Edits of collection items go through the use cases so
files and processing stay consistent; other models are edited directly."""
from django.contrib import admin

from neurovault.core.application.ports import SYSTEM
from neurovault.adapters.web.statmaps.forms import NIDMResultsForm, image_changes
from neurovault.adapters.persistence.models import Collection, Comparison, Item, NIDMBundle, Similarity
from neurovault.config.bootstrap import services


class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "collection", "modify_date")
    list_filter = ("kind",)
    search_fields = ("name",)
    exclude = ("kind",)
    readonly_fields = ["collection", "source_bundle"]

    def get_readonly_fields(self, request, obj=None):
        # enforce read only only on edit
        return self.readonly_fields if obj else []

    def has_add_permission(self, request):
        return False  # images are added through uploads

    def save_model(self, request, obj, form, change):
        changes, files, tags = image_changes(form)
        services().items.change(SYSTEM, obj.pk, changes, files, tags=tags)

    def save_related(self, request, form, formsets, change):
        pass

    def delete_model(self, request, obj):
        services().items.delete(SYSTEM, obj.pk)


class NIDMBundleAdmin(admin.ModelAdmin):
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


admin.site.register(Item, ItemAdmin)
admin.site.register(NIDMBundle, NIDMBundleAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(Comparison)
admin.site.register(Similarity)
