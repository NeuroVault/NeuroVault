"""Generic mapping between value objects and ORM rows.

Value-object field names equal ORM attnames, so reading and writing a group
of columns is one comprehension.
"""
from dataclasses import fields

from django.db.models.fields.files import FieldFile


def names(cls):
    return tuple(f.name for f in fields(cls))


def value(obj, attname):
    v = getattr(obj, attname)
    return v.name if isinstance(v, FieldFile) else v


def read(obj, cls):
    return cls(**{n: value(obj, n) for n in names(cls)})


def flatten(vo):
    return {n: getattr(vo, n) for n in names(type(vo))}


def assign(obj, values: dict):
    for k, v in values.items():
        setattr(obj, k, v)
