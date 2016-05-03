#!/bin/bash
# make sure that db is up
./wait-for-it.sh db:5432 -- python manage.py migrate --noinput
python manage.py collectstatic --noinput

# if the /images dir does not exist, then populate db
if [ ! -d "/var/www/image_data/images" ]; then
    echo "DOWNLOADING"
    python manage.py download_fixtures
    echo "LOADING"
    python manage.py loaddata dumpdata
    echo "COLLECTING"
    python manage.py collectmedia --noinput
    echo "REMOVING"
    rm -R /code/neurovault/apps/statmaps/fixtures
fi
uwsgi uwsgi.ini