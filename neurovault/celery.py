
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurovault.settings')
nvcelery = Celery('neurovault')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
nvcelery.config_from_object('django.conf:settings')
nvcelery.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


from raven.contrib.django.raven_compat.models import client
from raven.contrib.celery import register_signal, register_logger_signal


# register a custom filter to filter out duplicate logs
register_logger_signal(client)

# hook into the Celery error handler
register_signal(client)

