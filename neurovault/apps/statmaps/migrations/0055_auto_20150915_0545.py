# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0054_collection_doi_add_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='doi_add_date',
            field=models.DateTimeField(db_index=True, verbose_name=b'date the DOI was added', null=True, editable=False, blank=True),
            preserve_default=True,
        ),
    ]
