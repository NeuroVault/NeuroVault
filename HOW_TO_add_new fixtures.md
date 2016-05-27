## How to add new data to fixtures?

### Generating new fixtures

If you want to do create your data-fixture from scratch (clean Neurovault), you should comment the data loading lines in `run_uwsgi.sh`.
Fork and clone in your local https://github.com/NeuroVault/neurovault_data/

1. Fill Neurovault with desirabled data.
2. Run `docker exec -ti neurovault_uwsgi_1 /bin/bash` to enter the docker instance
3. Run `./manage.py dumpdata --natural-foreign > yourfixture.json` . This will save the fixture info in a JSON file. There are [many options](https://docs.djangoproject.com/en/1.9/ref/django-admin/#dumpdata) for fixture exporting that maybe fit your purposes 
*Warning: you will probably have to modify the JSON by yourself to avoid some errors that could arise when loading it*
4. Create a folder in `neurovault_data/fixtures` with the name of your fixture and copy the JSON into it. Create a subfolder `/media` and copy the data from the docker-image in `/var/www/image_data/*` into it.
5. Zip the folder in `neurovault_data/fixtures` and PR to upstream. 
6. Modify the `run_uwsgi.sh` file to load your data: `python manage.py download_fixtures YOURFIXTURENAME`