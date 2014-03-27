from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from neurovault.apps.statmaps.models import Image, Collection
admin.autodiscover()
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, routers, serializers
from rest_framework.decorators import link
from rest_framework.response import Response
from taggit.models import Tag

from django import template
template.add_to_builtins('django.templatetags.future')
template.add_to_builtins('django.contrib.staticfiles.templatetags.staticfiles')

class HyperlinkedFileField(serializers.FileField):

    def to_native(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.url)

# ViewSets define the view behavior.


class UserViewSet(viewsets.ModelViewSet):
    model = User


class GroupViewSet(viewsets.ModelViewSet):
    model = Group


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
            { 'aaData': zip(data.keys(), data.values()) }
        )


class ImageSerializer(serializers.HyperlinkedModelSerializer):

    file = HyperlinkedFileField(source='file')

    class Meta:
        model = Image
        # fields = ('file', 'hdr_file')


class CollectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Collection


class ImageViewSet(viewsets.ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer


    @link()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the 
        object for the Datatables plugin. '''
        image = self.get_object()
        data = ImageSerializer(image, context={'request': request}).data
        return APIHelper.wrap_for_datatables(data, ['name', 'modify_date', 'description', 'add_date'])


class CollectionViewSet(viewsets.ModelViewSet):

    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer

    @link()
    def datatable(self, request, pk=None):
        ''' A wrapper around standard retrieve() request that formats the 
        object for the Datatables plugin. '''
        collection = self.get_object()
        data = CollectionSerializer(collection).data
        return APIHelper.wrap_for_datatables(data, ['owner', 'modify_date'])


class TagViewSet(viewsets.ModelViewSet):

    model = Tag

    @link()
    def datatable(self, request, pk=None):
        from django.db.models import Count
        data = Tag.objects.annotate(action_count=Count('action'))
        return APIHelper.wrap_for_datatables(data)


# Routers provide an easy way of automatically determining the URL conf
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'images', ImageViewSet)
router.register(r'collections', CollectionViewSet)

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

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
                           (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
                            'document_root': settings.MEDIA_ROOT}))
