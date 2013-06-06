from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin
from neurovault.apps.statmaps.models import StatMap, Collection
admin.autodiscover()
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, routers, serializers

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
    
class StatMapSerializer(serializers.HyperlinkedModelSerializer):
    
    file = HyperlinkedFileField(source='file')
    hdr_file = HyperlinkedFileField(source='hdr_file')

    class Meta:
        model = StatMap
        #fields = ('file', 'hdr_file')
        
class StatMapViewSet(viewsets.ModelViewSet):
    queryset = StatMap.objects.all()
    serializer_class = StatMapSerializer
    
class CollectionViewSet(viewsets.ModelViewSet):
    model = Collection

# Routers provide an easy way of automatically determining the URL conf
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'statmaps', StatMapViewSet)
router.register(r'collection', CollectionViewSet)

urlpatterns = patterns('',
    url(r'^$', include('neurovault.apps.main.urls')),
    url(r'^studies/', include('neurovault.apps.statmaps.urls')),
    url(r'^accounts/', include('neurovault.apps.users.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('social_auth.urls')),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))