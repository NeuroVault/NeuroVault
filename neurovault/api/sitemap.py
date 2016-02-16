from neurovault.apps.statmaps.models import Image, Collection, CognitiveAtlasTask
from django.contrib.sitemaps import Sitemap

class BaseSitemap(Sitemap):
    changefreq = "always"
    priority = 0.5

    def lastmod(self, obj):
        return obj.modify_date

    def location(self,obj):
        return obj.get_absolute_url()


class ImageSitemap(BaseSitemap):

    def items(self):
        return Image.objects.filter(collection__private=False)


class CollectionSitemap(BaseSitemap):
    def items(self):
        return Collection.objects.filter(private=False)


class CognitiveAtlasTaskSitemap(Sitemap):
    changefreq = "always"
    priority = 0.5

    def items(self):
        return CognitiveAtlasTask.objects.all()

    def location(self,obj):
        return obj.get_absolute_url()
