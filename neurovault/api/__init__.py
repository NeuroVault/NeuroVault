"""
Necessary to import so that `python manage.py spectacular`
uses the custom authentication schema.
"""
from schemas import JankyAuth

__all__ = ["JankyAuth"]
