# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0050_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cognitiveatlastask',
            name='name',
            field=models.CharField(max_length=200, db_index=True),
            preserve_default=True,
        ),
    ]
