#!/usr/bin/env bash

mkdir -p openapi
python manage.py spectacular --file openapi/openapi-schema.yml
