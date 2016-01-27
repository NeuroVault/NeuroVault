# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0065_fix_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='basecollectionitem',
            name='is_valid',
            field=models.BooleanField(default=True),
            preserve_default=False,
        )
    ]
