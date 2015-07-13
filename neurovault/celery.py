from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurovault.settings')
nvcelery = Celery('neurovault')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
nvcelery.config_from_object('django.conf:settings')
nvcelery.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


from opbeat.contrib.django.models import client, logger, register_handlers
from opbeat.contrib.celery import register_signal
try:
    register_signal(client)
except Exception as e:
    logger.exception('Failed installing celery hook: %s' % e)

if 'opbeat.contrib.django' in settings.INSTALLED_APPS:
    register_handlers()
