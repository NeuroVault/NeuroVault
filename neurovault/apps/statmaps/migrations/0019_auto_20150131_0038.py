# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0018_similarity_comparison'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='similarity',
            unique_together=set([('similarity_metric', 'transformation')]),
        ),
    ]
