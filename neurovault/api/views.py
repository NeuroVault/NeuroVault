import cPickle as pickle
import os
import re
import xml.etree.ElementTree as ET
from django.http import HttpResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.filters import DjangoFilterBackend
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag

from neurovault.apps.statmaps.models import (Atlas, Collection, Image,
                                             NIDMResults)
from neurovault.apps.statmaps.urls import StandardResultPagination
from neurovault.apps.statmaps.utils import get_existing_comparisons
from neurovault.apps.statmaps.views import (get_collection, get_image,
                                            owner_or_contrib)
from neurovault.apps.statmaps.voxel_query_functions import (getAtlasVoxels,
                                                            getSynonyms,
                                                            toAtlas,
                                                            voxelToRegion)
from .serializers import (UserSerializer, AtlasSerializer,
                          CollectionSerializer, EditableAtlasSerializer,
                          EditableNIDMResultsSerializer,
                          EditableStatisticMapSerializer, ImageSerializer,
                          NIDMResultsSerializer, ComparisonSerializer)

from .permissions import (ObjectOnlyPermissions,
                          ObjectOnlyPolymorphicPermissions)


class JSONResponse(HttpResponse):

    """
    An HttpResponse that renders its content into JSON.
    """

    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


class APIHelper:

    """
    Contains generic helper methods to call from various
    serializers and viewsets.
    """
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
        data = dict([(k, v) for k, v in data.items()
                     if v and k not in fields_to_strip])
        return Response(
            {'aaData': zip(data.keys(), data.values())}
        )


class AuthUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class ImageViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   viewsets.GenericViewSet):

    queryset = Image.objects.filter(collection__private=False)
    serializer_class = ImageSerializer
    permission_classes = (ObjectOnlyPolymorphicPermissions,)

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
    permission_classes = (ObjectOnlyPolymorphicPermissions,)

    @detail_route()
    def datatable(self, request, pk=None):
        """
        A wrapper around standard retrieve() request that formats
        the object for the Datatables plugin.
        """
        image = self._get_api_image(request, pk)
        data = AtlasSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date',
                                                    'description', 'add_date'])

    @detail_route()
    def regions_table(self, request, pk=None):
        """
        A wrapper around standard retrieve() request that formats
        the object for the regions_table plugin.
        """
        image = self._get_api_image(request, pk)
        xmlFile = image.label_description_file
        xmlFile.open()
        root = ET.fromstring(xmlFile.read())
        xmlFile.close()
        lines = root.find('data').findall('label')
        if lines[0].get("index"):
            indices = [int(line.get('index')) + 1 for line in lines]
        else:
            indices = [int(line.find('index').text) for line in lines]
        if line.text:
            regions = [line.text.split(
                '(')[0].replace("'", '').rstrip(' ').lower() for line in lines]
        else:
            regions = [line.find("name").text.split(
                '(')[0].replace("'", '').rstrip(' ').lower() for line in lines]
        return Response(
            {'aaData': zip(indices, regions)})

    @list_route()
    def atlas_query_region(self, request, pk=None):
        """
        Returns a dictionary containing a list of voxels that match
        the searched term (or related searches) in the specified atlas.\n
        Parameters: region, collection, atlas \n
        Example: '/api/atlases/atlas_query_region/?region=middle frontal gyrus&collection=Harvard-Oxford cortical and subcortical structural atlases&atlas=HarvardOxford cort maxprob thr25 1mm'
        """
        search = request.GET.get('region', '')
        atlas = request.GET.get('atlas', '').replace('\'', '')
        collection = request.GET.get('collection', '')
        neurovault_root = os.path.dirname(
            os.path.dirname(os.path.realpath(__file__)))
        try:
            collection_object = Collection.objects.filter(name=collection)[0]
        except IndexError:
            return JSONResponse(
                'error: could not find collection: %s' % collection,
                status=400
            )
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
                    return Response(
                        'error: region not in atlas or ontology',
                        status=400
                    )
                if searchList == 'none':
                    return Response(
                        'error: could not map specified region to region in specified atlas',
                        status=400
                    )
            try:
                data = {
                    'voxels': getAtlasVoxels(searchList, atlas_image, atlas_xml)}
            except ValueError:
                return Response('error: region not in atlas', status=400)

            return Response(data)

    @list_route()
    def atlas_query_voxel(self, request, pk=None):
        """
        Returns the region name that matches specified coordinates
        in the specified atlas.\n
        Parameters: x, y, z, collection, atlas \n
        Example: '/api/atlases/atlas_query_voxel/?x=30&y=30&z=30&collection=Harvard-Oxford cortical and subcortical structural atlases&atlas=HarvardOxford cort maxprob thr25 1mm'
        """
        X = request.GET.get('x', '')
        Y = request.GET.get('y', '')
        Z = request.GET.get('z', '')
        collection = request.GET.get('collection', '')
        atlas = request.GET.get('atlas', '').replace('\'', '')
        try:
            collection_object = Collection.objects.filter(name=collection)[0]
        except IndexError:
            return JSONResponse(
                'error: could not find collection: %s' % collection,
                status=400
            )
        try:
            print atlas
            print[x.name
                  for x in Atlas.objects.filter(collection=collection_object)]
            atlas_object = Atlas.objects.filter(
                name=atlas, collection=collection_object)[0]
            atlas_image = atlas_object.file
            atlas_xml = atlas_object.label_description_file
        except IndexError:
            return JSONResponse('error: could not find atlas: %s' % atlas,
                                status=400)
        try:
            data = voxelToRegion(X, Y, Z, atlas_image, atlas_xml)
        except IndexError:
            return JSONResponse(
                'error: one or more coordinates are out of range',
                status=400
            )
        return Response(data)


class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.filter(private=False)
    filter_fields = ('name', 'DOI', 'owner')
    serializer_class = CollectionSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (ObjectOnlyPermissions,)

    @detail_route()
    def datatable(self, request, pk=None):
        collection = get_collection(pk, request, mode='api')
        data = CollectionSerializer(
            collection, context={'request': request}).data
        if data and 'description' in data and data['description']:
            data['description'] = data['description'].replace('\n', '<br />')
        return APIHelper.wrap_for_datatables(data, ['owner', 'modify_date',
                                                    'images'])

    @detail_route(methods=['get', 'post'])
    def images(self, request, pk=None):
        if request.method == 'POST':
            return self.add_item(request, pk, EditableStatisticMapSerializer)

        return self._get_paginated_results(Image, pk, request, ImageSerializer)

    def _get_paginated_results(self, obj_class, pk, request, serializer):
        collection = get_collection(pk, request, mode='api')
        queryset = obj_class.objects.filter(collection=collection)
        paginator = StandardResultPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = serializer(
            page, context={'request': request}, many=True)
        return paginator.get_paginated_response(serializer.data)

    @detail_route(methods=['get', 'post'])
    def atlases(self, request, pk):
        if request.method == 'POST':
            return self.add_item(request, pk, EditableAtlasSerializer)

        return self._get_paginated_results(Atlas, pk, request, AtlasSerializer)

    @detail_route(methods=['get', 'post'])
    def nidm_results(self, request, pk):
        if request.method == 'POST':
            return self.add_item(request, pk, EditableNIDMResultsSerializer)

        return self._get_paginated_results(NIDMResults, pk, request, NIDMResultsSerializer)

    def add_item(self, request, pk, obj_serializer):
        collection = get_collection(pk, request, mode='api')

        if not owner_or_contrib(request, collection):
            self.permission_denied(request)

        obj = obj_serializer.Meta.model(collection=collection)
        serializer = obj_serializer(data=request.data,
                                    instance=obj,
                                    context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        collection = get_collection(pk, request, mode='api')
        data = CollectionSerializer(
            collection, context={'request': request}).data
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MyCollectionsViewSet(CollectionViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Collection.objects.filter(owner=user)


class NIDMResultsViewSet(mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):

    queryset = NIDMResults.objects.filter(collection__private=False)
    serializer_class = NIDMResultsSerializer
    permission_classes = (ObjectOnlyPolymorphicPermissions,)

class ComparisonViewSet(viewsets.ModelViewSet):

    # @detail_route()
    # def datatable(self, request, pk=None):
    #     collection = get_collection(pk, request, mode='api')
    #     data = CollectionSerializer(
    #         collection, context={'request': request}).data
    #     if data and 'description' in data and data['description']:
    #         data['description'] = data['description'].replace('\n', '<br />')
    #     return APIHelper.wrap_for_datatables(data, ['owner', 'modify_date',
    #                                                 'images'])

    max_results = 100
    queryset = get_existing_comparisons(3).extra(select={"abs_score": "abs(similarity_score)"}).order_by(
        "-abs_score")[0:max_results]  # "-" indicates descending
    serializer_class = ComparisonSerializer
    permission_classes = (ObjectOnlyPolymorphicPermissions,)


class TagViewSet(viewsets.ModelViewSet):

    model = Tag

    @detail_route()
    def datatable(self, request, pk=None):
        from django.db.models import Count
        data = Tag.objects.annotate(action_count=Count('action'))
        return APIHelper.wrap_for_datatables(data)

