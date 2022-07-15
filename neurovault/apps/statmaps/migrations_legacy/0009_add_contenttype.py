# -*- coding: utf-8 -*-


from django.db import models, migrations

def add_contenttype(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    StatisticMap = apps.get_model("statmaps", "StatisticMap")
    for statisticmap in StatisticMap.objects.all():
        statisticmap.polymorphic_ctype = ContentType.objects.get(model='statisticmap', app_label='statmaps')
        statisticmap.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0008_polymorphism'),
    ]

    operations = [
        migrations.RunPython(add_contenttype),
    ]
