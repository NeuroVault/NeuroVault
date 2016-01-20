from rest_framework.renderers import JSONRenderer


class ExplicitUnicodeJSONRenderer(JSONRenderer):
    charset = 'utf-8'