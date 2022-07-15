# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0033_statisticmap_ignore_file_warning'),
    ]

    operations = [
        migrations.AddField(
            model_name='nidmresultstatisticmap',
            name='is_thresholded',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='nidmresultstatisticmap',
            name='perc_bad_voxels',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='is_thresholded',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='perc_bad_voxels',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
    ]
