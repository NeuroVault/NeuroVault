from rest_framework.renderers import JSONRenderer


class ExplicitUnicodeJSONRenderer(JSONRenderer):
    charset = "utf-8"
def strip(value):
    if not value:
        return value
    return value.strip()


def logical_xor(a, b):
    return bool(a) ^ bool(b)
