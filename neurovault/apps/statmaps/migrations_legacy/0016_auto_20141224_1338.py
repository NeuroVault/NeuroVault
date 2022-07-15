# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0015_auto_20141224_1214'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='name',
            field=models.CharField(max_length=200, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='nidmresults',
            name='name',
            field=models.CharField(max_length=200, db_index=True),
            preserve_default=True,
        ),
    ]
