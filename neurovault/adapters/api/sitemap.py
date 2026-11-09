from django.contrib.sitemaps import Sitemap

from django.db.models import Q

from neurovault.adapters.persistence.models import (
    Item,
    Collection,
    CognitiveAtlasTask,
)


class BaseSitemap(Sitemap):
    priority = 0.5
    limit = 5000

    def lastmod(self, obj):
        return obj.modify_date

    def location(self, obj):
        return obj.get_absolute_url()


class ImageSitemap(BaseSitemap):
    changefreq = "weekly"

    def items(self):
        return Item.objects.filter(collection__private=False)


class CollectionSitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 1.0

    def items(self):
        return (
            Collection.objects.filter(private=False)
            .filter(Q(items__isnull=False) | Q(nidm_bundles__isnull=False))
            .distinct()
        )


class CognitiveAtlasTaskSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        task_ids = (
            Item.objects.statmaps().filter(collection__private=False)
            .values_list("cognitive_paradigm_cogatlas", flat=True)
            .distinct()
        )
        return CognitiveAtlasTask.objects.filter(cog_atlas_id__in=task_ids)

    def location(self, obj):
        return obj.get_absolute_url()
