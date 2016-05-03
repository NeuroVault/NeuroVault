#!/bin/bash
# make sure tha db is up
./wait-for-it.sh db:5432 -- python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py download_fixtures
python manage.py loaddata dumpdata
python manage.py collectmedia --noinput
rm -R /code/neurovault/apps/statmaps/fixtures
uwsgi uwsgi.ini