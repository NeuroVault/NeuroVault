# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0013_author_max_length'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nidmresults',
            name='image_ptr',
        ),
        migrations.DeleteModel(
            name='NIDMResults',
        ),
    ]
