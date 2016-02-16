from neurovault.apps.statmaps.models import Image, Collection, CognitiveAtlasTask, StatisticMap
from django.contrib.sitemaps import Sitemap

class BaseSitemap(Sitemap):
    priority = 0.5

    def lastmod(self, obj):
        return obj.modify_date

    def location(self,obj):
        return obj.get_absolute_url()


class ImageSitemap(BaseSitemap):
    changefreq = "weekly"
    def items(self):
        return Image.objects.filter(collection__private=False)


class CollectionSitemap(BaseSitemap):
    changefreq = "weekly"
    def items(self):
        return Collection.objects.filter(private=False)


class CognitiveAtlasTaskSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5

    def items(self):
        task_ids = StatisticMap.objects.values_list('cognitive_paradigm_cogatlas',flat=True).distinct()
        return CognitiveAtlasTask.objects.filter(cog_atlas_id__in=task_ids)
         
    def location(self,obj):
        return obj.get_absolute_url()
