# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0003_collection_journal_name'),
    ]

    operations = [
        migrations.RenameModel('Image', 'StatisticMap')
    ]
