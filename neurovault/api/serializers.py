import os
import json
from typing_extensions import dataclass_transform
import pandas as pd
from urllib.parse import quote
from django.contrib.auth.models import User
from django.forms.utils import ErrorDict, ErrorList
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField, StringRelatedField

from neurovault.application.ports import Actor
from neurovault.application.services.bundles import NamedBytes
from neurovault.application.services.items import ImageFilesInput
from neurovault.bootstrap import services
from neurovault.domain.errors import DomainValidationError

from django.contrib.contenttypes.models import ContentType

from neurovault.apps.statmaps.models import (
    CognitiveAtlasTask,
    CognitiveAtlasContrast,
    Collection,
    Item,
    NIDMBundle,
)

from neurovault.utils import strip, logical_xor
from neurovault.api import fields as api_fields

FILE_FIELDS = ("file", "surface_left_file", "surface_right_file", "label_description_file")
FOREIGN_KEYS = ("cognitive_paradigm_cogatlas", "cognitive_contrast_cogatlas")


class ContentTypeIdField(serializers.SerializerMethodField):
    """The `polymorphic_ctype` key the API has always emitted: a content type id."""

    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        super().__init__(**kwargs)

    def to_representation(self, value):
        return ContentType.objects.get_by_natural_key("statmaps", self.model_name).pk


def actor_of(serializer):
    user = serializer.context["request"].user
    if not user.is_authenticated:
        return Actor(None)
    return Actor(user.pk, user.is_superuser)


def image_command(validated_data):
    """(column changes, file uploads) from validated image data."""
    changes, files = {}, ImageFilesInput()
    for key, value in validated_data.items():
        if key in FILE_FIELDS:
            if value:
                setattr(files, key, value)
            else:
                changes[key] = value
        elif key in FOREIGN_KEYS:
            changes[key + "_id"] = value.pk if value is not None else None
        elif key in ("collection", "polymorphic_ctype", "kind"):
            continue
        else:
            changes[key] = value
    return changes, files


class HyperlinkedFileField(serializers.FileField):
    def to_representation(self, value):
        if value:
            request = self.context.get("request", None)
            return request.build_absolute_uri(quote(value.url))


class HyperlinkedDownloadURL(serializers.RelatedField):
    def to_representation(self, value):
        if value:
            request = self.context.get("request", None)
            return request.build_absolute_uri(value + "download")


class HyperlinkedRelatedURL(serializers.RelatedField):
    def to_representation(self, value):
        if value:
            request = self.context.get("request", None)
            return request.build_absolute_uri(value.get_absolute_url())


class HyperlinkedImageURL(serializers.CharField):
    def to_representation(self, value):
        if value:
            request = self.context.get("request", None)
            return request.build_absolute_uri(value)


class SerializedContributors(serializers.CharField):
    def to_representation(self, value):
        if value:
            return ", ".join([v.username for v in value.all()])


class NIDMDescriptionSerializedField(serializers.CharField):
    def to_representation(self, value):
        if value and self.parent.instance is not None:
            parent = self.parent.instance.source_bundle.name
            fname = os.path.split(self.parent.instance.file.name)[-1]
            return "NIDM Results: {0}.zip > {1}".format(parent, fname)


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    collection_id = serializers.ReadOnlyField()
    url = HyperlinkedImageURL(source="get_absolute_url", read_only=True)
    file_size = serializers.SerializerMethodField()

    kind = None  # set by the serializers that create items

    class Meta:
        model = Item
        fields = api_fields.IMAGE_FIELDS

    def __init__(self, *args, **kwargs):
        super(ImageSerializer, self).__init__(*args, **kwargs)
        initial_data = getattr(self, "initial_data", None)
        if initial_data:
            self._metadata_dict = self.extract_metadata_fields(
                self.initial_data, self._writable_fields
            )

    def get_file_size(self, obj):
        try:
            return obj.file.size
        except OSError as e:
            return 0

    def to_representation(self, obj):
        """Dispatch on the kind of item, adding the legacy `image_type`."""
        if isinstance(obj, NIDMBundle):
            serializer = NIDMResultsSerializer
            image_type = "NIDM Results"
        elif obj.kind == Item.STATMAP and obj.source_bundle_id is None:
            serializer = StatisticMapSerializer
            image_type = "statistic_map"
        elif obj.kind == Item.ATLAS:
            serializer = AtlasSerializer
            image_type = "atlas"
        elif obj.kind == Item.STATMAP:
            serializer = NIDMResultStatisticMapSerializer
            image_type = "NIDM results statistic map"

        orderedDict = serializer(
            obj, context={"request": self.context["request"]}
        ).to_representation(obj)
        orderedDict["image_type"] = image_type
        for key, val in orderedDict.items():
            if pd.isnull(val):
                orderedDict[key] = None
        return orderedDict

    def extract_metadata_fields(self, initial_data, writable_fields):
        field_name_set = set(f.field_name for f in writable_fields)
        metadata_field_set = initial_data.keys() - field_name_set
        return {key: initial_data[key] for key in metadata_field_set}

    def validate(self, data):
        left, right = data.get("surface_left_file"), data.get("surface_right_file")
        if left and right:
            data["data_origin"] = "surface"
            try:
                projected = services().items.project_surfaces(left, right, data["name"])
            except DomainValidationError as e:
                raise serializers.ValidationError(e.errors)
            data["surface_left_file"] = NamedBytes(projected.left_name, projected.left)
            data["surface_right_file"] = NamedBytes(projected.right_name, projected.right)
            data["file"] = NamedBytes(projected.volume_name, projected.volume)
        return data

    def save(self, *args, **kwargs):
        metadata_dict = getattr(self, "_metadata_dict", None)
        if metadata_dict:
            data = self.instance.data.copy() if self.instance.data else {}
            data.update(self._metadata_dict)
            kwargs["data"] = data
        return super(ImageSerializer, self).save(*args, **kwargs)

    def update(self, instance, validated_data):
        """Add (unsaved instance from add_item) or change an image."""
        changes, files = image_command(validated_data)
        items = services().items
        if instance.pk is None:
            item_id = items.add(actor_of(self), instance.collection_id, self.kind, changes, files)
        else:
            item_id = items.change(actor_of(self), instance.pk, changes, files).id
        return Item.objects.get(pk=item_id)


class EditableStatisticMapSerializer(ImageSerializer):
    cognitive_paradigm_cogatlas = PrimaryKeyRelatedField(
        queryset=CognitiveAtlasTask.objects.all(), allow_null=True, required=False
    )
    cognitive_contrast_cogatlas = PrimaryKeyRelatedField(
        queryset=CognitiveAtlasContrast.objects.all(), allow_null=True, required=False
    )

    kind = Item.STATMAP

    class Meta:
        model = Item
        read_only_fields = ("collection",)
        fields = api_fields.EDITABLE_STATISTIC_MAP_FIELDS
        extra_kwargs = {
            "map_type": {"required": True, "allow_null": False},
            "modality": {"required": True, "allow_null": False},
        }


class StatisticMapSerializer(ImageSerializer):
    cognitive_paradigm_cogatlas = StringRelatedField(read_only=True)
    cognitive_paradigm_cogatlas_id = PrimaryKeyRelatedField(
        read_only=True, source="cognitive_paradigm_cogatlas"
    )
    cognitive_contrast_cogatlas = StringRelatedField(read_only=True)
    cognitive_contrast_cogatlas_id = PrimaryKeyRelatedField(
        read_only=True, source="cognitive_contrast_cogatlas"
    )
    map_type = serializers.SerializerMethodField()
    analysis_level = serializers.SerializerMethodField()

    def get_map_type(self, obj):
        return obj.get_map_type_display()

    def get_analysis_level(self, obj):
        return obj.get_analysis_level_display()

    class Meta:
        model = Item
        fields = api_fields.STATISTIC_MAP_FIELDS

    def value_to_python(self, value):
        if not value:
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def to_representation(self, obj):
        ret = super(ImageSerializer, self).to_representation(obj)
        try:
            for field_name, value in list(obj.data.items()):
                if field_name not in ret:
                    ret[field_name] = self.value_to_python(value)
        except AttributeError:
            pass
        return ret


class NIDMResultStatisticMapSerializer(ImageSerializer):
    nidm_results = HyperlinkedRelatedURL(read_only=True, source="source_bundle")
    nidm_results_ttl = serializers.SerializerMethodField()
    description = NIDMDescriptionSerializedField(source="get_absolute_url")
    map_type = serializers.SerializerMethodField()
    analysis_level = serializers.SerializerMethodField()

    def get_map_type(self, obj):
        return obj.get_map_type_display()

    def get_analysis_level(self, obj):
        return obj.get_analysis_level_display()

    def get_nidm_results_ttl(self, obj):
        return self.context["request"].build_absolute_uri(obj.source_bundle.ttl_file.url)

    class Meta:
        model = Item
        fields = api_fields.NIDM_RESULT_STATISTIC_MAP_FIELDS

    def to_representation(self, obj):
        return super(ImageSerializer, self).to_representation(obj)


class AtlasSerializer(ImageSerializer):
    label_description_file = HyperlinkedFileField()

    class Meta:
        model = Item
        fields = api_fields.ATLAS_FIELDS

    def to_representation(self, obj):
        return super(ImageSerializer, self).to_representation(obj)


class EditableAtlasSerializer(ImageSerializer):
    kind = Item.ATLAS
    polymorphic_ctype = ContentTypeIdField("item")

    class Meta:
        model = Item
        fields = api_fields.EDITABLE_ATLAS_FIELDS
        read_only_fields = ("collection",)
        extra_kwargs = {"label_description_file": {"required": True, "allow_null": False}}


class NIDMResultsCommands:
    """validate/update shared by the NIDM-Results serializers."""

    def validate(self, data):
        data["collection"] = self.instance.collection
        zip_file = data.get("zip_file")
        if zip_file or not getattr(self, "partial", False):
            try:
                self.prepared = services().bundles.prepare(
                    self.instance.collection_id, data["zip_file"], replacing_id=self.instance.pk
                )
            except DomainValidationError as e:
                raise serializers.ValidationError(list(e.errors.values())[0])
            data["name"] = self.prepared.name
        return data

    def update(self, instance, validated_data):
        bundles = services().bundles
        prepared = getattr(self, "prepared", None)
        if prepared is not None:
            bundle_id = bundles.ingest(
                actor_of(self), instance.collection_id, prepared,
                description=validated_data.get("description", instance.description),
                replacing_id=instance.pk,
            )
        else:
            changes = {k: validated_data[k] for k in ("name", "description") if k in validated_data}
            bundle_id = bundles.change(actor_of(self), instance.pk, changes).id
        return NIDMBundle.objects.get(pk=bundle_id)


class NIDMResultsSerializer(serializers.ModelSerializer):
    zip_file = HyperlinkedFileField()
    ttl_file = HyperlinkedFileField(required=False)
    statmaps = ImageSerializer(
        many=True, required=False
    )
    polymorphic_ctype = ContentTypeIdField("nidmbundle")
    url = HyperlinkedImageURL(source="get_absolute_url", read_only=True)

    validate = NIDMResultsCommands.validate
    update = NIDMResultsCommands.update

    class Meta:
        model = NIDMBundle
        fields = api_fields.NIDM_RESULTS_FIELDS
        read_only_fields = ("collection",)


class EditableNIDMResultsSerializer(serializers.ModelSerializer):
    url = HyperlinkedImageURL(source="get_absolute_url", read_only=True)
    polymorphic_ctype = ContentTypeIdField("nidmbundle")

    validate = NIDMResultsCommands.validate
    update = NIDMResultsCommands.update

    class Meta:
        model = NIDMBundle
        read_only_fields = ("collection",)
        fields = api_fields.EDITABLE_NIDM_RESULTS_FIELDS


class CollectionSerializer(serializers.ModelSerializer):
    url = HyperlinkedImageURL(source="get_absolute_url", read_only=True)
    download_url = HyperlinkedDownloadURL(source="get_absolute_url", read_only=True)
    owner = serializers.ReadOnlyField(source="owner.id")
    # images = ImageSerializer(many=True, source='basecollectionitem_set')
    contributors = SerializedContributors(required=False)
    owner_name = serializers.SerializerMethodField()
    number_of_images = serializers.SerializerMethodField("num_im")

    def num_im(self, obj):
        return obj.item_count()

    def get_owner_name(self, obj):
        return obj.owner.username

    def validate(self, data):
        doi = strip(data.get("DOI"))
        name = strip(data.get("name"))

        if not self.instance:
            if not (logical_xor(doi, name)):
                raise serializers.ValidationError('Specify either "name" or "DOI"')

        if doi:
            try:
                completed = services().collections.complete_publication(
                    {"DOI": doi}, require_name=False
                )
                completed.pop("DOI")
                data.update(completed)
            except DomainValidationError:
                raise serializers.ValidationError("Could not resolve DOI")
        return data

    def create(self, validated_data):
        return self._save(None, validated_data)

    def update(self, instance, validated_data):
        return self._save(instance.pk, validated_data)

    def _save(self, collection_id, validated_data):
        changes = dict(validated_data)
        changes.pop("owner", None)
        changes.pop("contributors", None)
        communities = changes.pop("communities", None)
        collection_id = services().collections.save(
            actor_of(self),
            collection_id,
            changes,
            community_ids=[c.pk for c in communities] if communities is not None else None,
        )
        return Collection.objects.get(pk=collection_id)

    class Meta:
        model = Collection
        fields = api_fields.COLLECTION_FIELDS
        # Override `required` to allow name fetching by DOI
        extra_kwargs = {"name": {"required": False}}
