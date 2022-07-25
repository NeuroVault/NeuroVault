
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurovault.settings')
nvcelery = Celery('neurovault')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
nvcelery.config_from_object('django.conf:settings')
nvcelery.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
