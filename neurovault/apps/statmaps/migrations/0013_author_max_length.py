# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0012_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='authors',
            field=models.CharField(max_length=5000, null=True, blank=True),
            preserve_default=True,
        ),
    ]
