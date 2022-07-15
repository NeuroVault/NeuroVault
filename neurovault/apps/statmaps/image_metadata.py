import functools
import json
import os
import re
from collections import defaultdict
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey

from .models import StatisticMap, Image


class MetadataGridValidationError(ValidationError):

    def __init__(self, items_messages_dict):
        self.items_messages_dict = items_messages_dict


def error_response(exception):
    data = None

    if hasattr(exception, 'items_messages_dict'):
        data = {'messages': exception.items_messages_dict}
    else:
        data = {'message': exception.message}

    return {'data': data, 'status': 400}


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


def file_basename(image_obj):
    return os.path.basename(image_obj.file.name)


def clean_u_prefix(s):
    return re.sub(r'u(\'[^\']+?\')', '\\1', s)


def to_verbose_name(obj, field_name):
    return obj._meta.get_field_by_name(field_name)[0].verbose_name.capitalize()


def prepare_messages(obj, message_dict):
    return dict((to_verbose_name(obj, field_name), list(map(clean_u_prefix, v)))
                for field_name, v in list(message_dict.items()))


def wrap_error(value):
    return "Value '%s' is not a valid choice." % value


def pair_data_and_objects(metadata_dict, image_obj_dict):
    extra_files = diff_dicts(image_obj_dict, metadata_dict)

    if extra_files:
        raise ValidationError(
            "Missing metadata for %s. Specify metadata rows "
            "for every image in the collection." % ', '.join(extra_files))

    for image_filename, metadata in list(metadata_dict.items()):
        image_obj = image_obj_dict.get(image_filename)
        if not image_obj:
            raise ValidationError('File is not found in the collection: %s' %
                                  image_filename,
                                  code='file_not_found')
        yield (metadata, image_obj)


def get_value_from_choices(value, choices):
    return next(x for x in choices if x[1] == value)[0]


def set_object_attribute(obj, key, value):
    field_type = None

    try:
        field_type, _, _, _ = obj._meta.get_field_by_name(key)
    except FieldDoesNotExist:
        raise FieldDoesNotExist("Error in fixed field name in "
                                "get_fixed_fields. Field %s "
                                "doesn't exist." % key)

    if not value and not field_type.empty_strings_allowed:
        # explicit None for empty strings
        value = None

    if isinstance(field_type, ForeignKey) and value:
        model = field_type.related_field.model
        try:
            value = model.objects.get(name=value)
        except model.DoesNotExist:
            raise ValidationError({key: wrap_error(value)})

    elif field_type.choices:
        try:
            value = get_value_from_choices(value, field_type.choices)
        except StopIteration:
            pass  # Delegate validation to the model

    setattr(obj, key, value)


def set_data_attribute(obj, key, value):
    obj.data[key] = value


def set_object_data(image_obj, data):
    image_obj.data = {}
    for key in data:
        value = data[key]

        if key in image_obj.get_fixed_fields():
            set_object_attribute(image_obj, key, value)
        else:
            if key != 'Filename':
                set_data_attribute(image_obj, key, value)


def save_metadata(collection, metadata):
    image_obj_list = []
    image_obj_errors = defaultdict(list)

    metadata_list = convert_to_list(metadata)
    metadata_dict = list_to_dict(metadata_list,
                                 key=lambda x: x['Filename'])

    image_obj_list = collection.basecollectionitem_set.instance_of(Image).all()
    image_obj_dict = list_to_dict(image_obj_list,
                                  key=file_basename)

    pairs = pair_data_and_objects(metadata_dict,
                                  image_obj_dict)
    for data, image_obj in pairs:
        try:
            set_object_data(image_obj, data)
            image_obj.full_clean()
        except ValidationError as e:
            image_obj_errors[file_basename(image_obj)].append(
                prepare_messages(image_obj, e.message_dict))

    if image_obj_errors:
        raise MetadataGridValidationError(image_obj_errors)

    for image_obj in image_obj_list:
        image_obj.is_valid = True
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


def get_field_by_name(model, field_name):
    return model._meta.get_field_by_name(field_name)[0]


def get_fixed_fields(model):
    fields = list(map(functools.partial(get_field_by_name, model),
               model.get_fixed_fields()))
    return sorted(fields, key=lambda field: field.blank)


def get_data_headers(image_obj_list):
    index_header = [{'name': 'Filename', 'fixed': True}]
    metadata_keys = list(get_all_metadata_keys(image_obj_list))

    def get_data_source(field):
        if field.choices or isinstance(field, ForeignKey):
            return {'choices': field.name}
        else:
            return None

    def to_fixed_header(field):
        return {
            'name': field.name,
            'verboseName': field.verbose_name.capitalize(),
            'required': not field.blank,
            'datasource': get_data_source(field),
            'fixed': True
        }

    def to_extra_field_header(header):
        return {
            'name': header
        }

    fixed_field_headers = list(map(to_fixed_header,
                              get_fixed_fields(StatisticMap)))

    extra_field_headers = list(map(to_extra_field_header, metadata_keys))

    return index_header + fixed_field_headers + extra_field_headers


def get_images_metadata(image_obj_list):
    metadata_keys = list(get_all_metadata_keys(image_obj_list))
    fixed_fields = get_fixed_fields(StatisticMap)

    def serialize(obj, field):
        value = getattr(obj, field)
        display = getattr(obj, "get_%s_display" % field, None)

        if isinstance(value, Model):
            return str(value)
        elif display:
            return display()
        else:
            return value

    def list_metadata(image):
        data = image.data

        return ([os.path.basename(image.file.name)] +
                [serialize(image, field.name) for field in fixed_fields] +
                [data.get(key, '') for key in metadata_keys])

    return list(map(list_metadata, image_obj_list))


def get_images_filenames(collection):
    return [os.path.basename(image.file.name)
            for image in collection.basecollection_set.instance_of(Image).all()]
