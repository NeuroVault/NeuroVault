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
from rest_framework import viewsets, routers, serializers, mixins, generics
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from rest_framework.views import APIView
import rest_framework_swagger
from taggit.models import Tag
from django.http import Http404, HttpResponse
from rest_framework.renderers import JSONRenderer
from neurovault.apps.statmaps.views import get_image,get_collection
import re
import xml.etree.ElementTree as ET
import urllib2
import os
import cPickle as pickle
from neurovault.apps.statmaps.voxel_query_functions import voxelToRegion, getSynonyms, toAtlas, getAtlasVoxels

from django import template
template.add_to_builtins('django.templatetags.future')
template.add_to_builtins('django.contrib.staticfiles.templatetags.staticfiles')

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


class HyperlinkedFileField(serializers.FileField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.url)


class HyperlinkedRelatedURL(serializers.RelatedField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.get_absolute_url())


class HyperlinkedImageURL(serializers.CharField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value)


class SerializedContributors(serializers.CharField):

    def to_representation(self, value):
        if value:
            return ', '.join([v.username for v in value.all()])


class NIDMDescriptionSerializedField(serializers.CharField):

    def to_representation(self, value):
        print self.parent.instance.nidm_results.name
        if value and self.parent.instance is not None:
            parent = self.parent.instance.nidm_results.name
            fname = os.path.split(self.parent.instance.file.name)[-1]
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

    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    url = HyperlinkedImageURL(source='get_absolute_url')

    class Meta:
        model = Image
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        """
        Because GalleryItem is Polymorphic
        """
        if isinstance(obj, StatisticMap):
            return StatisticMapSerializer(obj, context={
                                'request': self.context['request']}).to_representation(obj)
        if isinstance(obj, Atlas):
            return AtlasSerializer(obj, context={
                                'request': self.context['request']}).to_representation(obj)

        if isinstance(obj, NIDMResultStatisticMap):
            return NIDMResultStatisticMapSerializer(obj, context={
                                'request': self.context['request']}).to_representation(obj)

        return super(ImageSerializer, self).to_representation(obj)
    

class StatisticMapSerializer(serializers.HyperlinkedModelSerializer):

    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    url = HyperlinkedImageURL(source='get_absolute_url')

    class Meta:
        model = StatisticMap
        exclude = ['polymorphic_ctype']


class NIDMResultStatisticMapSerializer(serializers.HyperlinkedModelSerializer):
    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    url = HyperlinkedImageURL(source='get_absolute_url')
    nidm_results = HyperlinkedRelatedURL(read_only=True)
    description = NIDMDescriptionSerializedField(source='get_absolute_url')

    class Meta:
        model = NIDMResultStatisticMap
        exclude = ['polymorphic_ctype']


class AtlasSerializer(serializers.HyperlinkedModelSerializer):

    label_description_file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    url = HyperlinkedImageURL(source='get_absolute_url')

    class Meta:
        model = Atlas
        exclude = ['polymorphic_ctype']


class NIDMResultsSerializer(serializers.ModelSerializer):
    url = HyperlinkedImageURL(source='get_absolute_url')
    zip_file = HyperlinkedFileField()
    ttl_file = HyperlinkedFileField()
    provn_file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    statmaps = ImageSerializer(many=True, source='nidmresultstatisticmap_set')

    class Meta:
        model = NIDMResults
        exclude = ['id']

    
class CollectionSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, source='image_set')
    nidm_results = NIDMResultsSerializer(many=True, source='nidmresults_set')
    contributors = SerializedContributors()

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

    @detail_route()
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

    @detail_route()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the Datatables plugin. '''
        image = self._get_api_image(request,pk)
        data = AtlasSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date',
                                                    'description', 'add_date'])

    @detail_route()
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
        
    @list_route()
    def atlas_query_region(self, request, pk=None):
        ''' Returns a dictionary containing a list of voxels that match the searched term (or related searches) in the specified atlas.\n 
        Parameters: region, collection, atlas \n
        Example: '/api/atlases/atlas_query_region/?region=middle frontal gyrus&collection=Harvard-Oxford cortical and subcortical structural atlases&atlas=HarvardOxford cort maxprob thr25 1mm' '''
        search = request.GET.get('region','')
        atlas = request.GET.get('atlas','').replace('\'', '')
        collection = name=request.GET.get('collection','')
        neurovault_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        try:
            collection_object = Collection.objects.filter(name=collection)[0]
        except IndexError:
            return JSONResponse('error: could not find collection: %s' % collection, status=400)
        try:
            atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
            atlas_image = atlas_object.file
            atlas_xml = atlas_object.label_description_file
        except IndexError:
            return JSONResponse('could not find %s' % atlas, status=400)
        if request.method == 'GET':
            atlas_xml.open()
            root = ET.fromstring(atlas_xml.read())
            atlas_xml.close()
            atlasRegions = [x.text.lower() for x in root.find('data').findall('label')]
            if search in atlasRegions:
                searchList = [search]
            else:
                synonymsDict = {}
                with open(os.path.join(neurovault_root, 'neurovault/apps/statmaps/NIFgraph.pkl'),'rb') as input:
                    graph = pickle.load(input)
                for atlasRegion in atlasRegions:
                    synonymsDict[atlasRegion] = getSynonyms(atlasRegion)
                try:
                    searchList = toAtlas(search, graph, atlasRegions, synonymsDict)
                except ValueError:
                    return Response('error: region not in atlas or ontology', status=400)
                if searchList == 'none':
                    return Response('error: could not map specified region to region in specified atlas', status=400)
            try:
                data = {'voxels':getAtlasVoxels(searchList, atlas_image, atlas_xml)}
            except ValueError:
                return Response('error: region not in atlas', status=400)
    
            return Response(data)
        
    @list_route()
    def atlas_query_voxel(self, request, pk=None):
        ''' Returns the region name that matches specified coordinates in the specified atlas.\n 
        Parameters: x, y, z, collection, atlas \n
        Example: '/api/atlases/atlas_query_voxel/?x=30&y=30&z=30&collection=Harvard-Oxford cortical and subcortical structural atlases&atlas=HarvardOxford cort maxprob thr25 1mm' '''
        X = request.GET.get('x','')
        Y = request.GET.get('y','')
        Z = request.GET.get('z','')
        collection = name=request.GET.get('collection','')
        atlas = request.GET.get('atlas','').replace('\'', '')
        try:
            collection_object = Collection.objects.filter(name=collection)[0]
        except IndexError:
            return JSONResponse('error: could not find collection: %s' % collection, status=400)
        try:
            print atlas
            print [x.name for x in Atlas.objects.filter(collection=collection_object)]
            atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
            atlas_image = atlas_object.file
            atlas_xml = atlas_object.label_description_file
        except IndexError:
            return JSONResponse('error: could not find atlas: %s' % atlas, status=400)
        try:
            data = voxelToRegion(X,Y,Z,atlas_image, atlas_xml)
        except IndexError:
            return JSONResponse('error: one or more coordinates are out of range', status=400)
        return Response(data)


class CollectionViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):

    queryset = Collection.objects.filter(private=False)
    filter_fields = ('name', 'DOI', 'owner')
    serializer_class = CollectionSerializer
    filter_backends = (DjangoFilterBackend,)

    @detail_route()
    def datatable(self, request, pk=None):
        collection = get_collection(pk,request,mode='api')
        data = CollectionSerializer(collection, context={'request': request}).data
        if data and 'description' in data and data['description']:
            data['description'] = data['description'].replace('\n', '<br />')
        return APIHelper.wrap_for_datatables(data, ['owner', 'modify_date'])

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

    @detail_route()
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
                           'rest_framework.urls', namespace='rest_framework')),
                       url(r'^api-docs/', include('rest_framework_swagger.urls'))
                       )

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^(?P<path>favicon\.ico)$', 'django.views.static.serve', {
            'document_root': os.path.join(settings.STATIC_ROOT,'images')}),
    )
