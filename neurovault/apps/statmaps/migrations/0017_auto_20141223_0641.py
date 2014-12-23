# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0016_auto_20141223_0633'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nidmresults',
            name='provn_file',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.NIDMStorage(), upload_to=neurovault.apps.statmaps.models.upload_nidm_to, null=True, verbose_name=b'Provenance store serialization of NIDM Results (.provn)', blank=True),
            preserve_default=True,
        ),
    ]
