# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0032_migrate_cogatlas_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticmap',
            name='ignore_file_warning',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
