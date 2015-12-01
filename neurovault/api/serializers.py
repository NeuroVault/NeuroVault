import os

import pandas as pd

from django.forms.utils import ErrorDict, ErrorList

from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField, StringRelatedField

from neurovault.apps.statmaps.forms import (handle_update_ttl_urls,
                                            ImageValidationMixin,
                                            NIDMResultsValidationMixin,
                                            save_nidm_statmaps)
from neurovault.apps.statmaps.models import (Atlas, Collection, Image,
                                             NIDMResults,
                                             NIDMResultStatisticMap,
                                             StatisticMap)


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
                orderedDict[key] = None
        return orderedDict


class EditableImageSerializer(serializers.ModelSerializer,
                              ImageValidationMixin):

    def validate(self, data):
        self.afni_subbricks = []
        self.afni_tmp = None
        self._errors = ErrorDict()
        self.error_class = ErrorList

        cleaned_data = self.clean_and_validate(data)

        if self.errors:
            raise serializers.ValidationError(self.errors)

        return cleaned_data


class EditableStatisticMapSerializer(EditableImageSerializer):

    class Meta:
        model = StatisticMap
        read_only_fields = ('collection',)


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


class EditableAtlasSerializer(EditableImageSerializer):

    class Meta:
        model = Atlas
        read_only_fields = ('collection',)


class NIDMResultsSerializer(serializers.ModelSerializer):
    zip_file = HyperlinkedFileField()
    ttl_file = HyperlinkedFileField()
    provn_file = HyperlinkedFileField()
    statmaps = ImageSerializer(many=True, source='nidmresultstatisticmap_set')

    class Meta:
        model = NIDMResults
        exclude = ['id']


class EditableNIDMResultsSerializer(serializers.ModelSerializer,
                                    NIDMResultsValidationMixin):

    def validate(self, data):
        return self.clean_and_validate(data)

    def save(self):
        instance = super(EditableNIDMResultsSerializer, self).save()

        save_nidm_statmaps(self.nidm, instance)
        handle_update_ttl_urls(instance)

        return instance

    class Meta:
        model = NIDMResults
        read_only_fields = ('collection',)


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
