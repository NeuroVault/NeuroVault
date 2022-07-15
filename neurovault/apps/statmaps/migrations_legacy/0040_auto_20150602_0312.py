# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0039_auto_20150514_0045'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='length_of_trials',
            field=models.CharField(help_text=b"Length of individual trials in seconds. If length varies across trials, enter 'variable'. ", max_length=200, null=True, verbose_name=b'Length of trials', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='collection',
            name='object_image_type',
            field=models.CharField(help_text=b'What type of image was used to determine the transformation to the atlas? (e.g. T1, T2, EPI)', max_length=200, null=True, verbose_name=b'Object image type', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='collection',
            name='skip_distance',
            field=models.FloatField(help_text=b'The size of the skipped area between slices in millimeters', null=True, verbose_name=b'Skip distance', blank=True),
            preserve_default=True,
        ),
    ]
