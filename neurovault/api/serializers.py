import os
import json
import pandas as pd
from django.contrib.auth.models import User
from django.forms.utils import ErrorDict, ErrorList
from django.utils.http import urlquote
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField, StringRelatedField

from neurovault.apps.statmaps.forms import (
    handle_update_ttl_urls,
    ImageValidationMixin,
    NIDMResultsValidationMixin,
    save_nidm_statmaps
)

from neurovault.apps.statmaps.models import (
    Atlas,
    BaseCollectionItem,
    CognitiveAtlasTask,
    CognitiveAtlasContrast,
    Collection,
    NIDMResults,
    NIDMResultStatisticMap,
    StatisticMap
)

from neurovault.utils import strip, logical_xor
from neurovault.apps.statmaps.utils import get_paper_properties


class HyperlinkedFileField(serializers.FileField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(urlquote(value.url))


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
        if value and self.parent.instance is not None:
            parent = self.parent.instance.nidm_results.name
            fname = os.path.split(self.parent.instance.file.name)[-1]
            return 'NIDM Results: {0}.zip > {1}'.format(parent, fname)


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class ImageSerializer(serializers.HyperlinkedModelSerializer,
                      ImageValidationMixin):

    id = serializers.ReadOnlyField()
    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    collection_id = serializers.ReadOnlyField()
    url = HyperlinkedImageURL(source='get_absolute_url',
                              read_only=True)
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = BaseCollectionItem
        exclude = ['polymorphic_ctype']

    def __init__(self, *args, **kwargs):
        super(ImageSerializer, self).__init__(*args, **kwargs)
        initial_data = getattr(self, 'initial_data', None)
        if initial_data:
            self._metadata_dict = self.extract_metadata_fields(
                self.initial_data, self._writable_fields
            )

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
        elif isinstance(obj, NIDMResults):
            serializer = NIDMResultsSerializer
            image_type = 'NIDM Results'

        print image_type, obj.pk

        orderedDict = serializer(obj, context={
            'request': self.context['request']}).to_representation(obj)
        orderedDict['image_type'] = image_type
        for key, val in orderedDict.iteritems():
            if pd.isnull(val):
                orderedDict[key] = None
        return orderedDict

    def extract_metadata_fields(self, initial_data, writable_fields):
        field_name_set = set(f.field_name for f in writable_fields)
        metadata_field_set = initial_data.viewkeys() - field_name_set
        return {key: initial_data[key] for key in metadata_field_set}

    def validate(self, data):
        self.afni_subbricks = []
        self.afni_tmp = None
        self._errors = ErrorDict()
        self.error_class = ErrorList

        cleaned_data = self.clean_and_validate(data)

        if self.errors:
            raise serializers.ValidationError(self.errors)

        return cleaned_data

    def save(self, *args, **kwargs):
        metadata_dict = getattr(self, '_metadata_dict', None)
        if metadata_dict:
            data = self.instance.data.copy()
            data.update(self._metadata_dict)
            kwargs['data'] = data

        super(ImageSerializer, self).save(*args, **kwargs)


class EditableStatisticMapSerializer(ImageSerializer):
    cognitive_paradigm_cogatlas = PrimaryKeyRelatedField(
        queryset=CognitiveAtlasTask.objects.all(),
        allow_null=True,
        required=False
    )
    cognitive_contrast_cogatlas = PrimaryKeyRelatedField(
        queryset=CognitiveAtlasContrast.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = StatisticMap
        read_only_fields = ('collection',)
        exclude = ['polymorphic_ctype', 'ignore_file_warning', 'data']


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

    def value_to_python(self, value):
        if not value:
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def to_representation(self, obj):
        ret = super(ImageSerializer, self).to_representation(obj)
        for field_name, value in obj.data.items():
            if field_name not in ret:
                ret[field_name] = self.value_to_python(value)
        return ret


class NIDMResultStatisticMapSerializer(ImageSerializer):

    nidm_results = HyperlinkedRelatedURL(read_only=True)
    nidm_results_ttl = serializers.SerializerMethodField()
    description = NIDMDescriptionSerializedField(source='get_absolute_url')
    map_type = serializers.SerializerMethodField()
    analysis_level = serializers.SerializerMethodField()

    def get_map_type(self, obj):
        return obj.get_map_type_display()

    def get_analysis_level(self, obj):
        return obj.get_analysis_level_display()

    def get_nidm_results_ttl(self, obj):
        return self.context['request'].build_absolute_uri(
            obj.nidm_results.ttl_file.url
        )

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


class EditableAtlasSerializer(ImageSerializer):

    class Meta:
        model = Atlas
        read_only_fields = ('collection',)


class NIDMResultsSerializer(serializers.ModelSerializer,
                            NIDMResultsValidationMixin):
    zip_file = HyperlinkedFileField()
    ttl_file = HyperlinkedFileField(required=False)
    statmaps = ImageSerializer(many=True, source='nidmresultstatisticmap_set')

    def validate(self, data):
        data['collection'] = self.instance.collection
        return self.clean_and_validate(data)

    def save(self):
        instance = super(NIDMResultsSerializer, self).save()
        nidm = getattr(self, 'nidm', False)

        if nidm:
            # Handle file upload
            save_nidm_statmaps(nidm, instance)
            handle_update_ttl_urls(instance)

        return instance

    class Meta:
        model = NIDMResults
        exclude = ['id']
        read_only_fields = ('collection',)


class EditableNIDMResultsSerializer(serializers.ModelSerializer,
                                    NIDMResultsValidationMixin):

    def validate(self, data):
        data['collection'] = self.instance.collection
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
    images = ImageSerializer(many=True, source='basecollectionitem_set')
    contributors = SerializedContributors(required=False)
    owner_name = serializers.SerializerMethodField()
    number_of_images = serializers.SerializerMethodField('num_im')

    def num_im(self, obj):
        return obj.basecollectionitem_set.count()

    def get_owner_name(self, obj):
        return obj.owner.username

    def validate(self, data):
        doi = strip(data.get('DOI'))
        name = strip(data.get('name'))

        if not self.instance:
            if not (logical_xor(doi, name)):
                raise serializers.ValidationError(
                    'Specify either "name" or "DOI"'
                )

        if doi:
            try:
                (name, authors,
                 paper_url, _, journal_name) = get_paper_properties(doi)
                data['name'] = name
                data['authors'] = authors
                data['paper_url'] = paper_url
                data['journal_name'] = journal_name
            except:
                raise serializers.ValidationError('Could not resolve DOI')
        return data

    class Meta:
        model = Collection
        exclude = ['private_token', 'private', 'images']
        # Override `required` to allow name fetching by DOI
        extra_kwargs = {'name': {'required': False}}
