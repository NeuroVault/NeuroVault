# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0070_auto_20160526_2216'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='topic_set',
            field=models.BooleanField(default=False, choices=[(False, b'Any collection of maps or parcellations'), (True, b'Collection of topic maps (with weights) intended for cognintive decoding.')]),
        ),
    ]
