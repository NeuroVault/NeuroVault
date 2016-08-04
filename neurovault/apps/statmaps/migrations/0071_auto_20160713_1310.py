# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0070_auto_20160526_2216'),
    ]

    operations = [
         migrations.DeleteModel('Similarity'),
         migrations.DeleteModel('Comparison')
    ]
