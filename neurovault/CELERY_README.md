# Setting Up Celery for NeuroVault

Celery requires a task server. They recommend rabbitmq (and I tested this for the virtual machine) however django (a database) can also be used (but it's not recommended). The other option is redis, but they don't recommend because it is "susceptible to data loss in event of power failures"  This is really just like a task database or queue. I was going to do rabbit, but Gabriel said do redis, so I will do redis. Celery is python based so we install from pip.

     source /opt/nv_env/bin/activate
     pip install -U celery[redis]
     pip install redis

### Installing redis database

     cd /home/vagrant
     wget http://download.redis.io/redis-stable.tar.gz
     tar xvzf redis-stable.tar.gz
     cd redis-stable
     make
     sudo cp src/redis-server /opt/nv_env/local/bin/
     sudo cp src/redis-cli /opt/nv_env/local/bin/

#### Set up places for config and init script

     sudo mkdir /var/redis
     sudo mkdir /etc/redis
     sudo cp utils/redis_init_script /etc/init.d/redis_6379  # default port is 6379

#### change EXEC and CLIEXEC variables for nv_env
     sudo vim /etc/init.d/redis_6379
     EXEC=/opt/nv_env/local/bin/redis-server
     CLIEXEC=/opt/nv_env/local/bin/redis-cli

#### Now copy config file to etc
     sudo cp redis.conf /etc/redis/6379.conf
     sudo vim /etc/redis/6379.conf

     daemonize yes                         # line 37 change no to yes
     pidfile /var/run/redis_6379.pid       # line 41 pidfile
     logfile "/var/log/redis_6379.log"     # line 103, I added logfile
     dir /var/redis/6379                   # line 187, set working / data directory

#### working directory for redis and data
     sudo mkdir /var/redis/6379
     /opt/nv_env/local/bin/redis-server

#### start redis!
Note - I had to use sudo to do this. Not sure if this means potential permissions errors down the line...
     
     sudo /etc/init.d/redis_6379 start

Test to see if it's working (this is like Marco Polo!)
     
     /opt/nv_env/local/bin/redis-cli ping
     PONG

### Setting up Celery
We need to create a dedicated "celery module" and a celery_tasks script that will hold our different tasks.  The suggestion is to put it in the django top level directory, so the modules get initialized at the same time:

     touch /opt/nv_env/NeuroVault/neurovault/celery.py

The celery.py has a line that will "autodiscover" tasks defined in app directories in a module script named "tasks.py" (the app.autodiscover part below)

     vim /opt/nv_env/NeuroVault/neurovault/apps/statmaps/tasks.py

     from __future__ import absolute_import

     import os
     from celery import Celery
     from django.conf import settings

     # set the default Django settings module for the 'celery' program.
     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurovault.settings')

     app = Celery('neurovault')

     # Using a string here means the worker will not have to
     # pickle the object when using Windows.
     app.config_from_object('django.conf:settings')
     app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

     @app.task(bind=True)
     def debug_task(self):
         print('Request: {0!r}'.format(self.request))


The celery.py file also says to read the settings from the neurovault.settings (the app.config_from_object part above) so we need to add CELERY SETTINGS there (I added after INSTALLED_APPS):

     vim /opt/nv_env/NeuroVault/neurovault/settings.py
     # CELERY SETTINGS
     BROKER_URL = 'redis://localhost:6379/0'
     # comment out this line if you don't want to save results to backend
     CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
     CELERY_ACCEPT_CONTENT = ['json']
     CELERY_TASK_SERIALIZER = 'json'
     CELERY_RESULT_SERIALIZER = 'json'

#### Writing a test task
We can write tasks in any of our app folders in the tasks.py script. So if I add a function to make glass brains or a correlation matrix, I'd do it here (and I will need to look into how to specify when the job to run, etc).     

     vim /opt/nv_env/NeuroVault/neurovault/apps/tasks.py

     from __future__ import absolute_import

     from celery import shared_task

     @shared_task
     def test(name):
         return "Hello %s!" %(name)


#### Testing the task
In one terminal window, I start the server:

     (nv_env)vagrant@localhost:/opt/nv_env/NeuroVault$ /opt/nv_env/bin/celery --app=neurovault.celery:app worker --loglevel=INFO
 
     -------------- celery@localhost v3.1.17 (Cipater)
     ---- **** ----- 
     --- * ***  * -- Linux-3.13.0-24-generic-x86_64-with-Ubuntu-14.04-trusty
     -- * - **** --- 
     - ** ---------- [config]
     - ** ---------- .> app:         neurovault:0x7f18dc703f10
     - ** ---------- .> transport:   redis://localhost:6379/0
     - ** ---------- .> results:     disabled
     - *** --- * --- .> concurrency: 4 (prefork)
     -- ******* ---- 
     --- ***** ----- [queues]
     -------------- .> celery           exchange=celery(direct) key=celery
                

     [tasks]
       . neurovault.apps.statmaps.tasks.test
       . neurovault.celery.debug_task

     [2015-01-21 22:18:10,710: INFO/MainProcess] Connected to redis://localhost:6379/0
     [2015-01-21 22:18:10,723: INFO/MainProcess] mingle: searching for neighbors
     [2015-01-21 22:18:11,738: INFO/MainProcess] mingle: all alone
     /usr/local/lib/python2.7/dist-packages/celery/fixups/django.py:254: UserWarning: Using settings.DEBUG leads to a memory leak, never use this setting in production environments!
      warnings.warn('Using settings.DEBUG leads to a memory leak, never '

     [2015-01-21 22:18:11,759: WARNING/MainProcess] celery@localhost ready.

In another terminal window, I submit a job to it!

     source /opt/nv_env/bin/activate
     cd /opt/nv_env/NeuroVault
     python manage.py shell
     >>> from neurovault.apps.statmaps.tasks import test
     >>> result = test.delay('Vanessa')
     >>> result
     <AsyncResult: 1a3f1e7b-4678-4e3e-98e5-5386d6376439>
     >>> result.status
     >>> u'SUCCESS'
     >>> result.ready()
     >>> True

In the other window I see:

     [2015-01-21 22:40:38,170: INFO/MainProcess] Task neurovault.apps.statmaps.tasks.test[1a3f1e7b-4678-4e3e-98e5-5386d6376439] succeeded in 0.00690895300067s: u'Hello Vanessa!'

     # If we want to get any error:
     >>> result.traceback


### Setting up the daemon
I will want to set up celery to run as a daemon, and like uwsgi service thing, it looks like I can stop and start, and if we restart, we also need to specify the log files. It also looks we can start several workers (for different tasks) and this may be something that we want to do for different tasks in neurovault. I'm going to start with the one named worker (neurovault) with 4 processes. First, logging setup.

Note: I don't think I actually got this working, because I'm not totally sure which one to pick. I found a django module that can start the worker instead (keep reading).

#### Celery logging
The default is to send celery logs to pwd, so we have to specify where to send them.

     mkdir -p /var/run/celery
     mkdir -p /var/log/celery

Note: This is easy to direct to, although I didn't specify these paths when I was testing with the django module (djcelery) because there were permissions errors. I'm terrible with permissions, and didn't think it would be a good use of time to troubleshoot.

#### Setting up with django-celery

Add `celery-with-redis` and `django-celery` to required packages

     vim /opt/nv_env/NeuroVault/neurovault/requirements.txt
     celery-with-redis
     django-celery

     pip install requirements.txt

     # Add to the top of settings.py
     vim /opt/nv_env/NeuroVault/neurovault/settings.py
     import djcelery
     djcelery.setup_loader()
     ...

     # Add to installed apps:
     INSTALLED_APPS = [
         ...
         'djcelery',
         ...
     ]

#### Sync the database
Did I do this right?
     python /opt/nv_env/NeuroVault/manage.py syncdb


#### Starting the server!

     python /opt/nv_env/NeuroVault/manage.py celeryd -l INFO

(and the --pidfile and --logfile can be set, I was getting permissions errors for the ones in /var/run/celery* and I'm terrible with permissions so I just let it be the present working directory!)

Now I want to try running my task again:

     cd /opt/nv_env/NeuroVault
     python manage.py shell
     from neurovault.apps.statmaps.tasks import test
     result = test.delay('vanessa')
    
That worked too! It looks like this one is initialized from django, and the other option (above) is command line. I'll let Chris and Gabriel decide how they want to do this best, since I have no opinion, and more importantly, I'll probably mess it up. I'm now going to try to write tasks to produce the brain images when someone uploads, and also to generate a matrix each night.


### A Warning: No Pickles
When I was testing I found a warning that we can't use pickle for data structures, they don't like it:

     celery/apps/worker.py:161: CDeprecationWarning: 
     Starting from version 3.2 Celery will refuse to accept pickle by default.

     The pickle serializer is a security concern as it may give attackers
     the ability to execute any command.  It's important to secure
     your broker from unauthorized access when using pickle, so we think
     that enabling pickle should require a deliberate action and not be
     the default choice.

     If you depend on pickle then you should set a setting to disable this
     warning and to be sure that everything will continue working
     when you upgrade to Celery 3.2::

     CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
