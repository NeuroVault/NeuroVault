# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0069_auto_20160509_0907'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nidmresults',
            name='provn_file',
        ),
        migrations.AlterField(
            model_name='basecollectionitem',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
    ]
