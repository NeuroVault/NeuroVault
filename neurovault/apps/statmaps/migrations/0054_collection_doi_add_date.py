# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def populate_add_doi_date(apps, schema_editor):
    Collection = apps.get_model("statmaps", "Collection")
    for collection in Collection.objects.exclude(DOI__isnull=True).exclude(private=True):
        collection.doi_add_date = collection.add_date
        collection.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0053_auto_20150913_0657'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='doi_add_date',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name=b'date the DOI was added', db_index=True),
            preserve_default=True,
        ),
        migrations.RunPython(populate_add_doi_date)
    ]
