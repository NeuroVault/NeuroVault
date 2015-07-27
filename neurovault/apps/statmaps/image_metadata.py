import os
import re
from collections import defaultdict
import json

from django.core.exceptions import ValidationError
from django.db.models.fields import FieldDoesNotExist
from django.contrib import messages

from .models import StatisticMap


def dict_factory(header_row, row):
    d = {}
    for idx, field_name in enumerate(header_row):
        d[field_name] = row[idx]
    return d


def convert_to_list(data):
    return [dict_factory(data[0], row) for row in data[1:]]


def list_to_dict(iterable, key):
    return dict((key(item), item) for item in iterable)


def diff_dicts(dict_a, dict_b):
    keys = getattr(dict, 'viewkeys', dict.keys)
    return keys(dict_a) - keys(dict_b)


# TODO: add force flag
def pair_data_and_objects(metadata_dict, image_obj_dict):
    extra_files = diff_dicts(image_obj_dict, metadata_dict)

    if extra_files:
        raise ValidationError(
            "Missing metadata for %s. Specify metadata rows "
            "for every image in the collection." % ', '.join(extra_files))

    for image_filename, metadata in metadata_dict.items():
        image_obj = image_obj_dict.get(image_filename)
        if not image_obj:
            raise ValidationError('File is not found in the collection: %s' %
                                  image_filename,
                                  code='file_not_found')
        yield (metadata, image_obj)


def error_response(exception):
    data = None

    if hasattr(exception, 'items_messages_dict'):
        data = {'messages': exception.items_messages_dict}
    else:
        data = {'message': exception.message}

    return {'data': data, 'status': 400}


def clean_u_prefix(s):
    return re.sub(r'u(\'[^\']+?\')', '\\1', s)


def clear_messages(message_dict):
    return dict((k, map(clean_u_prefix, v))
                for k, v in message_dict.items())


class MetadataGridValidationError(ValidationError):

    def __init__(self, items_messages_dict):
        self.items_messages_dict = items_messages_dict


def save_metadata(collection, metadata):
    from django.db.models.fields.related import ForeignKey

    def file_basename(image_obj):
        return os.path.basename(image_obj.file.name)

    image_obj_errors = defaultdict(list)
    image_obj_list = []

    metadata_list = convert_to_list(metadata)
    metadata_dict = list_to_dict(metadata_list,
                                 key=lambda x: x['Filename'])

    image_obj_list = collection.image_set.all()
    image_obj_dict = list_to_dict(image_obj_list,
                                  key=file_basename)

    pairs = pair_data_and_objects(metadata_dict,
                                  image_obj_dict)
    for metadata_item, image_obj in pairs:
        for key in metadata_item:
            field_type = None
            if key in image_obj.get_fixed_fields():
                try:
                    field_type, _, _, _ = image_obj._meta.get_field_by_name(
                        key)
                except FieldDoesNotExist:
                    raise FieldDoesNotExist("Error in fixed field name in "
                                            "get_fixed_fields. Field %s "
                                            "doesn't exist." % key)

                value = metadata_item[key]
                if isinstance(field_type, ForeignKey):
                    value = (
                        field_type
                        .related_field
                        .model
                        .objects
                        .get(name=value)
                    )

                setattr(image_obj, key, value)
            else:
                if key != 'Filename':
                    if not image_obj.data:
                        image_obj.data = {}
                    image_obj.data[key] = metadata_item[key]

        try:
            image_obj.full_clean()
        except ValidationError as e:
            image_obj_errors[file_basename(image_obj)].append(
                clear_messages(e.message_dict))

    if image_obj_errors:
        raise MetadataGridValidationError(image_obj_errors)

    for image_obj in image_obj_list:
        image_obj.save()

    return metadata_list


def handle_post_metadata(request, collection, success_message):
    metadata = json.loads(request.body)

    try:
        metadata_list = save_metadata(collection, metadata)
    except ValidationError as e:
        return error_response(e)

    messages.success(request,
                     success_message,
                     extra_tags='alert-success')

    return {'data': metadata_list, 'status': 200}


def get_all_metadata_keys(image_obj_list):
    return set(key for image in image_obj_list if image.data
               for key in image.data)


def get_images_metadata(collection):
    image_obj_list = collection.image_set.all()
    metadata_keys = list(get_all_metadata_keys(image_obj_list))
    fixed_fields = list(StatisticMap.get_fixed_fields())

    def list_metadata(image):
        data = image.data

        return ([os.path.basename(image.file.name)] +
                [getattr(image, field) for field in fixed_fields] +
                [data.get(key, '') for key in metadata_keys])

    return [['Filename'] + fixed_fields + metadata_keys] + map(list_metadata,
                                                               image_obj_list)


def get_images_filenames(collection):
    return [os.path.basename(image.file.name)
            for image in collection.image_set.all()]
