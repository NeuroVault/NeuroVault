# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0041_cognitive_atlas_ondelete_do_nothing'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nidmresultstatisticmap',
            name='thumbnail',
        ),
        migrations.RemoveField(
            model_name='statisticmap',
            name='thumbnail',
        ),
        migrations.AddField(
            model_name='image',
            name='thumbnail',
            field=models.CharField(help_text=b'The orthogonal view thumbnail path of the nifti image', max_length=200, null=True, verbose_name=b'Image orthogonal view thumbnail (.png)', blank=True),
            preserve_default=True,
        ),
    ]
