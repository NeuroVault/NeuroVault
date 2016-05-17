#!/bin/bash
# make sure tha db is up
./wait-for-it.sh db:5432 -- python manage.py migrate --noinput
python manage.py collectstatic --noinput
uwsgi uwsgi.ini