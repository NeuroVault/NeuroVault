#!/usr/bin/env bash

mkdir -p openapi
./manage.py generateschema --title NeuroVault --description "All ur images R belong to us" --file openapi/openapi-schema.yml
