"""Django project configuration, entry points and the composition root.

The Celery app is loaded with the settings, so tasks queued from the web
process use its configuration.
"""
from .celery import nvcelery

__all__ = ("nvcelery",)
