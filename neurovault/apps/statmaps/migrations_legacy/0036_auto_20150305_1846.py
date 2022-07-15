# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0035_auto_20150305_0413'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statisticmap',
            name='ignore_file_warning',
            field=models.BooleanField(default=False, help_text=b'Ignore the warning when the map is sparse by nature, an ROI mask, or was acquired with limited field of view.', verbose_name=b'Ignore the warning about thresholding'),
            preserve_default=True,
        ),
    ]
