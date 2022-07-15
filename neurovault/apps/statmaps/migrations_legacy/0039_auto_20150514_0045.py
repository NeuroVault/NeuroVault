# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0038_auto_20150514_0032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='length_of_trials',
            field=models.CharField(help_text=b"Length of individual trials in seconds. If variable, enter 'variable'. ", max_length=200, null=True, verbose_name=b'Length of trials', blank=True),
            preserve_default=True,
        ),
    ]
