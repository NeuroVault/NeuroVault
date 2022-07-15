# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0037_auto_20150307_0222'),
    ]

    operations = [
        migrations.AddField(
            model_name='nidmresultstatisticmap',
            name='transform',
            field=models.CharField(help_text=b'The path to the pickle file with a brain masked vector of resampled image data', max_length=200, null=True, verbose_name=b'Image transformation pickle path', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='transform',
            field=models.CharField(help_text=b'The path to the pickle file with a brain masked vector of resampled image data', max_length=200, null=True, verbose_name=b'Image transformation pickle path', blank=True),
            preserve_default=True,
        ),
    ]
