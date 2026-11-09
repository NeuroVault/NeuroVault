"""Back-office admin. Every write to collections, images and NIDM bundles goes
through the use cases, so permissions, files and processing stay consistent."""
from django.contrib import admin

from neurovault.adapters.http import actor
from neurovault.adapters.persistence.models import Collection, Comparison, Item, NIDMBundle, Similarity
from neurovault.adapters.web.statmaps.forms import NIDMResultsForm, collection_changes, image_changes
from neurovault.config.bootstrap import services


class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "collection", "modify_date")
    list_filter = ("kind",)
    search_fields = ("name",)
    exclude = ("kind",)
    readonly_fields = ["collection", "source_bundle"]

    def has_add_permission(self, request):
        return False  # images are added through uploads

    def save_model(self, request, obj, form, change):
        changes, files, tags = image_changes(form)
        services().items.change(actor(request), obj.pk, changes, files, tags=tags)

    def save_related(self, request, form, formsets, change):
        pass

    def delete_model(self, request, obj):
        services().items.delete(actor(request), obj.pk)

    def delete_queryset(self, request, queryset):
        for pk in list(queryset.values_list("pk", flat=True)):
            services().items.delete(actor(request), pk)


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
        services().bundles.delete(actor(request), obj.pk)

    def delete_queryset(self, request, queryset):
        for pk in list(queryset.values_list("pk", flat=True)):
            services().bundles.delete(actor(request), pk)


class CollectionAdmin(admin.ModelAdmin):
    exclude = ("private_token",)

    def save_model(self, request, obj, form, change):
        data = form.cleaned_data
        obj.pk = obj.id = services().collections.save(
            actor(request),
            obj.pk if change else None,
            collection_changes(form),
            contributor_ids=[u.pk for u in data["contributors"]],
            community_ids=[c.pk for c in data["communities"]],
            owner_id=data["owner"].pk if data.get("owner") else None,
        )

    def save_related(self, request, form, formsets, change):
        pass  # contributors and communities were stored by the use case

    def delete_model(self, request, obj):
        services().collections.delete(actor(request), obj.pk)

    def delete_queryset(self, request, queryset):
        for pk in list(queryset.values_list("pk", flat=True)):
            services().collections.delete(actor(request), pk)


admin.site.register(Item, ItemAdmin)
admin.site.register(NIDMBundle, NIDMBundleAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(Comparison)
admin.site.register(Similarity)
