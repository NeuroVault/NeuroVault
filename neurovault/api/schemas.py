from django.core.validators import (
    DecimalValidator, EmailValidator, MaxLengthValidator, MaxValueValidator,
    MinLengthValidator, MinValueValidator, URLValidator
)
from rest_framework import serializers
from rest_framework.settings import api_settings
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.schemas.utils import is_list_view

class OpenAPISchema(AutoSchema):

    def map_field_validators(self, field, schema):
        """
        map field validators
        """
        for v in field.validators:
            # "Formats such as "email", "uuid", and so on, MAY be used even though undefined by this specification."
            # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#data-types
            if isinstance(v, EmailValidator):
                schema['format'] = 'email'
            if isinstance(v, URLValidator):
                schema['format'] = 'uri'
            # JK: HACK REGEX is too long to be interpreted by code-generator
            # if isinstance(v, RegexValidator):
            #     # In Python, the token \Z does what \z does in other engines.
            #     # https://stackoverflow.com/questions/53283160
            #     schema['pattern'] = v.regex.pattern.replace('\\Z', '\\z')
            elif isinstance(v, MaxLengthValidator):
                attr_name = 'maxLength'
                if isinstance(field, serializers.ListField):
                    attr_name = 'maxItems'
                schema[attr_name] = v.limit_value
            elif isinstance(v, MinLengthValidator):
                attr_name = 'minLength'
                if isinstance(field, serializers.ListField):
                    attr_name = 'minItems'
                schema[attr_name] = v.limit_value
            elif isinstance(v, MaxValueValidator):
                schema['maximum'] = v.limit_value
            elif isinstance(v, MinValueValidator):
                schema['minimum'] = v.limit_value
            elif isinstance(v, DecimalValidator) and \
                    not getattr(field, 'coerce_to_string', api_settings.COERCE_DECIMAL_TO_STRING):
                if v.decimal_places:
                    schema['multipleOf'] = float('.' + (v.decimal_places - 1) * '0' + '1')
                if v.max_digits:
                    digits = v.max_digits
                    if v.decimal_places is not None and v.decimal_places > 0:
                        digits -= v.decimal_places
                    schema['maximum'] = int(digits * '9') + 1
                    schema['minimum'] = -schema['maximum']

    def get_operation_id(self, path, method):
        """
        Compute an operation ID from the view type and get_operation_id_base method.
        """
        method_name = getattr(self.view, 'action', method.lower())
        mapped_method = self.method_mapping.get(method.lower(), method.lower())
        if is_list_view(path, method, self.view):
            action = self._to_camel_case('_'.join([mapped_method, 'list']))
        elif method_name not in self.method_mapping and \
             self._to_camel_case(method_name) not in self.method_mapping.values():
            action = self._to_camel_case('_'.join([mapped_method, method_name]))
        elif method_name in self.method_mapping.values():
            action = method_name
        else:
            action = self.method_mapping[method.lower()]

        name = self.get_operation_id_base(path, method, action)

        return action + name

    def get_operation_id_base(self, path, method, action):
        """
        Compute the base part for operation ID from the model, serializer or view name.
        """
        model = getattr(getattr(self.view, 'queryset', None), 'model', None)

        if self.operation_id_base is not None:
            name = self.operation_id_base

        # Try to deduce the ID from the view's model (and add method name).
        elif model is not None:
            name = model.__name__
            # JK HACK: differentiate between collections and my_collections
            if 'my_collections' in path:
                name = "My" + name


        # Try with the serializer class name
        elif self.get_serializer(path, method) is not None:
            name = self.get_serializer(path, method).__class__.__name__
            if name.endswith('Serializer'):
                name = name[:-10]

        # Fallback to the view name
        else:
            name = self.view.__class__.__name__
            if name.endswith('APIView'):
                name = name[:-7]
            elif name.endswith('View'):
                name = name[:-4]

            # Due to camel-casing of classes and `action` being lowercase, apply title in order to find if action truly
            # comes at the end of the name
            if name.endswith(action.title()):  # ListView, UpdateAPIView, ThingDelete ...
                name = name[:-len(action)]

        if action == 'list' and not name.endswith('s'):  # listThings instead of listThing
            name += 's'

        return name
