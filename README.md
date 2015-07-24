# NeuroVault.org
Easy to use web database for human brain statistical maps, atlases and parcellation maps.
## How to set up NeuroVault for local development?

### Installing dependencies
1. Fork the main repository (https://github.com/NeuroVault/NeuroVault)
2. Clone your fork to your computer: `git clone https://github.com/<your_username>/NeuroVault`
  3. *Warning: if you are using OS X you have to clone the repository to a subfolder in your home folder - `/Users/<your_username/...` - otherwise boot2docker will not be able to mount code directories and will fail silently.*
3. Install docker >= 1.6 (If you are using OS X you'll also need boot2docker)
4. Install docker-compose >= 1.2
  5. If you are using OS X and homebrew steps 3 and 4 can be achieved by: `brew update && brew install docker boot2docker docker-compose`
6. Make sure your docker daemon is running (on OS X: `boot2docker init && boot2docker up`)

### Running the server
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
docker build -t neurovault/neurovault_fs -f Dockerfile_freesurfer .
```
# Uptime
<a href="http://www.pingdom.com"><img src="https://share.pingdom.com/banners/8bbaa1a5" alt="Uptime Report for Neurovault: Last 30 days" title="Uptime Report for Neurovault: Last 30 days" width="300" height="165" /></a>
