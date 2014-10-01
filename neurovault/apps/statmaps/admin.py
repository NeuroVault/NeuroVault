from django.contrib import admin
from neurovault.apps.statmaps.models import Collection, Image 

admin.site.register(Image)
admin.site.register(Collection)