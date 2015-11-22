from neurovault.apps.statmaps.voxel_query_functions import voxelToRegion, getSynonyms, toAtlas, getAtlasVoxels
from rest_framework.relations import StringRelatedField, PrimaryKeyRelatedField
from neurovault.apps.statmaps.models import Image, Collection, StatisticMap,\
    Atlas, NIDMResults, NIDMResultStatisticMap, CognitiveAtlasTask, BaseStatisticMap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from neurovault.apps.statmaps.urls import StandardResultPagination
from rest_framework.filters import DjangoFilterBackend
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from lxml.etree import xmlfile
admin.autodiscover()
from rest_framework import viewsets, routers, serializers, mixins, generics
from neurovault.apps.statmaps.views import get_image, get_collection
from rest_framework.decorators import detail_route, list_route
from django.contrib.auth.models import User, Group
from rest_framework.renderers import JSONRenderer
from django.http import Http404, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from oauth2_provider import views as oauth_views
import xml.etree.ElementTree as ET
from taggit.models import Tag
import cPickle as pickle
import urllib2
import os
import re
import pandas as pd


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
            return 'NIDM Results: {0}.zip > {1}'.format(parent, fname)


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
        data = dict([(k, v)
                     for k, v in data.items() if v and k not in fields_to_strip])
        return Response(
            {'aaData': zip(data.keys(), data.values())}
        )


class ImageSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.ReadOnlyField()
    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    collection_id = serializers.ReadOnlyField()
    url = HyperlinkedImageURL(source='get_absolute_url')
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = Image
        exclude = ['polymorphic_ctype']

    def get_file_size(self, obj):
        return obj.file.size

    def to_representation(self, obj):
        """
        Because Image is Polymorphic
        """
        if isinstance(obj, StatisticMap):
            serializer = StatisticMapSerializer
            image_type = 'statistic_map'
        elif isinstance(obj, Atlas):
            serializer = AtlasSerializer
            image_type = 'atlas'
        elif isinstance(obj, NIDMResultStatisticMap):
            serializer = NIDMResultStatisticMapSerializer
            image_type = 'NIDM results statistic map'

        orderedDict = serializer(obj, context={
            'request': self.context['request']}).to_representation(obj)
        orderedDict['image_type'] = image_type
        for key, val in orderedDict.iteritems():
            if pd.isnull(val):
                orderedDict[key] = None;
        return orderedDict


class StatisticMapSerializer(ImageSerializer):

    cognitive_paradigm_cogatlas = StringRelatedField(read_only=True)
    cognitive_paradigm_cogatlas_id = PrimaryKeyRelatedField(
        read_only=True, source="cognitive_paradigm_cogatlas")
    cognitive_contrast_cogatlas = StringRelatedField(read_only=True)
    cognitive_contrast_cogatlas_id = PrimaryKeyRelatedField(
        read_only=True, source="cognitive_contrast_cogatlas")
    map_type = serializers.SerializerMethodField()
    analysis_level = serializers.SerializerMethodField()

    def get_map_type(self, obj):
        return obj.get_map_type_display()

    def get_analysis_level(self, obj):
        return obj.get_analysis_level_display()

    class Meta:
        model = StatisticMap
        exclude = ['polymorphic_ctype', 'ignore_file_warning', 'data']

    def to_representation(self, obj):
        ret = super(ImageSerializer, self).to_representation(obj)
        for field_name, value in obj.data.items():
            if field_name not in ret:
                ret[field_name] = value
        return ret


class NIDMResultStatisticMapSerializer(ImageSerializer):

    nidm_results = HyperlinkedRelatedURL(read_only=True)
    description = NIDMDescriptionSerializedField(source='get_absolute_url')
    map_type = serializers.SerializerMethodField()
    analysis_level = serializers.SerializerMethodField()

    def get_map_type(self, obj):
        return obj.get_map_type_display()

    def get_analysis_level(self, obj):
        return obj.get_analysis_level_display()

    class Meta:
        model = NIDMResultStatisticMap
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        return super(ImageSerializer, self).to_representation(obj)


class AtlasSerializer(ImageSerializer):

    label_description_file = HyperlinkedFileField()

    class Meta:
        model = Atlas
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        return super(ImageSerializer, self).to_representation(obj)


class NIDMResultsSerializer(serializers.ModelSerializer):
    zip_file = HyperlinkedFileField()
    ttl_file = HyperlinkedFileField()
    provn_file = HyperlinkedFileField()
    statmaps = ImageSerializer(many=True, source='nidmresultstatisticmap_set')

    class Meta:
        model = NIDMResults
        exclude = ['id']


class CollectionSerializer(serializers.ModelSerializer):
    url = HyperlinkedImageURL(source='get_absolute_url', read_only=True)
    owner = serializers.ReadOnlyField(source='owner.id')
    images = ImageSerializer(many=True, source='image_set')
    nidm_results = NIDMResultsSerializer(many=True, source='nidmresults_set')
    contributors = SerializedContributors(required=False)
    owner_name = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        return obj.owner.username

    class Meta:
        model = Collection
        exclude = ['private_token', 'private', 'images', 'nidm_results']


class ImageViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):

    queryset = Image.objects.filter(collection__private=False)
    serializer_class = ImageSerializer

    def _get_api_image(self, request, pk=None):
        private_url = re.match(r'^[A-Z]{8}\-\d+$', pk)
        if private_url:
            collection_cid, pk = pk.split('-')
        else:
            base_image = self.get_object()
            collection_cid = base_image.collection.id
        return get_image(pk, collection_cid, request, mode='api')

    @detail_route()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the Datatables plugin. '''
        image = self._get_api_image(request, pk)
        data = ImageSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date',
                                                    'description', 'add_date'])

    def retrieve(self, request, pk=None):
        image = self._get_api_image(request, pk)
        data = ImageSerializer(image, context={'request': request}).data
        return Response(data)


class AtlasViewSet(ImageViewSet):
    queryset = Atlas.objects.filter(collection__private=False)
    serializer_class = AtlasSerializer

    @detail_route()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the Datatables plugin. '''
        image = self._get_api_image(request, pk)
        data = AtlasSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date',
                                                    'description', 'add_date'])

    @detail_route()
    def regions_table(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the
        object for the regions_table plugin. '''
        image = self._get_api_image(request, pk)
        xmlFile = image.label_description_file
        xmlFile.open()
        root = ET.fromstring(xmlFile.read())
        xmlFile.close()
        lines = root.find('data').findall('label')
        indices = [int(line.get('index')) + 1 for line in lines]
        regions = [line.text.split(
            '(')[0].replace("'", '').rstrip(' ').lower() for line in lines]
        return Response(
            {'aaData': zip(indices, regions)})

    @list_route()
    def atlas_query_region(self, request, pk=None):
        ''' Returns a dictionary containing a list of voxels that match the searched term (or related searches) in the specified atlas.\n
        Parameters: region, collection, atlas \n
        Example: '/api/atlases/atlas_query_region/?region=middle frontal gyrus&collection=Harvard-Oxford cortical and subcortical structural atlases&atlas=HarvardOxford cort maxprob thr25 1mm' '''
        search = request.GET.get('region', '')
        atlas = request.GET.get('atlas', '').replace('\'', '')
        collection = name = request.GET.get('collection', '')
        neurovault_root = os.path.dirname(
            os.path.dirname(os.path.realpath(__file__)))
        try:
            collection_object = Collection.objects.filter(name=collection)[0]
        except IndexError:
            return JSONResponse('error: could not find collection: %s' % collection, status=400)
        try:
            atlas_object = Atlas.objects.filter(
                name=atlas, collection=collection_object)[0]
            atlas_image = atlas_object.file
            atlas_xml = atlas_object.label_description_file
        except IndexError:
            return JSONResponse('could not find %s' % atlas, status=400)
        if request.method == 'GET':
            atlas_xml.open()
            root = ET.fromstring(atlas_xml.read())
            atlas_xml.close()
            atlasRegions = [x.text.lower()
                            for x in root.find('data').findall('label')]
            if search in atlasRegions:
                searchList = [search]
            else:
                synonymsDict = {}
                with open(os.path.join(neurovault_root, 'neurovault/apps/statmaps/NIFgraph.pkl'), 'rb') as input:
                    graph = pickle.load(input)
                for atlasRegion in atlasRegions:
                    synonymsDict[atlasRegion] = getSynonyms(atlasRegion)
                try:
                    searchList = toAtlas(
                        search, graph, atlasRegions, synonymsDict)
                except ValueError:
                    return Response('error: region not in atlas or ontology', status=400)
                if searchList == 'none':
                    return Response('error: could not map specified region to region in specified atlas', status=400)
            try:
                data = {
                    'voxels': getAtlasVoxels(searchList, atlas_image, atlas_xml)}
            except ValueError:
                return Response('error: region not in atlas', status=400)

            return Response(data)

    @list_route()
    def atlas_query_voxel(self, request, pk=None):
        ''' Returns the region name that matches specified coordinates in the specified atlas.\n
        Parameters: x, y, z, collection, atlas \n
        Example: '/api/atlases/atlas_query_voxel/?x=30&y=30&z=30&collection=Harvard-Oxford cortical and subcortical structural atlases&atlas=HarvardOxford cort maxprob thr25 1mm' '''
        X = request.GET.get('x', '')
        Y = request.GET.get('y', '')
        Z = request.GET.get('z', '')
        collection = name = request.GET.get('collection', '')
        atlas = request.GET.get('atlas', '').replace('\'', '')
        try:
            collection_object = Collection.objects.filter(name=collection)[0]
        except IndexError:
            return JSONResponse('error: could not find collection: %s' % collection, status=400)
        try:
            print atlas
            print[x.name for x in Atlas.objects.filter(collection=collection_object)]
            atlas_object = Atlas.objects.filter(
                name=atlas, collection=collection_object)[0]
            atlas_image = atlas_object.file
            atlas_xml = atlas_object.label_description_file
        except IndexError:
            return JSONResponse('error: could not find atlas: %s' % atlas, status=400)
        try:
            data = voxelToRegion(X, Y, Z, atlas_image, atlas_xml)
        except IndexError:
            return JSONResponse('error: one or more coordinates are out of range', status=400)
        return Response(data)


class CollectionViewSet(mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):

    queryset = Collection.objects.filter(private=False)
    filter_fields = ('name', 'DOI', 'owner')
    serializer_class = CollectionSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    @detail_route()
    def datatable(self, request, pk=None):
        collection = get_collection(pk, request, mode='api')
        data = CollectionSerializer(
            collection, context={'request': request}).data
        if data and 'description' in data and data['description']:
            data['description'] = data['description'].replace('\n', '<br />')
        return APIHelper.wrap_for_datatables(data, ['owner', 'modify_date', 'images'])

    @detail_route()
    def images(self, request, pk=None):
        collection = get_collection(pk, request, mode='api')
        queryset = Image.objects.filter(collection=collection)
        paginator = StandardResultPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ImageSerializer(
            page, context={'request': request}, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        collection = get_collection(pk, request, mode='api')
        data = CollectionSerializer(
            collection, context={'request': request}).data
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


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


oauth_urlpatterns = [
    url(r'^authorize/$', oauth_views.AuthorizationView.as_view(),
        name="authorize"),
    url(r'^token/$', oauth_views.TokenView.as_view(),
        name="token"),
    url(r'^revoke_token/$', oauth_views.RevokeTokenView.as_view(),
        name="revoke-token"),
]

urlpatterns = patterns('',
                       url('', include(
                           'social.apps.django_app.urls', namespace='social')),
                       url(r'^', include('neurovault.apps.main.urls')),
                       url(r'^', include('neurovault.apps.statmaps.urls')),
                       url(r'^accounts/',
                           include('neurovault.apps.users.urls')),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^api/', include(router.urls)),
                       url(r'^api-auth/', include(
                           'rest_framework.urls', namespace='rest_framework')),
                       url(r'^o/', include((oauth_urlpatterns,
                                            'oauth2_provider',
                                            'oauth2_provider'))),
                       )

if settings.DEBUG:
    urlpatterns += patterns('',
                            url(r'^(?P<path>favicon\.ico)$', 'django.views.static.serve', {
                                'document_root': os.path.join(settings.STATIC_ROOT, 'images')}),
                            )
