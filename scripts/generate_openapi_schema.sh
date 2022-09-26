#!/usr/bin/env bash

mkdir -p openapi
./manage.py generateschema --title NeuroVault --description "All ur images R belong to us" --url="neurovault.org" --file openapi/openapi-schema.yml
