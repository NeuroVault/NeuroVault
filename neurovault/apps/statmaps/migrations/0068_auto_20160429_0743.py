# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def move_collection_data(apps, schema_editor):
    StatisticMap = apps.get_model("statmaps", "StatisticMap")
    BaseCollectionItem = apps.get_model("statmaps", "BaseCollectionItem")
    count = StatisticMap.objects.count()
    for i, image in enumerate(StatisticMap.objects.all()):
        print "Fixing image %d (%d/%d)"%(image.pk, i+1, count)
        print vars(image)
        image.number_of_subjects = image.basecollectionitem_ptr.collection.number_of_subjects
        image.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0066_basecollectionitem_is_valid'),
    ]

    operations = [
        migrations.AddField(
            model_name='nidmresultstatisticmap',
            name='number_of_subjects',
            field=models.IntegerField(help_text=b'Number of subjects used to generate this map', null=True, verbose_name=b'No. of subjects', blank=True),
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='number_of_subjects',
            field=models.IntegerField(help_text=b'Number of subjects used to generate this map', null=True, verbose_name=b'No. of subjects', blank=True),
        ),
        migrations.RunPython(move_collection_data),
        migrations.RemoveField(
            model_name='collection',
            name='number_of_subjects',
        ),
    ]
