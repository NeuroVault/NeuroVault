# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='private_token',
            field=models.CharField(null=True, default=None, max_length=8, blank=True, unique=True, db_index=True),
        ),
    ]
