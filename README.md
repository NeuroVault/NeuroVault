# NeuroVault.org

[![Join the chat at https://gitter.im/NeuroVault/NeuroVault](https://badges.gitter.im/NeuroVault/NeuroVault.svg)](https://gitter.im/NeuroVault/NeuroVault?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Blog: https://neurovault.github.io/

Easy to use web database for brain statistical maps, atlases and parcellation maps.
## How to set up NeuroVault for local development?

### Installing dependencies
1. Fork the main repository (https://github.com/NeuroVault/NeuroVault)
2. Clone your fork to your computer: `git clone https://github.com/<your_username>/NeuroVault`
3. Install docker >= 20
4. Install docker-compose >= 1.29
5. Make sure your docker daemon is running and environment variables are configured (`cp .env.example .env`)

### Running the server
```
docker-compose up -d
```
The webpage will be available at http://localhost:8000/

### Migrating the database
```
docker-compose exec django python manage.py migrate
```
The first time you run the application, you must migrate the db. You must also do this if you update any database models.

### Creating super user
```
docker-compose exec django python manage.py createsuperuser
````
This will create a super user that you can use to test the application

### Stopping the server
```
docker-compose stop
```
### Restarting the server
After making changes to the code you need to restart the server (but just the uwsgi and celery components):
```
docker-compose restart nginx django worker
```
### Resetting the server
If you would like to reset the server and clean the database:
```
docker-compose stop
docker-compose rm
docker-compose up
```
### Running Django shell
```
docker-compose run --rm django python manage.py shell
```
### Running tests
```
docker-compose run --rm django python manage.py test
```
### Updating Docker image
If you add a dependency (e.g., a new pip install) or modify the Dockerfile in any way, you will need to rebuild the docker image:

```
docker-compose build django
```

### Using pycortex
To use pycortex you will need a different image (that includes FreeSurfer). Just change "neurovault/neurovault" with "neurovault/neurovault_fs" in docker-compose.yml. This image is significantly bigger and will take longer to download.

You can also build it locally
```
docker build -t neurovault/neurovault_fs -f fs_docker/Dockerfile .
```
Pay special close attention that the command above ends with a `.` to indicate the present working directory, the base of the code repository.
