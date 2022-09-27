from typing import get_type_hints

from django.core.validators import (
    DecimalValidator, EmailValidator, MaxLengthValidator, MaxValueValidator,
    MinLengthValidator, MinValueValidator, URLValidator
)
from django.db.models import fields
from django.utils.encoding import force_str
from rest_framework import serializers
from rest_framework.compat import uritemplate
from rest_framework.settings import api_settings
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.schemas.utils import get_pk_description, is_list_view


TYPE_MAPPING = {
        int: 'integer',
        str: 'string',
        list: 'array',
        bool: 'boolean',
    }

class OpenAPISchema(AutoSchema):

    def __init__(self, tags=None, operation_id_base=None, component_name=None):
        """
        :param operation_id_base: user-defined name in operationId. If empty, it will be deducted from the Model/Serializer/View name.
        :param component_name: user-defined component's name. If empty, it will be deducted from the Serializer's class name.
        """
        super().__init__(tags=['neurovault'], operation_id_base=operation_id_base, component_name=component_name)

    #JK HACK: interpret path parameters as correct type
    def get_path_parameters(self, path, method):
        """
        Return a list of parameters from templated path variables.
        """
        assert uritemplate, '`uritemplate` must be installed for OpenAPI schema support.'

        model = getattr(getattr(self.view, 'queryset', None), 'model', None)
        parameters = []

        for variable in uritemplate.variables(path):
            description = ''
            if model is not None:  # TODO: test this.
                # Attempt to infer a field description if possible.
                try:
                    model_field = model._meta.get_field(variable)
                except Exception:
                    model_field = None

                if model_field is not None and model_field.help_text:
                    description = force_str(model_field.help_text)
                elif model_field is not None and model_field.primary_key:
                    description = get_pk_description(model, model_field)

            if isinstance(model_field, fields.AutoField):
                schema = {'type': 'integer'}
            else:
                schema = {'type': 'string'}

            parameter = {
                "name": variable,
                "in": "path",
                "required": True,
                "description": description,
                "schema": schema,
            }
            parameters.append(parameter)

        return parameters

    def map_choicefield(self, field):
        mapping = super().map_choicefield(field)
        if mapping['type'] == 'boolean':
            mapping.pop('enum')
        return mapping

    def map_field(self, field):
        # JK HACK: use type hints to discover the type of the field
        if isinstance(field, serializers.SerializerMethodField):
            type_hint = get_type_hints(
                getattr(field.parent, field.method_name)
            )['return']
            return {'type': TYPE_MAPPING[type_hint]}
        else:
            return super().map_field(field)
        
    def map_field_validators(self, field, schema):
        """
        map field validators
        """
        super().map_field_validators(field, schema)
        # JK: HACK REGEX is too long to be interpreted by code-generator
        schema.pop('pattern', None)

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
