from django.contrib import admin
from neurovault.apps.statmaps.models import Collection, StatisticMap 

admin.site.register(StatisticMap)
admin.site.register(Collection)