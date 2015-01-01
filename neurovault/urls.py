from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from neurovault.apps.statmaps.models import Image, Collection, StatisticMap,\
    Atlas, NIDMResults, NIDMResultStatisticMap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from rest_framework.filters import DjangoFilterBackend
from lxml.etree import xmlfile
admin.autodiscover()
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, routers, serializers, mixins
from rest_framework.decorators import link
from rest_framework.response import Response
from taggit.models import Tag
from neurovault.apps.statmaps.views import get_image,get_collection
import re
import xml.etree.ElementTree as ET
import urllib2
import os

from django import template
template.add_to_builtins('django.templatetags.future')
template.add_to_builtins('django.contrib.staticfiles.templatetags.staticfiles')


class HyperlinkedFileField(serializers.FileField):

    def to_native(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.url)


class HyperlinkedRelatedURL(serializers.RelatedField):

    def to_native(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.get_absolute_url())


class HyperlinkedImageURL(serializers.CharField):

    def to_native(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value)


class SerializedContributors(serializers.CharField):

    def to_native(self, value):
        if value:
            return ', '.join([v.username for v in value.all()])


class NIDMDescriptionSerializedField(serializers.CharField):

    def to_native(self, value):
        if value and self.parent.object is not None:
            #import ipdb; ipdb.set_trace()
            parent = self.parent.object.nidm_results.name
            fname = os.path.split(self.parent.object.file.name)[-1]
            return 'NIDM Results: {0}.zip > {1}'.format(parent,fname)


class APIHelper:
    ''' Contains generic helper methods to call from various
    serializers and viewsets. '''
    @staticmethod
    def wrap_for_datatables(data, fields_to_strip=[]):
        '''
        Formats a model instance for the Datatables JQuery plugin.

        Args:
            data: A Model instance retrieved from the database.
            fields_to_strip: A list of named attributes to exclude.

        Returns:
            A dict with an aaData field containing all of the
            values (and no keys) in tabular format. '''
        data = dict([(k,v) for k,v in data.items() if v and k not in fields_to_strip])
        return Response(
            {'aaData': zip(data.keys(), data.values())}
        )


class ImageSerializer(serializers.HyperlinkedModelSerializer):

    file = HyperlinkedFileField(source='file')
    collection = HyperlinkedRelatedURL(source='collection')
    url = HyperlinkedImageURL(source='get_absolute_url')

    class Meta:
        model = Image
        exclude = ['polymorphic_ctype']

    def to_native(self, obj):
        """
        Because GalleryItem is Polymorphic
        """
        if isinstance(obj, StatisticMap):
            return StatisticMapSerializer(obj, context={
                                'request': self.context['request']}).to_native(obj)
        if isinstance(obj, Atlas):
            return AtlasSerializer(obj, context={
                                'request': self.context['request']}).to_native(obj)

        if isinstance(obj, NIDMResultStatisticMap):
            return NIDMResultStatisticMapSerializer(obj, context={
                                'request': self.context['request']}).to_native(obj)

        return super(ImageSerializer, self).to_native(obj)


class StatisticMapSerializer(serializers.HyperlinkedModelSerializer):

    file = HyperlinkedFileField(source='file')
    collection = HyperlinkedRelatedURL(source='collection')
    url = HyperlinkedImageURL(source='get_absolute_url')

    class Meta:
        model = StatisticMap
        exclude = ['polymorphic_ctype']


class NIDMResultStatisticMapSerializer(serializers.HyperlinkedModelSerializer):
    file = HyperlinkedFileField(source='file')
    collection = HyperlinkedRelatedURL(source='collection')
    url = HyperlinkedImageURL(source='get_absolute_url')
    nidm_results = HyperlinkedRelatedURL(source='nidm_results')
    description = NIDMDescriptionSerializedField(source='get_absolute_url')

    class Meta:
        model = NIDMResultStatisticMap
        exclude = ['polymorphic_ctype']


class AtlasSerializer(serializers.HyperlinkedModelSerializer):

    label_description_file = HyperlinkedFileField(source='label_description_file')
    collection = HyperlinkedRelatedURL(source='collection')
    url = HyperlinkedImageURL(source='get_absolute_url')

    class Meta:
        model = Atlas
        exclude = ['polymorphic_ctype']


class NIDMResultsSerializer(serializers.ModelSerializer):
    url = HyperlinkedImageURL(source='get_absolute_url')
    zip_file = HyperlinkedFileField(source='zip_file')
    ttl_file = HyperlinkedFileField(source='ttl_file')
    provn_file = HyperlinkedFileField(source='provn_file')
    collection = HyperlinkedRelatedURL(source='collection')
    statmaps = ImageSerializer(source='nidmresultstatisticmap_set')

    class Meta:
        model = NIDMResults
        exclude = ['polymorphic_ctype','id']


class CollectionSerializer(serializers.ModelSerializer):
    images = ImageSerializer(source='image_set')
    nidm_results = NIDMResultsSerializer(source='nidmresults_set')
    contributors = SerializedContributors(source='contributors')

    class Meta:
        model = Collection
        exclude = ['private_token', 'private']


class ImageViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):

    queryset = Image.objects.filter(collection__private=False)
    serializer_class = ImageSerializer

    def _get_api_image(self,request,pk=None):
        private_url = re.match(r'^[A-Z]{8}\-\d+$',pk)
        if private_url:
            collection_cid,pk = pk.split('-')
        else:
            base_image = self.get_object()
            collection_cid = base_image.collection.id
        return get_image(pk,collection_cid,request,mode='api')

    @link()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the Datatables plugin. '''
        image = self._get_api_image(request,pk)
        data = ImageSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date',
                                                    'description', 'add_date'])

    def retrieve(self, request, pk=None):
        image = self._get_api_image(request,pk)
        data = ImageSerializer(image, context={'request': request}).data
        return Response(data)


class AtlasViewSet(ImageViewSet):
    queryset = Atlas.objects.filter(collection__private=False)
    serializer_class = AtlasSerializer

    @link()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the Datatables plugin. '''
        image = self._get_api_image(request,pk)
        data = AtlasSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date',
                                                    'description', 'add_date'])

    @link()
    def regions_table(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the regions_table plugin. '''
        image = self._get_api_image(request,pk)
        xmlFile = image.label_description_file
        xmlFile.open()
        root = ET.fromstring(xmlFile.read())
        xmlFile.close()
        lines = root.find('data').findall('label')
        indices = [int(line.get('index')) + 1 for line in lines]
        regions = [line.text.split('(')[0].replace("'",'').rstrip(' ').lower() for line in lines]
        return Response(
            {'aaData': zip(indices, regions)})


class CollectionViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):

    queryset = Collection.objects.filter(private=False)
    filter_fields = ('name', 'DOI', 'owner')
    serializer_class = CollectionSerializer
    filter_backends = (DjangoFilterBackend,)

    @link()
    def datatable(self, request, pk=None):
        collection = get_collection(pk,request,mode='api')
        data = CollectionSerializer(collection, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['owner', 'modify_date', 'images'])

    def retrieve(self, request, pk=None):
        collection = get_collection(pk,request,mode='api')
        data = CollectionSerializer(collection, context={'request': request}).data
        return Response(data)


class NIDMResultsViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):

    queryset = NIDMResults.objects.filter(collection__private=False)
    serializer_class = NIDMResultsSerializer


class TagViewSet(viewsets.ModelViewSet):

    model = Tag

    @link()
    def datatable(self, request, pk=None):
        from django.db.models import Count
        data = Tag.objects.annotate(action_count=Count('action'))
        return APIHelper.wrap_for_datatables(data)


# Routers provide an easy way of automatically determining the URL conf
router = routers.DefaultRouter()
router.register(r'images', ImageViewSet)
router.register(r'atlases', AtlasViewSet)
router.register(r'collections', CollectionViewSet)
router.register(r'nidm_results', NIDMResultsViewSet)

urlpatterns = patterns('',
                       url('', include('social.apps.django_app.urls', namespace='social')),
                       url(r'^', include('neurovault.apps.main.urls')),
                       url(r'^', include('neurovault.apps.statmaps.urls')),
                       url(r'^accounts/', include('neurovault.apps.users.urls')),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^api/', include(router.urls)),
                       url(r'^api-auth/', include(
                           'rest_framework.urls', namespace='rest_framework'))
                       )
