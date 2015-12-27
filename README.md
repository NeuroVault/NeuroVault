# NeuroVault.org
Easy to use web database for human brain statistical maps, atlases and parcellation maps.
## How to set up NeuroVault for local development?

### Installing dependencies
1. Fork the main repository (https://github.com/NeuroVault/NeuroVault)
2. Clone your fork to your computer: `git clone https://github.com/<your_username>/NeuroVault`
3. Install [Docker Machine](https://docs.docker.com/machine/install-machine/)
4. Register your username/password/email at [Docker Hub](hub.docker.com).
5. From the terminal, create a new docker machine, 'nv': `docker-machine create --driver virtualbox nv`
   * Note: this also starts `nv`; if stopped, you can start by running `docker-machine start nv`.
6. Run `docker-machine env nv && eval "$(docker-machine env nv)"` to start the docker daemon.
   * Note: you can validate by running `docker ps`--should return with no errors.
7. Run `docker login`, using your username/password/email from Step 4.
8. Run `docker pull neurovault/neurovault` to download the latest docker container.
   * Note: to build the container locally, run `docker build -t neurovault/neurovault .` from the (cloned) NeuroVault directory.


### Running the server

If your docker daemon is not running, run:
```
docker-machine start nv
docker-machine env nv && eval "$(docker-machine env nv)
```

Then, run:
```
docker-compose up -d
```

The webpage will be available at 127.0.0.1 (unless you are using boot2docker - then run `boot2docker ip` to figure out which IP address you need to use).

You can also run the server in non detached mode (shows all the logs in realtime).
```
docker-compose up
```
### Stopping the server
```
docker-compose stop
```
### Restarting the server
After making changes to the code you need to restart the server (but just the uwsgi and celery components):
```
docker-compose restart nginx uwsgi worker
```
### Reseting the server
If you would like to reset the server and clean the database:
```
docker-compose stop
docker-compose rm
docker-compose up
```
### Running Django shell
```
docker-compose run --rm uwsgi python manage.py shell
```
### Running tests
```
docker-compose run --rm uwsgi python manage.py test
```
### Updating docker image
If you add a dependency to requirements.txt or modify Dockerfile you will need to rebuild the docker image
```
docker build -t neurovault/neurovault .
```

### Using pycortex
To use pycortex you will need a different image (that includes FreeSurfer). Just change "neurovault/neurovault" with "neurovault/neurovault_fs" in docker-compose.yml. This image is significantly bigger and will take longer to download.

You can also build it locally
```
docker build -t neurovault/neurovault_fs -f fs_docker/Dockerfile .
```
# Uptime
<a href="http://www.pingdom.com"><img src="https://share.pingdom.com/banners/8bbaa1a5" alt="Uptime Report for Neurovault: Last 30 days" title="Uptime Report for Neurovault: Last 30 days" width="300" height="165" /></a>
