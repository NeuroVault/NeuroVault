# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0055_auto_20150915_0545'),
    ]

    operations = [
        migrations.RenameField(
            model_name='collection',
            old_name='url',
            new_name='paper_url',
        ),
    ]
