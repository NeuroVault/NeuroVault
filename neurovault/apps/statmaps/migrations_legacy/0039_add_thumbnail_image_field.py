# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0038_add_transform_image_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='nidmresultstatisticmap',
            name='thumbnail',
            field=models.CharField(help_text=b'The orthogonal view thumbnail path of the nifti image', max_length=200, null=True, verbose_name=b'Image orthogonal view thumbnail (.png)', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='thumbnail',
            field=models.CharField(help_text=b'The orthogonal view thumbnail path of the nifti image', max_length=200, null=True, verbose_name=b'Image orthogonal view thumbnail (.png)', blank=True),
            preserve_default=True,
        ),
    ]
